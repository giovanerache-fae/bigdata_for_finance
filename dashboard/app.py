# app.py — Dashboard CVM • Análise Financeira do Varejo
# ==============================================================================
import os
import streamlit as st
from dotenv import load_dotenv

from config import (
    PAGE_CONFIG, SETOR_VAREJO, EMPRESA_PADRAO_CNPJ, N_ANOS_PADRAO,
)

# 1) Config da página (primeira chamada Streamlit)
st.set_page_config(**PAGE_CONFIG)

# 2) Variáveis de ambiente (.env na raiz do projeto)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from database import (  # noqa: E402  (após load_dotenv)
    get_setores, get_empresas_setor, get_anos_empresa, healthcheck,
)
from views.visao_geral import render_visao_geral       # noqa: E402
from views.demonstrativos import render_demonstrativo   # noqa: E402
from views.indicadores import render_indicadores        # noqa: E402


# ------------------------------------------------------------------------------
# SIDEBAR — seleção de setor / empresa / período + navegação
# ------------------------------------------------------------------------------
def _selecao_sidebar():
    st.sidebar.title("🛒 CVM · Varejo")
    st.sidebar.caption("Big Data for Finance — FAE")

    ok, msg = healthcheck()
    if not ok:
        st.sidebar.error(f"Banco indisponível: {msg}")
        st.stop()

    df_setores = get_setores()
    setores = df_setores["SETOR"].tolist()
    idx_setor = setores.index(SETOR_VAREJO) if SETOR_VAREJO in setores else 0
    setor = st.sidebar.selectbox("Setor (benchmark)", setores, index=idx_setor,
                                 help="O benchmark é a mediana das empresas deste setor.")

    df_emp = get_empresas_setor(setor)
    if df_emp.empty:
        st.sidebar.error("Setor sem empresas.")
        st.stop()

    labels = df_emp["LABEL"].tolist()
    cnpjs = df_emp["CNPJ_CIA"].tolist()
    idx_emp = cnpjs.index(EMPRESA_PADRAO_CNPJ) if EMPRESA_PADRAO_CNPJ in cnpjs else 0
    label_sel = st.sidebar.selectbox("Empresa-alvo", labels, index=idx_emp)
    cnpj = dict(zip(labels, cnpjs))[label_sel]
    nome = df_emp[df_emp["CNPJ_CIA"] == cnpj]["RAZAO_SOCIAL"].iloc[0]

    anos_disp = sorted(get_anos_empresa(cnpj))   # ascendente
    if not anos_disp:
        st.sidebar.error("Empresa sem exercícios disponíveis na base.")
        st.stop()
    if len(anos_disp) >= 2:
        # padrão: últimos N anos; usuário arrasta as pontas para escolher o intervalo
        default_ini = anos_disp[-N_ANOS_PADRAO] if len(anos_disp) >= N_ANOS_PADRAO else anos_disp[0]
        ini, fim = st.sidebar.select_slider(
            "Período (intervalo de exercícios)",
            options=anos_disp,
            value=(default_ini, anos_disp[-1]),
            help="Arraste as pontas para escolher de qual a qual ano analisar.",
        )
        anos = [a for a in anos_disp if ini <= a <= fim]
    else:
        anos = anos_disp

    st.sidebar.markdown("---")
    pagina = st.sidebar.radio(
        "Navegação",
        ["Visão Geral", "Balanço Patrimonial", "DRE", "DFC", "Indicadores × Benchmark"],
    )
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Período: **{min(anos)}–{max(anos)}** · {len(anos)} anos")
    return setor, cnpj, nome, anos, pagina


def main():
    setor, cnpj, nome, anos, pagina = _selecao_sidebar()

    if pagina == "Visão Geral":
        render_visao_geral(cnpj, nome, setor, anos)
    elif pagina == "Balanço Patrimonial":
        render_demonstrativo(cnpj, nome, "BP", anos)
    elif pagina == "DRE":
        render_demonstrativo(cnpj, nome, "DRE", anos)
    elif pagina == "DFC":
        render_demonstrativo(cnpj, nome, "DFC", anos)
    elif pagina == "Indicadores × Benchmark":
        render_indicadores(cnpj, nome, setor, anos)

    # Rodapé
    st.markdown("---")
    c1, c2 = st.columns([3, 1])
    c1.caption("Dados públicos CVM (DFP) · Pipeline Medallion (bronze→silver→gold) · fins didáticos.")
    c2.caption("Big Data for Finance — FAE")


main()
