# 🛒 Dashboard — Análise Financeira do Varejo (CVM)

Dashboard Streamlit que apresenta os **três demonstrativos** (BP, DRE, DFC) dos últimos
exercícios de uma empresa do **varejo** e calcula um conjunto curado de **indicadores
financeiros** comparando-os com o **benchmark setorial** (mediana das demais varejistas).

---

## 1. Pré-requisitos

- PostgreSQL com o banco `bigdata_for_finance` restaurado (schemas `layer_02_silver` e `layer_03_gold`).
- Python 3.10+ com as dependências de `requirements.txt` (inclui `streamlit`).

### Restaurar o dump (feito uma vez)

```bash
# instalar cliente/servidor PostgreSQL 18 (o dump é archive custom v1.16)
# criar role e banco
createdb -O bigdata bigdata_for_finance
# restaurar só os schemas necessários ao dashboard
pg_restore -d "postgresql://bigdata:bigdata@localhost:5432/bigdata_for_finance" \
  --no-owner --no-acl -n layer_02_silver -n layer_03_gold -j 2 \
  dump-bigdata_for_finance-202605222109.sql
```

### Credenciais (`.env` na raiz do projeto)

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bigdata_for_finance
DB_USER=bigdata
DB_PASS=bigdata
```

---

## 2. Como rodar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Acesse `http://localhost:8501`. Na barra lateral selecione o **setor** (padrão:
*Comércio (Atacado e Varejo)*), a **empresa-alvo** e o **número de exercícios** (padrão: 5).

---

## 3. Páginas

| Página | Conteúdo |
|---|---|
| **Visão Geral** | Identidade da empresa + KPIs do último exercício (Receita, Lucro, Ativo, PL, Margem Líquida, ROE, Liquidez, Ciclo Financeiro) e evolução Receita × Lucro. |
| **Balanço Patrimonial** | Ativo e Passivo+PL por conta (com filtro de nível), validação `Ativo = Passivo + PL` e evolução do Ativo Total. |
| **DRE** | Demonstração do Resultado por conta + linhas-chave (Receita, Lucro Bruto, EBIT, Lucro Líquido). |
| **DFC** | Fluxos de Caixa por conta + fluxos Operacional/Investimento/Financiamento e Saldo Final de Caixa. |
| **Indicadores × Benchmark** | ~18 indicadores curados do varejo: cartões de destaque, tabela comparativa (empresa × mediana do setor) e gráficos de evolução por grupo. |

---

## 4. Indicadores curados (setor de varejo)

Definidos em `config.py → INDICADORES_VAREJO`, agrupados em: **Margens**, **Rentabilidade**,
**Liquidez**, **Endividamento**, **Atividade** (giros e prazos), **Ciclos** e **Capital de Giro**
(modelo Fleuriet). A ênfase em atividade/ciclos e capital de giro reflete o que mais diferencia
varejistas (giro de estoque, prazos e autofinanciamento operacional).

### Benchmark

Para cada indicador e ano, o benchmark é a **mediana de todas as empresas do setor**
(a empresa-alvo **é incluída** no cálculo). Assim o benchmark é uma **referência fixa
do setor**: não muda quando se troca a empresa selecionada. A mediana é robusta a
outliers — mesma metodologia do notebook `03_gold/1_benchmarking_indicadores_financeiros.ipynb`.
Os indicadores de capital de giro (CGL, NCG, ST) são normalizados pelo **Ativo Total**
(% do AT) para comparar empresas de portes diferentes.

### ⚠️ Nota de cálculo (importante)

A tabela `layer_03_gold.mart_indicadores_financeiros_x` aplica as fórmulas do *data contract*
de forma **literal**, usando o CPV (conta 3.02) com o **sinal negativo** que ele tem na base.
Isso **inverte o sinal** de Giro de Estoques, PMRE, PMPC e dos Ciclos. Por isso o dashboard
**recalcula** os indicadores a partir das variáveis Nível-1 (`V1_*`/`V2_*`) em
`helpers.computar_indicador()`, aplicando `ABS(CPV)` — conforme exige o `premissas_calculo.md` —
e a definição correta de Saldo de Tesouraria de Fleuriet `ST = (Caixa + Aplicações) − Empréstimos CP`.

---

## 5. Estrutura do código

```
dashboard/
├── app.py            # navegação + seleção de setor/empresa/período
├── config.py         # cores, setor de foco e metadados dos indicadores
├── database.py       # conexão e queries cacheadas (silver + gold)
├── helpers.py        # formatação BR e cálculo de indicadores/benchmark
└── views/
    ├── visao_geral.py
    ├── demonstrativos.py   # renderizador genérico de BP/DRE/DFC
    └── indicadores.py      # indicadores × benchmark
```
