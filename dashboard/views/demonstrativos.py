# views/demonstrativos.py
# ==============================================================================
# Renderizador genérico dos 3 demonstrativos da camada Silver: BP, DRE e DFC.
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config import DEMONSTRATIVOS, CORES_FAE
from database import get_demonstrativo
from helpers import (
    fmt_moeda_br, pivot_demonstrativo, nivel_para_digitos, conta_qtd_digitos,
    aplicar_estilo_grafico,
)

ESCALAS = {
    "Unidade (R$)": 1,
    "Milhares": 1_000,
    "Milhões": 1_000_000,
    "Bilhões": 1_000_000_000,
}


# ------------------------------------------------------------------------------
def _tabela(df, cols_anos, titulo, emoji, escala_label):
    """cols_anos define a ORDEM das colunas de ano (mais recente primeiro)."""
    st.markdown(f"#### {emoji} {titulo}  \n<span style='color:#888'>valores em {escala_label}</span>",
                unsafe_allow_html=True)
    if df.empty:
        st.info("Sem contas neste nível.")
        return
    df_view = df.copy()
    for c in cols_anos:
        df_view[c] = df_view[c].apply(fmt_moeda_br)
    cols_presentes = [c for c in cols_anos if c in df_view.columns]
    df_view = df_view[["CD_CONTA", "DS_CONTA"] + cols_presentes]   # ordem: mais recente -> mais antigo
    col_cfg = {
        "CD_CONTA": st.column_config.TextColumn("Conta", width="small"),
        "DS_CONTA": st.column_config.TextColumn("Descrição", width="large"),
        **{c: st.column_config.TextColumn(c, width="small") for c in cols_presentes},
    }
    altura = min((len(df_view) + 1) * 35 + 3, 720)
    st.dataframe(df_view, hide_index=True, width="stretch",
                 column_config=col_cfg, height=altura)


def _linha_conta(df_raw, codigo, anos, divisor):
    """Série [valor por ano] de uma conta específica (ordenada por ano)."""
    sub = df_raw[df_raw["CD_CONTA"] == codigo]
    m = {int(r["ANO"]): pd.to_numeric(r["VL_CONTA_TRATADO"], errors="coerce") / divisor
         for _, r in sub.iterrows()}
    return [m.get(int(a)) for a in anos]


# ------------------------------------------------------------------------------
def render_demonstrativo(cnpj, nome, tipo, anos):
    cfg = DEMONSTRATIVOS[tipo]
    st.subheader(f"{cfg['icone']} {cfg['titulo']}")
    st.caption(f"**{nome}** · CNPJ {cnpj} · exercícios: {', '.join(str(a) for a in sorted(anos, reverse=True))}")

    c1, c2 = st.columns([1, 2])
    nivel = c1.slider("Nível de detalhe das contas", 1, 5, 3, key=f"niv_{tipo}",
                      help="1 = grupos principais · 5 = contas mais analíticas")
    escala_label = c2.radio("Escala dos valores", list(ESCALAS.keys()),
                            index=1, horizontal=True, key=f"esc_{tipo}")
    divisor = ESCALAS[escala_label]

    df_raw = get_demonstrativo(cnpj, tipo, anos)
    if df_raw.empty:
        st.warning("Nenhum dado encontrado para esta empresa/período.")
        return

    piv, cols_anos = pivot_demonstrativo(df_raw, anos, divisor)
    if piv.empty:
        st.warning("Nenhum dado encontrado.")
        return

    cols_desc = cols_anos[::-1]                 # mais recente -> mais antigo (tabelas)
    anos_cron = sorted(int(a) for a in anos)    # cronológico (gráficos)

    max_dig = nivel_para_digitos(nivel)
    piv_f = piv[piv["CD_CONTA"].apply(conta_qtd_digitos) <= max_dig].copy()

    if cfg["tipo_layout"] == "bp":
        _render_bp(piv_f, cols_desc, df_raw, anos_cron, divisor, escala_label)
    else:
        _tabela(piv_f, cols_desc, cfg["titulo"], cfg["icone"], escala_label)
        st.markdown("###")
        _render_linhas_chave(df_raw, anos_cron, divisor, cfg, escala_label)


