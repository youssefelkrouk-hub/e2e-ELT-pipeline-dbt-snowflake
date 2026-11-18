"""
config.py — Configuration centrale de l'application Streamlit.

Modifiez UNIQUEMENT ce fichier pour adapter les noms de tables
à votre environnement Snowflake.
"""

from __future__ import annotations
import os

# ---------------------------------------------------------------------------
# Snowflake — credentials chargés depuis les variables d'environnement
# ---------------------------------------------------------------------------
SNOWFLAKE_ACCOUNT   = os.getenv("SNOWFLAKE_ACCOUNT", "")
SNOWFLAKE_USER      = os.getenv("SNOWFLAKE_USER", "")
SNOWFLAKE_PASSWORD  = os.getenv("SNOWFLAKE_PASSWORD", "")
SNOWFLAKE_ROLE      = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
SNOWFLAKE_DATABASE  = os.getenv("SNOWFLAKE_DATABASE", "finance_db")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "finance_dwh")
SNOWFLAKE_SCHEMA    = os.getenv("SNOWFLAKE_SCHEMA", "raw")          # schema RAW
SNOWFLAKE_MARTS_SCHEMA = os.getenv("SNOWFLAKE_MARTS_SCHEMA", "MARTS")  # schema des marts dbt

# ---------------------------------------------------------------------------
# Tables RAW (source)
# ---------------------------------------------------------------------------
RAW_TABLES: dict[str, str] = {
    "customers":   f"{SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.CUSTOMERS",
    "orders":      f"{SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.ORDERS",
    "order_items": f"{SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.ORDER_ITEMS",
    "products":    f"{SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.PRODUCTS",
}

# ---------------------------------------------------------------------------
# Tables MARTS dbt (fully-qualified)
# ---------------------------------------------------------------------------
MART_DAILY_REVENUE      = f"{SNOWFLAKE_DATABASE}.{SNOWFLAKE_MARTS_SCHEMA}.DAILY_ORDER_REVENUE"
MART_STATUS_ORDER_COUNT = f"{SNOWFLAKE_DATABASE}.{SNOWFLAKE_MARTS_SCHEMA}.STATUS_ORDER_COUNT"
MART_COUNTRIES_QTY      = f"{SNOWFLAKE_DATABASE}.{SNOWFLAKE_MARTS_SCHEMA}.COUNTRIES_QUANTITIES"
MART_CUSTOMER_SEG       = f"{SNOWFLAKE_DATABASE}.{SNOWFLAKE_MARTS_SCHEMA}.CUSTOMER_SEGMENTATION"

# ---------------------------------------------------------------------------
# CSV — chemin monté dans le conteneur Docker
# ---------------------------------------------------------------------------
CSV_DIR = os.getenv("CSV_DIR", "/app/data")

# ---------------------------------------------------------------------------
# Airflow REST API (facultatif)
# ---------------------------------------------------------------------------
AIRFLOW_URL      = os.getenv("AIRFLOW_URL", "")          # ex: http://airflow:8080
AIRFLOW_USER     = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
AIRFLOW_DAG_ID   = os.getenv("AIRFLOW_DAG_ID", "dbt_snowflake_pipeline")

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
APP_TITLE      = "Sales Data Pipeline"
APP_SUBTITLE   = "Tableau de bord analytique — Snowflake · dbt · Streamlit"
COLOR_PALETTE  = [
    "#4C78A8", "#F58518", "#54A24B", "#E45756",
    "#72B7B2", "#FF9DA7", "#9D755D", "#BAB0AC",
]
PLOTLY_TEMPLATE = "plotly_white"
CACHE_TTL       = 600   # secondes
