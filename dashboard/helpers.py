# helpers.py
# ==============================================================================
# Funções utilitárias: formatação (padrão BR) e cálculo de benchmark setorial
# ==============================================================================
import numpy as np
import pandas as pd


# ------------------------------------------------------------------------------
# Formatação numérica no padrão brasileiro
# ------------------------------------------------------------------------------
def br_num(valor, dec=2):
    """Formata número no padrão brasileiro: 1.234,56"""
    if valor is None or pd.isna(valor):
        return "—"
    texto = f"{valor:,.{dec}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_moeda_br(valor):
    """float -> '1.000,00' (padrão brasileiro). NaN -> '—'."""
    return br_num(valor, 2)


def fmt_moeda_compacta(valor):
    """Valor monetário compacto: R$ 1,2 bi / R$ 340,5 mi / R$ 12,3 mil."""
    if valor is None or pd.isna(valor):
        return "—"
    v = float(valor)
    sinal = "-" if v < 0 else ""
    a = abs(v)
    if a >= 1e9:
        return f"{sinal}R$ {br_num(a / 1e9, 2)} bi"
    if a >= 1e6:
        return f"{sinal}R$ {br_num(a / 1e6, 1)} mi"
    if a >= 1e3:
        return f"{sinal}R$ {br_num(a / 1e3, 1)} mil"
    return f"{sinal}R$ {br_num(a, 0)}"


def fmt_indicador(valor, fmt):
    """
    Formata o valor de um indicador conforme seu tipo:
      pct / pct_at -> percentual (valor*100 %)
      mult         -> múltiplo (1,83×)
      dias         -> prazo (72 d)
    """
    if valor is None or pd.isna(valor) or (isinstance(valor, float) and np.isinf(valor)):
        return "—"
    if fmt in ("pct", "pct_at"):
        return f"{br_num(valor * 100, 1)}%"
    if fmt == "mult":
        return f"{br_num(valor, 2)}×"
    if fmt == "dias":
        return f"{br_num(valor, 0)} d"
    return br_num(valor, 2)


# ------------------------------------------------------------------------------
# Extração do valor de um indicador (com normalização opcional pelo Ativo Total)
# ------------------------------------------------------------------------------
def _safe_div(num, den):
    """Divisão vetorizada segura: denominador 0/NaN -> NaN (evita inf)."""
    den = pd.to_numeric(den, errors="coerce").replace(0, np.nan)
    return pd.to_numeric(num, errors="coerce") / den


def computar_indicador(df, col):
    """
    (RE)calcula um indicador a partir das variáveis Nível-1/Nível-2 da Gold,
    seguindo `premissas_calculo.md` e `indicadores_financeiros.md`.

    Motivo: a tabela `mart_indicadores_financeiros_x` aplicou as fórmulas do
    data contract de forma literal usando o CPV com SINAL NEGATIVO (como vem na
    Silver). Isso inverte o sinal de Giro de Estoques, PMRE, PMPC e dos Ciclos.
    Aqui usamos ABS(CPV) (premissa explícita) e a definição correta de Fleuriet,
    garantindo valores corretos tanto para a empresa quanto para o benchmark.
    """
    def c(name):
        return pd.to_numeric(df[name], errors="coerce")

    AC, PC, PNC, RLP, PL = c("V1_AC"), c("V1_PC"), c("V1_PNC"), c("V1_RLP"), c("V1_PL")
    ES, CR, FO, RL = c("V1_ES"), c("V1_CR"), c("V1_FO"), c("V1_RL")
    ES_nz = ES.where(ES > 0)           # estoque > 0; senão N/A (premissa N2: sem estoque -> N/A)
    LB, EBIT, LL = c("V1_LB"), c("V1_EBIT"), c("V1_LL")
    CX, AP, EFCP = c("V1_CX"), c("V1_AP"), c("V1_EFCP")
    AT, EFT = c("V2_AT"), c("V2_EFT")
    COGS = c("V1_COGS").abs()          # premissa: usar ABS(CPV)
    PASSIVO_TOT = PC + PNC

    f = {
        # Margens
        "I_MARGEM_LUCR": lambda: _safe_div(LB, RL),
        "I_MARGEM_OPER": lambda: _safe_div(EBIT, RL),
        "I_MARGEM_LIQ":  lambda: _safe_div(LL, RL),
        # Rentabilidade
        # ROE/ROI: N/A quando o capital próprio / investido é <= 0 (premissa V12):
        # com PL negativo, prejuízo (LL<0) produziria ROE POSITIVO enganoso.
        "I_ROA": lambda: _safe_div(LL, AT),
        "I_ROE": lambda: _safe_div(LL, PL.where(PL > 0)),
        "I_ROI": lambda: _safe_div(LL, (EFT + PL).where((EFT + PL) > 0)),
        # Liquidez
        "I_LIQ_COR": lambda: _safe_div(AC, PC),
        "I_LIQ_SEC": lambda: _safe_div(AC - ES.fillna(0), PC),
        # Endividamento
        "I_PCT_AT":     lambda: _safe_div(PASSIVO_TOT, AT),
        "I_COMP_ENDIV": lambda: _safe_div(PC, PASSIVO_TOT),
        # Atividade (ABS no CPV; estoque deve ser > 0, senão N/A)
        "I_GIR_ESTQ": lambda: _safe_div(COGS, ES_nz),
        "I_PMRE":     lambda: _safe_div(ES_nz * 360, COGS),
        "I_PMRV":     lambda: _safe_div(CR * 360, RL),
        "I_PMPC":     lambda: _safe_div(FO * 360, COGS),
        # Ciclos (Econômico/Financeiro ficam N/A quando não há estoque)
        "I_CICLO_ECON": lambda: _safe_div(ES_nz * 360, COGS) + _safe_div(CR * 360, RL),
        "I_CICLO_FIN":  lambda: _safe_div(ES_nz * 360, COGS) + _safe_div(CR * 360, RL) - _safe_div(FO * 360, COGS),
        # Capital de Giro (valores em R$; normalização p/ % do AT ocorre em valor_col)
        "I_CGL_CCL": lambda: AC - PC,
        "I_NCG":     lambda: (ES.fillna(0) + CR) - FO,
        "I_ST":      lambda: (CX + AP.fillna(0)) - EFCP,   # Fleuriet: ACF - PCF
    }
    if col in f:
        return f[col]().replace([np.inf, -np.inf], np.nan)
    # fallback: lê a coluna pré-calculada
    return pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)


