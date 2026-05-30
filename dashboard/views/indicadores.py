# views/indicadores.py
# ==============================================================================
# Indicadores financeiros do VAREJO x BENCHMARK (mediana das demais varejistas)
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config import (
    INDICADORES_VAREJO, INDICADORES_DESTAQUE, IND_POR_COL, ORDEM_GRUPOS,
    COR_EMPRESA, COR_BENCH, COR_MELHOR, COR_PIOR, COR_NEUTRO, SETOR_VAREJO,
)
from database import get_painel_setor
from helpers import (
    fmt_indicador, serie_empresa, serie_benchmark, comparar, br_num,
    aplicar_estilo_grafico,
)


# ------------------------------------------------------------------------------
def _delta_texto(v_emp, v_bench, fmt):
    """Diferença empresa - benchmark, formatada na unidade do indicador."""
    if v_emp is None or v_bench is None or pd.isna(v_emp) or pd.isna(v_bench):
        return "—"
    d = v_emp - v_bench
    sinal = "+" if d >= 0 else "−"
    d = abs(d)
    if fmt in ("pct", "pct_at"):
        return f"{sinal}{br_num(d * 100, 1)} p.p."
    if fmt == "mult":
        return f"{sinal}{br_num(d, 2)}×"
    if fmt == "dias":
        return f"{sinal}{br_num(d, 0)} d"
    return f"{sinal}{br_num(d, 2)}"


def _ultimo_valor(serie, ano):
    if serie.empty:
        return None
    row = serie[serie["ANO"] == ano]
    if row.empty or pd.isna(row["valor"].iloc[0]):
        return None
    return float(row["valor"].iloc[0])


def _metric_card(container, ind, v_emp, v_bench):
    """Cartão = st.metric nativo. O tooltip (ícone ⓘ via help=) traz a FÓRMULA
    e a mediana do setor. O delta colorido mostra a posição vs setor."""
    formula = ind.get("formula", "")
    txt_bench = fmt_indicador(v_bench, ind["fmt"])
    ajuda = f"Fórmula: {formula}\n\nMediana do setor: {txt_bench}"
    val = fmt_indicador(v_emp, ind["fmt"])

    if v_emp is None or v_bench is None or pd.isna(v_emp) or pd.isna(v_bench):
        container.metric(ind["nome"], val, help=ajuda, border=True)
        return

    diff = v_emp - v_bench
    if ind["fmt"] in ("pct", "pct_at"):
        mag = f"{br_num(abs(diff) * 100, 1)} p.p."
    elif ind["fmt"] == "mult":
        mag = f"{br_num(abs(diff), 2)}×"
    elif ind["fmt"] == "dias":
        mag = f"{br_num(abs(diff), 0)} d"
    else:
        mag = br_num(abs(diff), 2)
    sinal = "+" if diff >= 0 else "-"                      # ascii: o Streamlit infere a cor pelo sinal
    delta = f"{sinal}{mag} vs setor"
    # 'maior é melhor' -> sobe=verde (normal); 'menor é melhor' -> desce=verde (inverse)
    dcolor = "normal" if ind["melhor"] == "maior" else "inverse"
    container.metric(ind["nome"], val, delta=delta, delta_color=dcolor, help=ajuda, border=True)


