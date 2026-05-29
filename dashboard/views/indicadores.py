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


def _card(container, ind, v_emp, v_bench):
    verdict = comparar(v_emp, v_bench, ind["melhor"])
    cor = {"melhor": COR_MELHOR, "pior": COR_PIOR, "igual": COR_NEUTRO}.get(verdict, COR_NEUTRO)
    # Seta = direção factual (acima/abaixo da mediana); a COR indica se é bom ou ruim
    if v_emp is None or v_bench is None or pd.isna(v_emp) or pd.isna(v_bench):
        seta = "•"
    elif v_emp > v_bench:
        seta = "↑"
    elif v_emp < v_bench:
        seta = "↓"
    else:
        seta = "→"
    txt_emp = fmt_indicador(v_emp, ind["fmt"])
    txt_bench = fmt_indicador(v_bench, ind["fmt"])
    delta = _delta_texto(v_emp, v_bench, ind["fmt"]) if verdict else "sem comparação"
    html = f"""
    <div style="border:1px solid #ECECEC;border-left:5px solid {cor};border-radius:10px;
                padding:12px 14px;background:#FFFFFF;box-shadow:0 1px 2px rgba(0,0,0,.04);">
      <div style="font-size:.78rem;color:#6B7280;height:2.2em;line-height:1.1em;">{ind['nome']}</div>
      <div style="font-size:1.7rem;font-weight:700;color:#111827;">{txt_emp}</div>
      <div style="font-size:.8rem;color:{cor};font-weight:600;">{seta} {delta} vs setor</div>
      <div style="font-size:.72rem;color:#9CA3AF;">mediana setor: {txt_bench}</div>
    </div>
    """
    container.markdown(html, unsafe_allow_html=True)


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

    # ---------- 1) Cartões de destaque (ano de referência) ----------
    st.markdown("##### Destaques")
    cols = st.columns(3)
    for i, col_id in enumerate(INDICADORES_DESTAQUE):
        ind = IND_POR_COL[col_id]
        emp, bench = series[col_id]
        v_emp = _ultimo_valor(emp, ano_ref)
        v_bench = _ultimo_valor(bench, ano_ref)
        _card(cols[i % 3], ind, v_emp, v_bench)
        if i % 3 == 2 and i != len(INDICADORES_DESTAQUE) - 1:
            cols = st.columns(3)

    st.markdown("---")

    # ---------- 2) Tabela-resumo (empresa x setor no ano de referência) ----------
    st.markdown(f"##### Resumo comparativo — {ano_ref}")
    linhas = []
    for ind in INDICADORES_VAREJO:
        emp, bench = series[ind["col"]]
        v_emp = _ultimo_valor(emp, ano_ref)
        v_bench = _ultimo_valor(bench, ano_ref)
        verdict = comparar(v_emp, v_bench, ind["melhor"])
        # Posição = factual (valor maior/menor que a mediana); a COR reflete se é BOM
        if verdict is None:
            posicao = "— sem dado"
        elif v_emp > v_bench:
            posicao = "▲ acima do setor"
        elif v_emp < v_bench:
            posicao = "▼ abaixo do setor"
        else:
            posicao = "▬ na mediana"
        # a cor reflete se é BOM
        linhas.append({
            "Grupo": ind["grupo"],
            "Indicador": ind["nome"],
            "Empresa": fmt_indicador(v_emp, ind["fmt"]),
            "Mediana Setor": fmt_indicador(v_bench, ind["fmt"]),
            "Diferença": _delta_texto(v_emp, v_bench, ind["fmt"]),
            "Posição": posicao,
            "_verdict": verdict or "",
        })
    df_resumo = pd.DataFrame(linhas)

    def _estilo(row):
        cor = {"melhor": "background-color:#DCFCE7;color:#166534;font-weight:600",
               "pior": "background-color:#FEE2E2;color:#991B1B;font-weight:600",
               "igual": "background-color:#F3F4F6;color:#374151"}.get(row["_verdict"], "")
        return ["" if c != "Posição" else cor for c in df_resumo.columns]

    styler = df_resumo.style.apply(_estilo, axis=1)
    st.dataframe(
        styler, hide_index=True, width="stretch",
        column_order=["Grupo", "Indicador", "Empresa", "Mediana Setor", "Diferença", "Posição"],
        column_config={"_verdict": None},
        height=min((len(df_resumo) + 1) * 35 + 3, 760),
    )
    st.caption("🟩 verde = melhor que a mediana do setor · 🟥 vermelho = pior · "
               "a direção considera se 'maior' ou 'menor' é melhor para cada indicador.")

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
def _yaxis_fmt(fmt):
    if fmt in ("pct", "pct_at"):
        return dict(tickformat=".0%")
    if fmt == "mult":
        return dict(ticksuffix="×")
    if fmt == "dias":
        return dict(ticksuffix=" d")
    return dict()


def _grafico_evolucao(ind, emp, bench, anos):
    anos_str = [str(a) for a in anos]
    emp_map = {int(r["ANO"]): r["valor"] for _, r in emp.iterrows()}
    bench_map = {int(r["ANO"]): r["valor"] for _, r in bench.iterrows()}
    y_emp = [emp_map.get(a) for a in anos]
    y_bench = [bench_map.get(a) for a in anos]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=anos_str, y=y_bench, name="Mediana setor", mode="lines+markers",
                             line=dict(color=COR_BENCH, width=2, dash="dash"), marker=dict(size=6)))
    fig.add_trace(go.Scatter(x=anos_str, y=y_emp, name="Empresa", mode="lines+markers",
                             line=dict(color=COR_EMPRESA, width=3), marker=dict(size=8)))
    fig.update_layout(
        title=dict(text=f"{ind['nome']}", font=dict(size=13)),
        height=300, plot_bgcolor="white", margin=dict(t=40, b=30, l=10, r=10),
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center", font=dict(size=10)),
        hovermode="x unified",
    )
    fig.update_yaxes(**_yaxis_fmt(ind["fmt"]), gridcolor="#EEE")
    fig.update_xaxes(type="category")
    st.plotly_chart(fig, width="stretch")
    st.caption(ind["desc"])
