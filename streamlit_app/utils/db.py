"""
db.py — Connexion Snowflake et fonctions de requêtage.

Toutes les requêtes sont paramétrées (pas de concaténation de chaînes).
La connexion est mise en cache via @st.cache_resource.
Les données sont mises en cache via @st.cache_data(ttl=CACHE_TTL).

En cas d'indisponibilité de Snowflake, les fonctions lèvent une exception
que l'appelant traite en mode démo (CSV locaux).
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st

from utils.config import (
    SNOWFLAKE_ACCOUNT,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_PASSWORD,
    SNOWFLAKE_ROLE,
    SNOWFLAKE_USER,
    SNOWFLAKE_WAREHOUSE,
    SNOWFLAKE_MARTS_SCHEMA,
    MART_DAILY_REVENUE,
    MART_STATUS_ORDER_COUNT,
    MART_COUNTRIES_QTY,
    MART_CUSTOMER_SEG,
    RAW_TABLES,
    CACHE_TTL,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connexion
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Connexion à Snowflake…")
def get_connection():
    """Crée et retourne une connexion Snowflake mise en cache.

    Returns:
        snowflake.connector.SnowflakeConnection

    Raises:
        RuntimeError: si les credentials sont absents ou la connexion échoue.
    """
    if not SNOWFLAKE_ACCOUNT or not SNOWFLAKE_USER or not SNOWFLAKE_PASSWORD:
        raise RuntimeError(
            "Variables d'environnement Snowflake manquantes. "
            "Vérifiez SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD."
        )
    try:
        import snowflake.connector  # noqa: PLC0415

        conn = snowflake.connector.connect(
            account=SNOWFLAKE_ACCOUNT,
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            role=SNOWFLAKE_ROLE,
            database=SNOWFLAKE_DATABASE,
            warehouse=SNOWFLAKE_WAREHOUSE,
            schema=SNOWFLAKE_MARTS_SCHEMA,
            client_session_keep_alive=True,
        )
        logger.info("Connexion Snowflake établie.")
        return conn
    except Exception as exc:
        logger.error("Échec de la connexion Snowflake : %s", exc)
        raise


# ---------------------------------------------------------------------------
# Utilitaire de requête bas niveau
# ---------------------------------------------------------------------------

def _query(sql: str, params: tuple[Any, ...] | None = None) -> pd.DataFrame:
    """Exécute *sql* (paramétré) et retourne un DataFrame pandas.

    Args:
        sql:    Requête SQL avec des placeholders %s.
        params: Tuple de valeurs à lier.

    Returns:
        pd.DataFrame avec les colonnes en MAJUSCULES normalisées.

    Raises:
        Exception: toute erreur de base de données est propagée.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        df = cur.fetch_pandas_all()
        # Normalisation des noms de colonnes en minuscules pour cohérence
        df.columns = [c.lower() for c in df.columns]
        return df
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Fonctions métier mises en cache
# ---------------------------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL, show_spinner="Chargement des revenus journaliers…")
def fetch_daily_revenue() -> pd.DataFrame:
    """Retourne le mart Daily_Order_Revenue (order_date, total_price)."""
    sql = f"SELECT order_date, total_price FROM {MART_DAILY_REVENUE} ORDER BY order_date"  # noqa: S608
    df = _query(sql)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["total_price"] = pd.to_numeric(df["total_price"], errors="coerce")
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner="Chargement des statuts de commandes…")
def fetch_status_order_count() -> pd.DataFrame:
    """Retourne le mart Status_Order_Count (order_status, no of orders)."""
    sql = f'SELECT order_status, "no of orders" AS nb_orders FROM {MART_STATUS_ORDER_COUNT}'  # noqa: S608
    df = _query(sql)
    df["nb_orders"] = pd.to_numeric(df["nb_orders"], errors="coerce")
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner="Chargement des quantités par pays…")
def fetch_countries_quantities() -> pd.DataFrame:
    """Retourne le mart Countries_Quantities (country, total_quantities)."""
    sql = f"SELECT country, total_quantities FROM {MART_COUNTRIES_QTY} ORDER BY total_quantities DESC"  # noqa: S608
    df = _query(sql)
    df["total_quantities"] = pd.to_numeric(df["total_quantities"], errors="coerce")
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner="Chargement de la segmentation clients…")
def fetch_customer_segmentation() -> pd.DataFrame:
    """Retourne le mart Customer_Segmentation (customer_id, customer_segment)."""
    sql = f"SELECT customer_id, customer_segment FROM {MART_CUSTOMER_SEG}"  # noqa: S608
    return _query(sql)