# ------------------------------------------------------------------------------
# Balanço Patrimonial: Ativo EM CIMA, Passivo + PL EMBAIXO + validação contábil
# ------------------------------------------------------------------------------
def _render_bp(piv_f, cols_desc, df_raw, anos_cron, divisor, escala_label):
    df_ativo = piv_f[piv_f["CD_CONTA"].str.startswith("1")].copy()
    df_passivo = piv_f[piv_f["CD_CONTA"].str.startswith("2")].copy()

    # Ativo acima do Passivo (melhor visibilidade)
    _tabela(df_ativo, cols_desc, "Ativo", "🟢", escala_label)
    st.markdown("###")
    _tabela(df_passivo, cols_desc, "Passivo + Patrimônio Líquido", "🔴", escala_label)

    # Totais (conta raiz '1' e '2') a partir do df_raw (independe do nível)
    total_ativo = _linha_conta(df_raw, "1", anos_cron, divisor)
    total_passivo = _linha_conta(df_raw, "2", anos_cron, divisor)
    anos_str = [str(a) for a in anos_cron]

    fig = go.Figure()
    fig.add_bar(x=anos_str, y=total_ativo, name="Ativo Total", marker_color="#2E8B57",
                text=[fmt_moeda_br(v) for v in total_ativo], textposition="outside",
                textfont=dict(size=19))
    fig.add_bar(x=anos_str, y=total_passivo, name="Passivo + PL", marker_color="#CD5C5C",
                text=[fmt_moeda_br(v) for v in total_passivo], textposition="outside",
                textfont=dict(size=19))
    fig.update_layout(barmode="group", height=420,
                      title=f"Equilíbrio Patrimonial ({escala_label})",
                      legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
                      margin=dict(t=70, b=30, l=10, r=10))
    aplicar_estilo_grafico(fig)
    st.plotly_chart(fig, width="stretch")

    # Validação Ativo = Passivo + PL
    difs = [(ta - tp) if (ta is not None and tp is not None) else None
            for ta, tp in zip(total_ativo, total_passivo)]
    max_dif = max([abs(d) for d in difs if d is not None], default=0)
    if max_dif > 0.1:
        st.error(f"⚠️ Divergência contábil máx. de {fmt_moeda_br(max_dif)} ({escala_label}).")
    else:
        st.success("✅ Balanço validado: Ativo = Passivo + Patrimônio Líquido em todos os anos.")


# ------------------------------------------------------------------------------
# DRE / DFC: tabela + gráfico das linhas-chave (com rótulos de dados)
# ------------------------------------------------------------------------------
def _render_linhas_chave(df_raw, anos_cron, divisor, cfg, escala_label):
    linhas = cfg.get("linhas_chave", {})
    if not linhas:
        return
    anos_str = [str(a) for a in anos_cron]
    st.markdown(f"#### 📊 Linhas-chave ({escala_label})")

    paleta = [CORES_FAE["roxo"], "#2E8B57", CORES_FAE["dourado"], "#2563EB", "#DC2626"]
    fig = go.Figure()
    usa_barra = cfg["tipo_layout"] == "fluxo"
    for i, (codigo, rotulo) in enumerate(linhas.items()):
        valores = _linha_conta(df_raw, codigo, anos_cron, divisor)
        rotulos = [fmt_moeda_br(v) for v in valores]
        cor = paleta[i % len(paleta)]
        if usa_barra and codigo != "6.05.02":
            fig.add_bar(x=anos_str, y=valores, name=rotulo, marker_color=cor,
                        text=rotulos, textposition="outside", textfont=dict(size=18))
        else:
            fig.add_trace(go.Scatter(
                x=anos_str, y=valores, name=rotulo, mode="lines+markers+text",
                line=dict(color=cor, width=3), marker=dict(size=8),
                text=rotulos, textposition="top center", textfont=dict(size=18, color=cor)))
    fig.update_layout(height=460,
                      legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
                      hovermode="x unified", margin=dict(t=70, b=30, l=10, r=10))
    aplicar_estilo_grafico(fig)
    st.plotly_chart(fig, width="stretch")
