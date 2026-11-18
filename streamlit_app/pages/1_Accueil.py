"""
1_Accueil.py — Page d'accueil : description du projet, diagramme du pipeline
et KPI cards calculés depuis les marts Snowflake.

Fallback : si Snowflake est inaccessible, les KPI sont calculés depuis les CSV locaux.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from utils.config import APP_SUBTITLE, APP_TITLE, CSV_DIR

# ---------------------------------------------------------------------------
# Configuration de la page
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=f"Accueil — {APP_TITLE}",
    page_icon="🏠",
    layout="wide",
)

# CSS hérité
st.markdown(
    """
    <style>
      div[data-testid="metric-container"] {
          background: #ffffff;
          border: 1px solid #e8eaed;
          border-radius: 12px;
          padding: 18px 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.07);
      }
      div[data-testid="metric-container"] > label {
          font-size: 0.82rem; color: #666;
          font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
      }
      div[data-testid="metric-container"] > div {
          font-size: 1.7rem; font-weight: 700; color: #1a1a2e;
      }
      h2 { color: #16213e; border-bottom: 2px solid #4C78A8; padding-bottom: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------------
st.title("🏠 Accueil — Sales Data Pipeline")
st.markdown(f"##### {APP_SUBTITLE}")
st.divider()

# ---------------------------------------------------------------------------
# Description du projet
# ---------------------------------------------------------------------------
st.header("📖 À propos du projet")
col_desc, col_tech = st.columns([2, 1])

with col_desc:
    st.markdown(
        """
        Ce projet implémente un **pipeline ELT complet** pour l'analyse des ventes,
        depuis l'ingestion de fichiers CSV bruts jusqu'à la visualisation interactive.

        Les données passent par plusieurs couches de transformation :
        - **Raw** : chargement des CSV dans Snowflake sans transformation.
        - **Staging** : nettoyage, déduplication et typage fort via dbt.
        - **Marts** : agrégations métier (revenu, statuts, géographie, segmentation RFM).

        L'orchestration est assurée par **Apache Airflow** (planification quotidienne à minuit).
        La visualisation est disponible via **Power BI** et cette application **Streamlit**.
        """
    )

with col_tech:
    st.markdown("**Stack technique**")
    st.markdown(
        """
        | Couche | Technologie |
        |--------|-------------|
        | Ingestion | CSV → Snowflake |
        | Stockage | Snowflake |
        | Transform. | dbt Core |
        | Orchestration | Apache Airflow |
        | Conteneurs | Docker Compose |
        | Viz BI | Power BI |
        | Viz Web | Streamlit |
        """
    )

st.divider()

# ---------------------------------------------------------------------------
# Diagramme du pipeline (Mermaid via st.markdown HTML)
# ---------------------------------------------------------------------------
st.header("🔄 Architecture du pipeline")

pipeline_mermaid = """
```mermaid
flowchart LR
    CSV["📄 CSV Files<br/>customers · orders<br/>order_items · products"]
    SF_RAW["❄️ Snowflake<br/>Schema : RAW"]
    DBT["⚙️ dbt Core<br/>Staging → Marts"]
    SF_MARTS["❄️ Snowflake<br/>Schema : MARTS"]
    AIRFLOW["🌀 Apache Airflow<br/>Orchestration<br/>DAG quotidien"]
    POWERBI["📊 Power BI<br/>Rapports"]
    STREAMLIT["🚀 Streamlit<br/>App interactive"]
    DOCKER["🐳 Docker Compose<br/>Conteneurs"]

    CSV -->|COPY INTO| SF_RAW
    SF_RAW -->|dbt run| DBT
    DBT --> SF_MARTS
    AIRFLOW -->|déclenche| DBT
    SF_MARTS --> POWERBI
    SF_MARTS --> STREAMLIT
    DOCKER -.->|héberge| AIRFLOW
    DOCKER -.->|héberge| STREAMLIT
```
"""

st.markdown(pipeline_mermaid)
st.divider()

# ---------------------------------------------------------------------------
# KPI — chargement Snowflake avec fallback CSV
# ---------------------------------------------------------------------------
st.header("📊 Indicateurs clés (KPI)")


@st.cache_data(ttl=600)
def _load_kpis_from_csv() -> dict:
    """Calcule les KPI directement depuis les CSV locaux (mode démo)."""
    try:
        customers_path   = os.path.join(CSV_DIR, "customers.csv")
        orders_path      = os.path.join(CSV_DIR, "orders.csv")
        order_items_path = os.path.join(CSV_DIR, "order_items.csv")

        cust = pd.read_csv(customers_path)
        orders = pd.read_csv(orders_path, parse_dates=["order_date"])
        items  = pd.read_csv(order_items_path)

        items["total_price"] = items["quantity"] * items["unit_price"]
        daily = items.merge(orders[["id", "order_date"]], left_on="order_id", right_on="id")
        daily_rev = daily.groupby("order_date")["total_price"].sum().reset_index()
        daily_rev.columns = ["order_date", "total_price"]

        total_revenue = float(items["total_price"].sum())
        total_orders  = int(orders["id"].nunique())
        nb_countries  = int(cust["country"].nunique())
        nb_customers  = int(cust["id"].nunique())

        if not daily_rev.empty:
            idx_best         = daily_rev["total_price"].idxmax()
            best_day         = daily_rev.loc[idx_best, "order_date"]
            best_day_revenue = float(daily_rev.loc[idx_best, "total_price"])
            last_date        = orders["order_date"].max()
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
    except Exception as exc:
        return {"error": str(exc)}


# Essai Snowflake
kpis = None
demo_mode = False

try:
    from utils.db import fetch_kpis
    kpis = fetch_kpis()
except Exception as exc:
    st.warning(
        f"⚠️ Snowflake inaccessible — affichage en **mode démo** (CSV locaux).\n\n`{exc}`",
        icon="⚠️",
    )
    demo_mode = True
    kpis = _load_kpis_from_csv()

if kpis and "error" not in kpis:
    if demo_mode:
        st.info("📂 KPI calculés depuis les fichiers CSV locaux.", icon="📂")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    # Formatage des valeurs
    total_revenue    = kpis.get("total_revenue", 0)
    total_orders     = kpis.get("total_orders", 0)
    nb_countries     = kpis.get("nb_countries", 0)
    nb_customers     = kpis.get("nb_customers", 0)
    best_day         = kpis.get("best_day")
    best_day_revenue = kpis.get("best_day_revenue", 0)
    last_date        = kpis.get("last_date")

    best_day_str  = pd.Timestamp(best_day).strftime("%d/%m/%Y") if best_day is not None else "N/A"
    last_date_str = pd.Timestamp(last_date).strftime("%d/%m/%Y") if last_date is not None else "N/A"

    with c1:
        st.metric(
            label="💰 Chiffre d'affaires total",
            value=f"{total_revenue:,.0f} €".replace(",", " "),
        )
    with c2:
        st.metric(label="🛒 Total commandes", value=f"{total_orders:,}".replace(",", " "))
    with c3:
        st.metric(label="🌍 Pays actifs", value=f"{nb_countries}")
    with c4:
        st.metric(label="👤 Clients", value=f"{nb_customers}")
    with c5:
        st.metric(
            label="📈 Meilleur jour",
            value=best_day_str,
            delta=f"{best_day_revenue:,.0f} €".replace(",", " "),
        )
    with c6:
        st.metric(label="📅 Dernière donnée", value=last_date_str)

else:
    st.error(
        f"Impossible de charger les KPI : {kpis.get('error', 'Erreur inconnue')}",
        icon="❌",
    )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "Sales Data Pipeline · Données issues de Snowflake (marts dbt) · "
    "Rafraîchissement automatique toutes les 10 minutes."
)