@st.cache_data(ttl=CACHE_TTL, show_spinner="Chargement des KPI…")
def fetch_kpis() -> dict[str, Any]:
    """Calcule les KPI globaux depuis les marts.

    Returns:
        Dictionnaire avec : total_revenue, total_orders, nb_countries,
        nb_customers, best_day, best_day_revenue, last_date.
    """
    rev_df = fetch_daily_revenue()
    status_df = fetch_status_order_count()
    countries_df = fetch_countries_quantities()
    seg_df = fetch_customer_segmentation()

    total_revenue = float(rev_df["total_price"].sum()) if not rev_df.empty else 0.0
    total_orders  = int(status_df["nb_orders"].sum()) if not status_df.empty else 0
    nb_countries  = int(countries_df["country"].nunique()) if not countries_df.empty else 0
    nb_customers  = int(seg_df["customer_id"].nunique()) if not seg_df.empty else 0

    if not rev_df.empty:
        idx_best = rev_df["total_price"].idxmax()
        best_day         = rev_df.loc[idx_best, "order_date"]
        best_day_revenue = float(rev_df.loc[idx_best, "total_price"])
        last_date        = rev_df["order_date"].max()
    else:
        best_day = best_day_revenue = last_date = None

    return {
        "total_revenue":    total_revenue,
        "total_orders":     total_orders,
        "nb_countries":     nb_countries,
        "nb_customers":     nb_customers,
        "best_day":         best_day,
        "best_day_revenue": best_day_revenue,
        "last_date":        last_date,
    }


@st.cache_data(ttl=CACHE_TTL, show_spinner="Chargement des métriques de qualité…")
def fetch_quality_metrics() -> dict[str, pd.DataFrame]:
    """Retourne les métriques de qualité (nb lignes, nulls, fraîcheur) pour chaque table."""
    results: dict[str, pd.DataFrame] = {}

    # --- Marts ---
    marts = {
        "daily_revenue":      MART_DAILY_REVENUE,
        "status_order_count": MART_STATUS_ORDER_COUNT,
        "countries_qty":      MART_COUNTRIES_QTY,
        "customer_seg":       MART_CUSTOMER_SEG,
    }
    for key, table in marts.items():
        try:
            df = _query(f"SELECT * FROM {table}")  # noqa: S608
            info = _build_quality_df(df, table)
            results[key] = info
        except Exception as exc:
            logger.warning("Qualité %s : %s", key, exc)

    # --- Raw ---
    for key, table in RAW_TABLES.items():
        try:
            df = _query(f"SELECT * FROM {table}")  # noqa: S608
            info = _build_quality_df(df, table)
            results[f"raw_{key}"] = info
        except Exception as exc:
            logger.warning("Qualité raw %s : %s", key, exc)

    return results


def _build_quality_df(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Construit un DataFrame de métriques de qualité pour *df*."""
    rows = []
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        null_rate  = round(null_count / len(df) * 100, 2) if len(df) > 0 else 0.0
        rows.append({
            "table":      table_name,
            "colonne":    col,
            "nb_lignes":  len(df),
            "nb_nulls":   null_count,
            "taux_null":  null_rate,
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=CACHE_TTL)
def fetch_row_counts() -> pd.DataFrame:
    """Retourne le nombre de lignes pour les tables raw et les marts."""
    tables = {**RAW_TABLES, **{
        "mart_daily_revenue":      MART_DAILY_REVENUE,
        "mart_status_order_count": MART_STATUS_ORDER_COUNT,
        "mart_countries_qty":      MART_COUNTRIES_QTY,
        "mart_customer_seg":       MART_CUSTOMER_SEG,
    }}
    rows = []
    for label, table in tables.items():
        try:
            df = _query(f"SELECT COUNT(*) AS nb FROM {table}")  # noqa: S608
            nb = int(df["nb"].iloc[0]) if not df.empty else 0
        except Exception:
            nb = -1
        rows.append({"table": label, "nb_lignes": nb})
    return pd.DataFrame(rows)
