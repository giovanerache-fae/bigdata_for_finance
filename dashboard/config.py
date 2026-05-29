# config.py
# ==============================================================================
# Configurações globais, identidade visual e metadados dos indicadores
# ==============================================================================

# Paleta de Cores FAE (Identidade Visual)
CORES_FAE = {
    'roxo': '#9B2BC7',
    'dourado': '#E0D449',
    'azul_esverdeado': '#82E8E1',
    'amarelo_claro': '#F6ED52',
    'cinza_claro': '#F0F0F0',
    'cinza_escuro': '#404040',
}

# Cores semânticas (comparação com benchmark)
COR_EMPRESA   = '#9B2BC7'   # roxo FAE -> a empresa selecionada
COR_BENCH     = '#6B7280'   # cinza   -> mediana do setor (benchmark)
COR_MELHOR    = '#16A34A'   # verde   -> empresa melhor que o setor
COR_PIOR      = '#DC2626'   # vermelho-> empresa pior que o setor
COR_NEUTRO    = '#6B7280'

# Configurações Gerais da página
PAGE_CONFIG = {
    "page_title": "CVM Varejo • Análise Financeira",
    "page_icon": "🛒",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# ------------------------------------------------------------------------------
# Setor de foco do projeto: Varejo
# Classificação CVM (campo SETOR_ATIV) do setor de comércio varejista/atacadista.
# ------------------------------------------------------------------------------
SETOR_VAREJO = 'Comércio (Atacado e Varejo)'
EMPRESA_PADRAO_CNPJ = '61.585.865/0001-51'  # RAIA DROGASIL S.A.
N_ANOS_PADRAO = 5

# ------------------------------------------------------------------------------
# Demonstrativos financeiros (camada Silver)
# ------------------------------------------------------------------------------
DEMONSTRATIVOS = {
    "BP": {
        "tabela": "layer_02_silver.n1_dfp_cia_aberta_bp",
        "titulo": "Balanço Patrimonial",
        "icone": "🏛️",
        "tipo_layout": "bp",          # tratamento especial (Ativo x Passivo)
    },
    "DRE": {
        "tabela": "layer_02_silver.n1_dfp_cia_aberta_dre",
        "titulo": "Demonstração do Resultado (DRE)",
        "icone": "📈",
        "tipo_layout": "cascata",
        "prefixo": "3",
        "linhas_chave": {
            "3.01": "Receita Líquida",
            "3.03": "Lucro Bruto",
            "3.05": "EBIT (Result. Operacional)",
            "3.11": "Lucro/Prejuízo Líquido",
        },
    },
    "DFC": {
        "tabela": "layer_02_silver.n1_dfp_cia_aberta_dfc",
        "titulo": "Demonstração dos Fluxos de Caixa (DFC)",
        "icone": "💵",
        "tipo_layout": "fluxo",
        "prefixo": "6",
        "linhas_chave": {
            "6.01": "FC Operacional",
            "6.02": "FC Investimento",
            "6.03": "FC Financiamento",
            "6.05.02": "Saldo Final de Caixa",
        },
    },
}

GOLD_TABLE = "layer_03_gold.mart_indicadores_financeiros_x"

# ------------------------------------------------------------------------------
# Conjunto CURADO de indicadores para análise do varejo.
# Cada indicador: coluna da gold, rótulo, grupo, formato e direção ("melhor").
#   fmt:    'pct'   -> percentual (valor*100 %)
#           'mult'  -> índice/múltiplo (1,83×)
#           'dias'  -> prazo em dias
#           'pct_at'-> valor monetário normalizado pelo Ativo Total (% do AT)
#   melhor: 'maior' (quanto maior melhor) | 'menor' (quanto menor melhor)
#   norm:   coluna usada para normalizar (apenas fmt 'pct_at')
# ------------------------------------------------------------------------------
INDICADORES_VAREJO = [
    # --- Margens ---
    {"col": "I_MARGEM_LUCR", "nome": "Margem Bruta",        "grupo": "Margens",        "fmt": "pct",  "melhor": "maior",
     "desc": "Lucro Bruto ÷ Receita Líquida. Sobra após o custo das mercadorias vendidas (CMV)."},
    {"col": "I_MARGEM_OPER", "nome": "Margem Operacional",  "grupo": "Margens",        "fmt": "pct",  "melhor": "maior",
     "desc": "EBIT ÷ Receita Líquida. Eficiência da operação antes de juros e impostos."},
    {"col": "I_MARGEM_LIQ",  "nome": "Margem Líquida",      "grupo": "Margens",        "fmt": "pct",  "melhor": "maior",
     "desc": "Lucro Líquido ÷ Receita Líquida. Quanto sobra de cada R$ vendido após tudo."},
    # --- Rentabilidade ---
    {"col": "I_ROE", "nome": "ROE",  "grupo": "Rentabilidade", "fmt": "pct", "melhor": "maior",
     "desc": "Lucro Líquido ÷ Patrimônio Líquido. Retorno ao acionista. (N/A quando PL ≤ 0, pois o índice perde sentido.)"},
    {"col": "I_ROA", "nome": "ROA",  "grupo": "Rentabilidade", "fmt": "pct", "melhor": "maior",
     "desc": "Lucro Líquido ÷ Ativo Total. Eficiência dos ativos em gerar lucro."},
    {"col": "I_ROI", "nome": "ROI",  "grupo": "Rentabilidade", "fmt": "pct", "melhor": "maior",
     "desc": "Lucro Líquido ÷ (PL + Passivo Oneroso). Retorno sobre o capital investido. (N/A quando a base ≤ 0.)"},
    # --- Liquidez ---
    {"col": "I_LIQ_COR", "nome": "Liquidez Corrente", "grupo": "Liquidez", "fmt": "mult", "melhor": "maior",
     "desc": "Ativo Circulante ÷ Passivo Circulante. Folga de caixa de curto prazo (ref. ≥ 1,5×)."},
    {"col": "I_LIQ_SEC", "nome": "Liquidez Seca",     "grupo": "Liquidez", "fmt": "mult", "melhor": "maior",
     "desc": "(AC − Estoques) ÷ PC. Liquidez sem depender da venda do estoque — crítico no varejo."},
    # --- Endividamento ---
    {"col": "I_PCT_AT", "nome": "Capital de Terceiros / Ativo", "grupo": "Endividamento", "fmt": "pct", "melhor": "menor",
     "desc": "(PC + ELP) ÷ Ativo Total. Quanto do ativo é financiado por dívida."},
    {"col": "I_COMP_ENDIV", "nome": "Composição do Endividamento", "grupo": "Endividamento", "fmt": "pct", "melhor": "menor",
     "desc": "PC ÷ (PC + ELP). Quanto da dívida vence no curto prazo (quanto maior, pior)."},
    # --- Atividade (giros e prazos) ---
    {"col": "I_GIR_ESTQ", "nome": "Giro de Estoques", "grupo": "Atividade", "fmt": "mult", "melhor": "maior",
     "desc": "CMV ÷ Estoques. Nº de vezes que o estoque se renova no ano."},
    {"col": "I_PMRE", "nome": "PMRE — Prazo Médio de Estoques",   "grupo": "Atividade", "fmt": "dias", "melhor": "menor",
     "desc": "Dias que a mercadoria fica em estoque até ser vendida."},
    {"col": "I_PMRV", "nome": "PMRV — Prazo Médio de Recebimento", "grupo": "Atividade", "fmt": "dias", "melhor": "menor",
     "desc": "Dias para receber dos clientes após a venda."},
    {"col": "I_PMPC", "nome": "PMPC — Prazo Médio de Pagamento",   "grupo": "Atividade", "fmt": "dias", "melhor": "maior",
     "desc": "Dias para pagar fornecedores. Quanto maior, mais 'financiamento gratuito'."},
    # --- Ciclos ---
    {"col": "I_CICLO_ECON", "nome": "Ciclo Econômico",  "grupo": "Ciclos", "fmt": "dias", "melhor": "menor",
     "desc": "PMRE + PMRV. Dias entre comprar a mercadoria e receber pela venda."},
    {"col": "I_CICLO_FIN",  "nome": "Ciclo Financeiro", "grupo": "Ciclos", "fmt": "dias", "melhor": "menor",
     "desc": "PMRE + PMRV − PMPC. Dias que a empresa precisa financiar a operação (negativo = se autofinancia)."},
    # --- Capital de Giro (Modelo Fleuriet) — normalizados pelo Ativo Total ---
    {"col": "I_CGL_CCL", "nome": "Capital de Giro Líquido (CGL)", "grupo": "Capital de Giro", "fmt": "pct_at", "melhor": "maior", "norm": "V2_AT",
     "desc": "AC − PC, em % do Ativo Total. Folga estrutural de curto prazo."},
    {"col": "I_NCG", "nome": "Necessidade de Capital de Giro (NCG)", "grupo": "Capital de Giro", "fmt": "pct_at", "melhor": "menor", "norm": "V2_AT",
     "desc": "(Estoques + Clientes − Fornecedores), em % do AT. Negativo = operação se autofinancia."},
    {"col": "I_ST", "nome": "Saldo de Tesouraria (ST)", "grupo": "Capital de Giro", "fmt": "pct_at", "melhor": "maior", "norm": "V2_AT",
     "desc": "ACF − PCF, em % do AT. Saldo negativo recorrente = 'efeito tesoura' (alerta)."},
]

# Indicadores de destaque (cards no topo da página de indicadores)
INDICADORES_DESTAQUE = ["I_MARGEM_LIQ", "I_ROE", "I_LIQ_COR", "I_GIR_ESTQ", "I_CICLO_FIN", "I_PCT_AT"]

# Ordem dos grupos na exibição
ORDEM_GRUPOS = ["Margens", "Rentabilidade", "Liquidez", "Endividamento", "Atividade", "Ciclos", "Capital de Giro"]

# Acesso rápido por coluna
IND_POR_COL = {ind["col"]: ind for ind in INDICADORES_VAREJO}
