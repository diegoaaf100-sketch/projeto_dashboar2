import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Consulta",
    page_icon="🔍",
    layout="wide"
)

# Escopos da API do Google
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# --- AUTENTICAÇÃO COM GOOGLE SHEETS ---
@st.cache_resource
def get_gspread_client():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(credentials)

# --- FUNÇÃO PARA LISTAR AS ABAS DA PLANILHA ---
@st.cache_data(ttl=300)  # Atualiza a lista a cada 5 minutos
def list_worksheets(sheet_id):
    client = get_gspread_client()
    spreadsheet = client.open_by_key(sheet_id)
    return [ws.title for ws in spreadsheet.worksheets()]

# --- FUNÇÃO PARA CARREGAR OS DADOS DA ABA SELECIONADA ---
@st.cache_data(ttl=60)   # Atualiza os dados a cada 1 minuto
def load_sheet_data(sheet_id, sheet_name):
    client = get_gspread_client()
    worksheet = client.open_by_key(sheet_id).worksheet(sheet_name)
    records = worksheet.get_all_records()
    
    if not records:
        return pd.DataFrame()
        
    df = pd.DataFrame(records)
    # Limpa nomes de colunas (remove espaços extras)
    df.columns = [str(col).strip() for col in df.columns]
    return df

# --- INTERFACE DO DASHBOARD ---
st.title("🔍 Painel de Consulta e Leitura de Dados")

try:
    SHEET_ID = st.secrets["NEW_SHEET_ID"]
    
    # 1. Menu Lateral - Seleção da Aba
    st.sidebar.header("📂 Navegação")
    lista_abas = list_worksheets(SHEET_ID)
    
    aba_selecionada = st.sidebar.selectbox(
        "Selecione a Aba / Página:",
        options=lista_abas
    )
    
    # Carrega os dados da aba escolhida
    df = load_sheet_data(SHEET_ID, aba_selecionada)
    
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Filtros")
    
    if df.empty:
        st.warning("A aba selecionada está vazia ou não possui dados formatados.")
    else:
        # 2. Filtro Dinâmico na Sidebar
        # Permite ao usuário escolher por qual coluna deseja filtrar
        colunas_disponiveis = list(df.columns)
        coluna_filtro = st.sidebar.selectbox(
            "Filtrar pela coluna:",
            options=["(Nenhum filtro)"] + colunas_disponiveis
        )
        
        df_filtrado = df.copy()
        
        if coluna_filtro != "(Nenhum filtro)":
            valores_unicos = sorted(list(df[coluna_filtro].astype(str).unique()))
            valores_selecionados = st.sidebar.multiselect(
                f"Selecione o(s) valor(es) em '{coluna_filtro}':",
                options=valores_unicos,
                default=valores_unicos
            )
            # Aplica o filtro
            if valores_selecionados:
                df_filtrado = df[df[coluna_filtro].astype(str).isin(valores_selecionados)]
            else:
                df_filtrado = pd.DataFrame(columns=df.columns)

        # Campo de busca rápida por texto em toda a tabela
        busca_texto = st.text_input("🔎 Pesquisa rápida (busca qualquer termo na tabela):")
        if busca_texto:
            df_filtrado = df_filtrado[
                df_filtrado.astype(str).apply(
                    lambda row: row.str.contains(busca_texto, case=False).any(), axis=1
                )
            ]

        # 3. Métricas Rápidas
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Registros Exibidos", len(df_filtrado))
        col_m2.metric("Total de Registros na Aba", len(df))
        
        st.markdown("---")
        
        # 4. Exibição da Tabela
        st.subheader(f"📋 Dados da aba: `{aba_selecionada}`")
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

        # 5. Botão de Exportação/Download do resultado filtrado
        csv_data = df_filtrado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Baixar dados filtrados (CSV)",
            data=csv_data,
            file_name=f"consulta_{aba_selecionada}.csv",
            mime="text/csv"
        )

except Exception as e:
    st.error(f"❌ Ocorreu um erro ao carregar os dados: {e}")