def valor_col(df, ind):
    """
    Series numérica do indicador `ind`, recalculada das variáveis-base.
    Se `ind` define 'norm' (ex.: V2_AT), normaliza o valor (valor / denominador).
    """
    s = computar_indicador(df, ind["col"])
    norm = ind.get("norm")
    if norm:
        s = _safe_div(s, df[norm])
    return s.replace([np.inf, -np.inf], np.nan)


def serie_empresa(painel, cnpj, ind):
    """DataFrame [ANO, valor] do indicador para a empresa-alvo (ordenado por ano)."""
    sub = painel[painel["CNPJ_CIA"] == cnpj].copy()
    if sub.empty:
        return pd.DataFrame(columns=["ANO", "valor"])
    sub["valor"] = valor_col(sub, ind)
    return sub[["ANO", "valor"]].sort_values("ANO").reset_index(drop=True)


def serie_benchmark(painel, ind):
    """
    DataFrame [ANO, valor] com a MEDIANA setorial do indicador, por ano,
    considerando TODAS as empresas do setor (INCLUSIVE a empresa-alvo).
    Assim o benchmark é uma referência fixa do setor: não muda ao trocar a
    empresa selecionada. Coluna 'n' = nº de empresas com valor em cada ano.
    """
    if painel.empty:
        return pd.DataFrame(columns=["ANO", "valor", "n"])
    base = painel.copy()
    base["_v"] = valor_col(base, ind)
    g = base.dropna(subset=["_v"]).groupby("ANO")["_v"]
    out = g.median().reset_index().rename(columns={"_v": "valor"})
    out["n"] = g.size().values
    return out.sort_values("ANO").reset_index(drop=True)


def comparar(valor_empresa, valor_bench, melhor):
    """
    Compara empresa x benchmark respeitando a direção do indicador.
    Retorna 'melhor' | 'pior' | 'igual' | None.
    """
    if valor_empresa is None or valor_bench is None:
        return None
    if pd.isna(valor_empresa) or pd.isna(valor_bench):
        return None
    diff = valor_empresa - valor_bench
    if abs(diff) < 1e-9:
        return "igual"
    if melhor == "maior":
        return "melhor" if diff > 0 else "pior"
    else:  # 'menor'
        return "melhor" if diff < 0 else "pior"


# ------------------------------------------------------------------------------
# Pivot de demonstrativo: linhas = contas, colunas = anos
# ------------------------------------------------------------------------------
def pivot_demonstrativo(df_raw, anos, divisor=1.0):
    """
    Recebe o DataFrame de get_demonstrativo (CD_CONTA, DS_CONTA, ANO, VL_CONTA_TRATADO)
    e retorna pivot [CD_CONTA, DS_CONTA, <ano1>, <ano2>, ...] (anos como str, ordenados).
    """
    if df_raw.empty:
        return pd.DataFrame(), []
    df = df_raw.copy()
    df["VL_CONTA_TRATADO"] = pd.to_numeric(df["VL_CONTA_TRATADO"], errors="coerce") / divisor

    # Descrição representativa por conta = a do ano mais recente
    ds = (df.sort_values("ANO").groupby("CD_CONTA")["DS_CONTA"].last())

    # Pivot apenas por CD_CONTA (evita duplicar linha quando DS_CONTA varia entre anos)
    piv = df.pivot_table(
        values="VL_CONTA_TRATADO", index="CD_CONTA", columns="ANO", aggfunc="sum",
    )
    cols_anos_int = sorted(piv.columns.tolist())
    piv = piv[cols_anos_int].rename(columns={c: str(c) for c in cols_anos_int})
    cols_anos = [str(c) for c in cols_anos_int]
    piv = piv.reset_index()
    piv.insert(1, "DS_CONTA", piv["CD_CONTA"].map(ds))
    piv = piv.sort_values("CD_CONTA").reset_index(drop=True)
    return piv, cols_anos


def nivel_para_digitos(nivel):
    """Nível 1->1 dígito, 2->3, 3->5, 4->7, 5->9 (formato CD_CONTA hierárquico)."""
    return (nivel * 2) - 1


def conta_qtd_digitos(cd_conta):
    """Quantidade de dígitos de um CD_CONTA (ex.: '1.01.04' -> 5)."""
    return len(str(cd_conta).replace(".", ""))
