# views/visao_geral.py
# ==============================================================================
# Painel de abertura: identidade da empresa + KPIs do último exercício
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config import CORES_FAE, COR_EMPRESA, IND_POR_COL
from database import get_painel_setor
from helpers import fmt_moeda_compacta, fmt_indicador, br_num, valor_col


def _num(df, col, ano):
    row = df[df["ANO"] == ano]
    if row.empty:
        return None
    v = pd.to_numeric(row[col], errors="coerce").iloc[0]
    return None if pd.isna(v) else float(v)


def _delta_pct(atual, anterior):
    if atual is None or anterior is None or anterior == 0:
        return None
    return (atual / anterior - 1)


def render_visao_geral(cnpj, nome, setor, anos):
    st.subheader(f"🛒 {nome}")
    st.caption(f"CNPJ {cnpj} · Setor **{setor}** · Análise dos últimos {len(anos)} exercícios")

    painel = get_painel_setor(setor)
    emp = painel[painel["CNPJ_CIA"] == cnpj].copy()
    if emp.empty:
        st.warning("Sem dados para esta empresa.")
        return

    anos = sorted(int(a) for a in anos)
    ano_ref = max(anos)
    ano_ant = ano_ref - 1 if (ano_ref - 1) in set(emp["ANO"]) else None

    st.markdown(f"##### Destaques do exercício de {ano_ref}")

    # KPIs monetários
    kpis_money = [
        ("V1_RL", "Receita Líquida"),
        ("V1_LL", "Lucro Líquido"),
        ("V2_AT", "Ativo Total"),
        ("V1_PL", "Patrimônio Líquido"),
    ]
    cols = st.columns(4)
    for c, (col, label) in zip(cols, kpis_money):
        atual = _num(emp, col, ano_ref)
        ant = _num(emp, col, ano_ant) if ano_ant else None
        d = _delta_pct(atual, ant)
        c.metric(label, fmt_moeda_compacta(atual),
                 delta=(f"{br_num(d * 100, 1)}% a/a" if d is not None else None))

    # KPIs de indicadores (recalculados das variáveis-base via valor_col)
    kpis_ind = ["I_MARGEM_LIQ", "I_ROE", "I_LIQ_COR", "I_CICLO_FIN"]
    cols = st.columns(4)
    emp_calc = emp.assign(_ord=emp["ANO"])
    for c, col in zip(cols, kpis_ind):
        ind = IND_POR_COL[col]
        serie = valor_col(emp_calc, ind)
        df_v = emp_calc.assign(_v=serie)
        row = df_v[df_v["ANO"] == ano_ref]
        atual = None if row.empty or pd.isna(row["_v"].iloc[0]) else float(row["_v"].iloc[0])
        c.metric(ind["nome"], fmt_indicador(atual, ind["fmt"]))

    st.markdown("---")

    # Gráfico Receita x Lucro Líquido ao longo dos anos
    st.markdown("##### Receita Líquida e Lucro Líquido")
    emp_a = emp[emp["ANO"].isin(anos)].sort_values("ANO")
    anos_str = [str(a) for a in emp_a["ANO"]]
    receita = pd.to_numeric(emp_a["V1_RL"], errors="coerce")
    lucro = pd.to_numeric(emp_a["V1_LL"], errors="coerce")

    fig = go.Figure()
    fig.add_bar(x=anos_str, y=receita, name="Receita Líquida", marker_color=CORES_FAE["azul_esverdeado"],
                text=[fmt_moeda_compacta(v) for v in receita], textposition="outside")
    fig.add_trace(go.Scatter(x=anos_str, y=lucro, name="Lucro Líquido", mode="lines+markers+text",
                             line=dict(color=COR_EMPRESA, width=3), marker=dict(size=9),
                             text=[fmt_moeda_compacta(v) for v in lucro], textposition="top center"))
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.update_layout(height=430, plot_bgcolor="white", hovermode="x unified",
                      legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"))
    st.plotly_chart(fig, width="stretch")

    st.info(
        "Use o menu lateral para navegar: **Balanço Patrimonial**, **DRE** e **DFC** trazem os "
        "três demonstrativos dos últimos anos; **Indicadores × Benchmark** compara a empresa com a "
        "mediana das demais varejistas do setor."
    )