# ------------------------------------------------------------------------------
def render_indicadores(cnpj, nome, setor, anos):
    st.subheader("🎯 Indicadores do Varejo × Benchmark Setorial")
    st.caption(
        f"**{nome}** · CNPJ {cnpj} · setor **{setor}**  \n"
        f"Benchmark = **mediana de todas as empresas do setor** (referência fixa — não muda ao trocar a empresa), por ano."
    )

    painel = get_painel_setor(setor)
    if painel.empty:
        st.warning("Setor sem dados na camada Gold.")
        return

    anos = sorted(int(a) for a in anos)
    painel = painel[painel["ANO"].isin(anos)].copy()
    ano_ref = max(anos)

    n_emp = painel["CNPJ_CIA"].nunique()
    st.info(f"📌 Ano de referência dos cartões: **{ano_ref}** · "
            f"Benchmark = mediana de **{n_emp} empresas** do setor (inclui a empresa-alvo; é uma referência fixa).")

    # Pré-computa séries por indicador
    series = {}
    for ind in INDICADORES_VAREJO:
        emp = serie_empresa(painel, cnpj, ind)
        bench = serie_benchmark(painel, ind)
        series[ind["col"]] = (emp, bench)

    # ---------- Resumo comparativo — cards por indicador (tooltip de fórmula no ⓘ) ----------
    st.markdown(
        f"##### Resumo comparativo — {ano_ref}  "
        "·  <span style='color:#888;font-size:.82rem'>passe o mouse no ⓘ de cada indicador para ver a fórmula</span>",
        unsafe_allow_html=True,
    )
    grupos = [g for g in ORDEM_GRUPOS if any(i["grupo"] == g for i in INDICADORES_VAREJO)]
    for gi, grupo in enumerate(grupos):
        if gi > 0:   # linha discreta separando as categorias
            st.markdown("<hr style='border:none;border-top:1px solid #ECECEC;margin:0.7rem 0 0.4rem;'>",
                        unsafe_allow_html=True)
        st.markdown(f"**{grupo}**")
        inds_g = [i for i in INDICADORES_VAREJO if i["grupo"] == grupo]
        for j in range(0, len(inds_g), 3):
            linha = inds_g[j:j + 3]
            cols = st.columns(3)
            for k, ind in enumerate(linha):
                emp, bench = series[ind["col"]]
                v_emp = _ultimo_valor(emp, ano_ref)
                v_bench = _ultimo_valor(bench, ano_ref)
                _metric_card(cols[k], ind, v_emp, v_bench)
    st.caption("Cada cartão: valor da empresa · variação vs mediana do setor "
               "(verde = melhor, vermelho = pior, conforme a direção do indicador) · ⓘ = fórmula.")

    st.markdown("---")

    # ---------- 3) Evolução nos anos selecionados (por grupo) ----------
    st.markdown(f"##### Evolução {min(anos)}–{max(anos)} · empresa × mediana do setor")
    grupos = [g for g in ORDEM_GRUPOS if any(i["grupo"] == g for i in INDICADORES_VAREJO)]
    tabs = st.tabs(grupos)
    for tab, grupo in zip(tabs, grupos):
        with tab:
            inds_grupo = [i for i in INDICADORES_VAREJO if i["grupo"] == grupo]
            for j in range(0, len(inds_grupo), 2):
                linha = inds_grupo[j:j + 2]
                cols = st.columns(len(linha))
                for c, ind in zip(cols, linha):
                    with c:
                        _grafico_evolucao(ind, *series[ind["col"]], anos)


# ------------------------------------------------------------------------------
def _grafico_evolucao(ind, emp, bench, anos):
    anos_str = [str(a) for a in anos]
    emp_map = {int(r["ANO"]): r["valor"] for _, r in emp.iterrows()}
    bench_map = {int(r["ANO"]): r["valor"] for _, r in bench.iterrows()}
    y_emp = [emp_map.get(a) for a in anos]
    y_bench = [bench_map.get(a) for a in anos]
    rot = lambda ys: [fmt_indicador(v, ind["fmt"]) if v is not None else "" for v in ys]
    formula = ind.get("formula", "")
    # hover (tooltip do gráfico) inclui a fórmula do indicador
    ht_emp = ("<b>Empresa · " + ind["nome"] + "</b><br>ƒ: " + formula
              + "<br>%{x}: %{customdata}<extra></extra>")
    ht_bench = "<b>Mediana do setor</b><br>%{x}: %{customdata}<extra></extra>"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=anos_str, y=y_bench, name="Mediana setor", mode="lines+markers+text",
        line=dict(color=COR_BENCH, width=2, dash="dash"), marker=dict(size=6),
        text=rot(y_bench), textposition="bottom center", textfont=dict(size=15, color=COR_BENCH),
        customdata=rot(y_bench), hovertemplate=ht_bench))
    fig.add_trace(go.Scatter(
        x=anos_str, y=y_emp, name="Empresa", mode="lines+markers+text",
        line=dict(color=COR_EMPRESA, width=3), marker=dict(size=8),
        text=rot(y_emp), textposition="top center", textfont=dict(size=16, color=COR_EMPRESA),
        customdata=rot(y_emp), hovertemplate=ht_emp))
    fig.update_layout(
        title=dict(text=f"{ind['nome']}", font=dict(size=13)),
        height=320, margin=dict(t=40, b=30, l=10, r=10),
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center", font=dict(size=10)),
        hovermode="x unified",
    )
    aplicar_estilo_grafico(fig)
    st.plotly_chart(fig, width="stretch")
    st.caption(f"**ƒ:** {ind.get('formula','')} — {ind['desc']}")
