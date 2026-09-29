import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Dashboard de Consulta - Planilha Privada",
    page_icon="📊",
    layout="wide"
)

# Escopos de permissão
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# --- AUTENTICAÇÃO COM A CONTA DE SERVIÇO ---
@st.cache_resource
def get_gspread_client():
    # Lê as credenciais seguras vindas do st.secrets
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(credentials)

# --- FUNÇÃO PARA LISTAR TODAS AS ABAS DA PLANILHA PRIVADA ---
@st.cache_data(ttl=300) # Cache de 5 minutos
def list_worksheets(sheet_id):
    client = get_gspread_client()
    spreadsheet = client.open_by_key(sheet_id)
    return [ws.title for ws in spreadsheet.worksheets()]

# --- FUNÇÃO PARA CARREGAR OS DADOS DA ABA SELECIONADA ---
@st.cache_data(ttl=60) # Cache de 1 minuto
def load_sheet_data(sheet_id, sheet_name):
    client = get_gspread_client()
    worksheet = client.open_by_key(sheet_id).worksheet(sheet_name)
    records = worksheet.get_all_records()
    
    if not records:
        return pd.DataFrame()
        
    df = pd.DataFrame(records)
    df.columns = [str(col).strip() for col in df.columns]
    return df

# --- DENTRO DA APLICAÇÃO ---
st.title("📊 Painel de Consulta de Dados")

try:
    # ID da nova planilha configurada nos Secrets
    NEW_SHEET_ID = st.secrets["NEW_SHEET_ID"]
    
    # Busca todas as abas automaticamente
    lista_abas = list_worksheets(NEW_SHEET_ID)
    
    # Menu Lateral para Navegação e Filtros
    st.sidebar.header("📂 Navegação")
    aba_selecionada = st.sidebar.selectbox("Selecione a Aba:", options=lista_abas)
    
    # Carrega dados da aba escolhida
    df = load_sheet_data(NEW_SHEET_ID, aba_selecionada)
    
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Filtros")
    
    if df.empty:
        st.warning("A aba selecionada não possui dados.")
    else:
        # Filtro dinâmico por coluna
        colunas = list(df.columns)
        coluna_filtro = st.sidebar.selectbox("Filtrar por coluna:", options=["(Nenhum filtro)"] + colunas)
        
        df_filtrado = df.copy()
        
        if coluna_filtro != "(Nenhum filtro)":
            opcoes_unicas = sorted(list(df[coluna_filtro].astype(str).unique()))
            selecionados = st.sidebar.multiselect(
                f"Valores em '{coluna_filtro}':",
                options=opcoes_unicas,
                default=opcoes_unicas
            )
            df_filtrado = df[df[coluna_filtro].astype(str).isin(selecionados)]

        # Pesquisa textual rápida
        busca = st.text_input("🔎 Pesquisar termo na tabela:")
        if busca:
            df_filtrado = df_filtrado[
                df_filtrado.astype(str).apply(
                    lambda row: row.str.contains(busca, case=False).any(), axis=1
                )
            ]

        # Métricas de contagem
        col1, col2 = st.columns(2)
        col1.metric("Registros Filtrados", len(df_filtrado))
        col2.metric("Total na Aba", len(df))
        
        st.markdown("---")
        
        # Tabela
        st.subheader(f"📋 Exibindo: `{aba_selecionada}`")
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

        # Botão para baixar CSV
        csv = df_filtrado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar resultado em CSV",
            data=csv,
            file_name=f"{aba_selecionada}_filtrado.csv",
            mime="text/csv"
        )

except Exception as e:
    st.error(f"❌ Erro ao conectar com a planilha privada: {e}")
