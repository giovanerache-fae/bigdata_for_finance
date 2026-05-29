# database.py
# ==============================================================================
# Conexão e queries cacheadas (PostgreSQL)
#   - Demonstrativos (BP / DRE / DFC)  -> layer_02_silver
#   - Indicadores e Benchmark          -> layer_03_gold.mart_indicadores_financeiros_x
# ==============================================================================
import os
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import streamlit as st

from config import DEMONSTRATIVOS, GOLD_TABLE


# ==============================================================================
# CONEXÃO
# ==============================================================================
@st.cache_resource
def get_engine():
    """Cria a engine SQLAlchemy uma única vez (cache_resource)."""
    user = quote_plus(os.getenv("DB_USER", "postgres"))
    password = quote_plus(os.getenv("DB_PASS", os.getenv("DB_PASSWORD", "password")))
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "bigdata_for_finance")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url, pool_pre_ping=True)


def _read_sql(query, params=None):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params or {})


# ==============================================================================
# CATÁLOGO: setores e empresas (a partir da tabela Gold)
# ==============================================================================
@st.cache_data(ttl=3600)
def get_setores():
    """Setores disponíveis na Gold, ordenados por nº de empresas (desc)."""
    q = f"""
        SELECT "SETOR", COUNT(DISTINCT "CNPJ_CIA") AS n_empresas
        FROM {GOLD_TABLE}
        WHERE "SETOR" IS NOT NULL
        GROUP BY "SETOR"
        ORDER BY n_empresas DESC, "SETOR";
    """
    return _read_sql(q)


@st.cache_data(ttl=3600)
def get_empresas_setor(setor):
    """Empresas de um setor (CNPJ + razão social mais recente + nº de períodos)."""
    q = f"""
        SELECT DISTINCT ON ("CNPJ_CIA")
               "CNPJ_CIA",
               "RAZAO_SOCIAL",
               COUNT(*) OVER (PARTITION BY "CNPJ_CIA") AS n_periodos
        FROM {GOLD_TABLE}
        WHERE "SETOR" = :setor
        ORDER BY "CNPJ_CIA", "DT_REFER" DESC;
    """
    df = _read_sql(q, {"setor": setor})
    if not df.empty:
        df = df.sort_values("RAZAO_SOCIAL").reset_index(drop=True)
        df["LABEL"] = df["RAZAO_SOCIAL"] + "  (" + df["CNPJ_CIA"] + ")"
    return df


@st.cache_data(ttl=3600)
def get_anos_empresa(cnpj):
    """Anos (fiscais) disponíveis para a empresa na Gold, do mais recente p/ o mais antigo."""
    q = f"""
        SELECT DISTINCT EXTRACT(YEAR FROM "DT_REFER")::int AS ano
        FROM {GOLD_TABLE}
        WHERE "CNPJ_CIA" = :cnpj
        ORDER BY ano DESC;
    """
    df = _read_sql(q, {"cnpj": cnpj})
    return df["ano"].tolist() if not df.empty else []


# ==============================================================================
# DEMONSTRATIVOS (Silver) — BP / DRE / DFC
# ==============================================================================
@st.cache_data(ttl=600)
def get_demonstrativo(cnpj, tipo, anos):
    """
    Retorna as contas de um demonstrativo (BP/DRE/DFC) para uma empresa e
    lista de anos. Deduplica por (CD_CONTA, ano) preferindo o dado ORIGINAL
    (FLAG_RECONSTRUCAO=False) e a maior VERSAO.
    Colunas: CD_CONTA, DS_CONTA, ANO, VL_CONTA_TRATADO
    """
    tabela = DEMONSTRATIVOS[tipo]["tabela"]
    # anos são inteiros derivados do banco (sem risco de injeção) — inline na cláusula IN
    lista_anos = ", ".join(str(int(a)) for a in anos)
    if not lista_anos:
        return pd.DataFrame(columns=["CD_CONTA", "DS_CONTA", "ANO", "VL_CONTA_TRATADO"])
    q = f"""
        WITH ranked AS (
            SELECT
                "CD_CONTA",
                "DS_CONTA",
                EXTRACT(YEAR FROM "DT_REFER")::int AS "ANO",
                "VL_CONTA_TRATADO",
                ROW_NUMBER() OVER (
                    PARTITION BY "CD_CONTA", EXTRACT(YEAR FROM "DT_REFER")
                    ORDER BY "FLAG_RECONSTRUCAO" ASC, "VERSAO" DESC
                ) AS rn
            FROM {tabela}
            WHERE "CNPJ_CIA" = :cnpj
              AND EXTRACT(YEAR FROM "DT_REFER")::int IN ({lista_anos})
        )
        SELECT "CD_CONTA", "DS_CONTA", "ANO", "VL_CONTA_TRATADO"
        FROM ranked
        WHERE rn = 1
        ORDER BY "CD_CONTA", "ANO";
    """
    return _read_sql(q, {"cnpj": cnpj})


# ==============================================================================
# INDICADORES + BENCHMARK (Gold)
# ==============================================================================
@st.cache_data(ttl=600)
def get_painel_setor(setor):
    """
    Painel completo do setor (todas as empresas, todos os anos) a partir da Gold.
    Uma linha por (CNPJ, DT_REFER) com V1_*, V2_* e indicadores I_*.
    Usado tanto para a empresa-alvo quanto para o benchmark (mediana dos pares).
    """
    q = f"""
        SELECT *, EXTRACT(YEAR FROM "DT_REFER")::int AS "ANO"
        FROM {GOLD_TABLE}
        WHERE "SETOR" = :setor
        ORDER BY "CNPJ_CIA", "DT_REFER";
    """
    return _read_sql(q, {"setor": setor})


@st.cache_data(ttl=3600)
def healthcheck():
    """Verifica conexão e presença das tabelas-chave. Retorna (ok, msg)."""
    try:
        df = _read_sql(f'SELECT COUNT(*) AS n FROM {GOLD_TABLE};')
        return True, f"{int(df['n'].iloc[0])} linhas na camada Gold"
    except Exception as e:  # pragma: no cover
        return False, str(e)
