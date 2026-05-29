# Dashboard CVM · Análise Financeira do Varejo

Dashboard em **Streamlit** que analisa as demonstrações financeiras (CVM/DFP) de
empresas do setor de **varejo** — Balanço Patrimonial, DRE, DFC e ~18 indicadores
comparados com o benchmark (mediana) do setor.

O dashboard **não traz os dados embutidos**: ele lê de um banco **PostgreSQL** com
as camadas `layer_02_silver` e `layer_03_gold` já restauradas.

---

## Pré-requisitos

- **Python 3.11+**
- **PostgreSQL** com o banco restaurado (schemas `layer_02_silver` e `layer_03_gold`).

## Como rodar

```bash
# 1. Clonar o projeto
git clone https://github.com/felipeniehuesgarcia-oss/big_data_for_finance_final.git
cd big_data_for_finance_final

# 2. Criar e ativar um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Configurar a conexão com o banco
cp .env.example .env
#   abra o .env e ajuste DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASS
#   para apontar para o SEU PostgreSQL local

# 5. Rodar o dashboard
streamlit run dashboard/app.py
```

O Streamlit abre em `http://localhost:8501`.

## Configuração do banco (`.env`)

Copie `.env.example` para `.env` e ajuste os valores para o seu banco:

| Variável  | Descrição              | Exemplo               |
|-----------|------------------------|-----------------------|
| `DB_HOST` | endereço do PostgreSQL | `localhost`           |
| `DB_PORT` | porta                  | `5432`                |
| `DB_NAME` | nome do banco          | `bigdata_for_finance` |
| `DB_USER` | usuário                | `bigdata`             |
| `DB_PASS` | senha                  | `bigdata`             |

> O `.env` é ignorado pelo Git — cada pessoa usa as credenciais do seu próprio
> banco. Por isso o repositório traz apenas o `.env.example` de modelo.

## Estrutura

```
dashboard/
  app.py            # entrada do Streamlit (sidebar, navegação)
  config.py         # setor, empresa padrão e catálogo de indicadores
  database.py       # conexão e queries (silver + gold)
  helpers.py        # cálculo e formatação dos indicadores
  views/            # páginas: visão geral, demonstrativos, indicadores
notebooks/          # pipeline Medallion (bronze → silver → gold)
```

---

Dados públicos da CVM (DFP) · pipeline Medallion · projeto didático — FAE.
