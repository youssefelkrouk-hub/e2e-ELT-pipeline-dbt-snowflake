"""
4_Qualite.py — Qualité des données et état du pipeline.

Sections :
  1. Volumétrie : nb lignes tables raw vs marts.
  2. Fraîcheur : max(order_date) dans les marts contenant une date.
  3. Taux de nullité par colonne pour chaque mart.
  4. Statut du dernier run Airflow (via REST API si AIRFLOW_URL défini).
"""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

from utils.charts import chart_null_rates, chart_row_counts
from utils.config import (
    AIRFLOW_DAG_ID,
    AIRFLOW_PASSWORD,
    AIRFLOW_URL,
    AIRFLOW_USER,
    APP_TITLE,
    CSV_DIR,
)

# ---------------------------------------------------------------------------
# Configuration de la page
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=f"Qualité & Pipeline — {APP_TITLE}",
    page_icon="🔍",
    layout="wide",
)

st.markdown(
    """
    <style>
      h2 { color: #16213e; border-bottom: 2px solid #4C78A8; padding-bottom: 6px; }
      h3 { color: #2c3e50; }
      div[data-testid="metric-container"] {
          background: #fff; border: 1px solid #e8eaed;
          border-radius: 12px; padding: 18px 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.07);
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Page principale
# ---------------------------------------------------------------------------
st.title("🔍 Qualité des données & Pipeline")
st.markdown("Surveillance de la volumétrie, de la fraîcheur et de l'intégrité du pipeline.")
st.divider()

# ============================================================================
# 1. Volumétrie
# ============================================================================
st.header("📊 Volumétrie des tables")

try:
    from utils.db import fetch_row_counts
    row_counts_df = fetch_row_counts()
    sf_ok = True
except Exception as exc:
    st.warning(
        f"⚠️ Snowflake inaccessible — volumétrie calculée depuis les CSV locaux.\n\n`{exc}`",
        icon="⚠️",
    )
    sf_ok = False
    # Fallback : compter les lignes des CSV
    csv_rows = []
    for fname in ["customers.csv", "orders.csv", "order_items.csv", "products.csv"]:
        path = os.path.join(CSV_DIR, fname)
        try:
            nb = sum(1 for _ in open(path, encoding="utf-8")) - 1  # -1 pour le header
        except FileNotFoundError:
            nb = -1
        csv_rows.append({"table": fname.replace(".csv", ""), "nb_lignes": nb})
    row_counts_df = pd.DataFrame(csv_rows)

if not row_counts_df.empty:
    col_chart, col_table = st.columns([2, 1])
    with col_chart:
        st.plotly_chart(chart_row_counts(row_counts_df), use_container_width=True)
    with col_table:
        st.dataframe(
            row_counts_df.rename(columns={"table": "Table", "nb_lignes": "Nb lignes"})
                         .sort_values("Nb lignes", ascending=False)
                         .reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

st.divider()

# ============================================================================
# 2. Fraîcheur des données
# ============================================================================
st.header("📅 Fraîcheur des données")

if sf_ok:
    try:
        from utils.db import fetch_daily_revenue

        rev_df = fetch_daily_revenue()
        if not rev_df.empty:
            last_date = rev_df["order_date"].max()
            days_ago  = (pd.Timestamp.now().normalize() - pd.Timestamp(last_date).normalize()).days

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.metric(
                    "🕐 Dernière date de commande",
                    pd.Timestamp(last_date).strftime("%d/%m/%Y"),
                    delta=f"{days_ago} jour(s) depuis aujourd'hui",
                    delta_color="inverse" if days_ago > 7 else "normal",
                )
            with col_f2:
                freshness_status = "✅ Données fraîches" if days_ago <= 1 else f"⚠️ {days_ago} jours sans nouvelles données"
                st.metric("Statut fraîcheur", freshness_status)
        else:
            st.info("Aucune donnée de date disponible.", icon="ℹ️")
    except Exception as exc:
        st.error(f"Impossible de récupérer la fraîcheur : {exc}", icon="❌")
else:
    # Fallback CSV
    try:
        orders_df = pd.read_csv(
            os.path.join(CSV_DIR, "orders.csv"), parse_dates=["order_date"]
        )
        last_date = orders_df["order_date"].max()
        st.metric(
            "🕐 Dernière date de commande (CSV local)",
            pd.Timestamp(last_date).strftime("%d/%m/%Y"),
        )
    except Exception:
        st.warning("Impossible de déterminer la fraîcheur depuis les CSV.", icon="⚠️")

st.divider()

# ============================================================================
# 3. Taux de nullité par colonne
# ============================================================================
st.header("🔎 Taux de nullité par colonne")

if sf_ok:
    try:
        from utils.db import fetch_quality_metrics

        quality = fetch_quality_metrics()
        if quality:
            mart_keys = [k for k in quality if not k.startswith("raw_")]
            raw_keys  = [k for k in quality if k.startswith("raw_")]

            tabs_labels = ["Marts"] + ["Tables RAW"]
            tab_marts, tab_raw = st.tabs(tabs_labels)

            with tab_marts:
                for key in mart_keys:
                    df_q = quality[key]
                    with st.expander(f"📋 {key.replace('_', ' ').title()}", expanded=False):
                        col_c, col_t = st.columns([2, 1])
                        with col_c:
                            st.plotly_chart(chart_null_rates(df_q), use_container_width=True)
                        with col_t:
                            display = df_q[["colonne", "nb_lignes", "nb_nulls", "taux_null"]].copy()
                            display.columns = ["Colonne", "Nb lignes", "Nb nulls", "% null"]
                            st.dataframe(display, use_container_width=True, hide_index=True)

            with tab_raw:
                for key in raw_keys:
                    df_q = quality[key]
                    with st.expander(f"📋 {key.replace('raw_', '').title()}", expanded=False):
                        col_c, col_t = st.columns([2, 1])
                        with col_c:
                            st.plotly_chart(chart_null_rates(df_q), use_container_width=True)
                        with col_t:
                            display = df_q[["colonne", "nb_lignes", "nb_nulls", "taux_null"]].copy()
                            display.columns = ["Colonne", "Nb lignes", "Nb nulls", "% null"]
                            st.dataframe(display, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune métrique de qualité disponible.", icon="ℹ️")
    except Exception as exc:
        st.error(f"Impossible de charger les métriques de qualité : {exc}", icon="❌")
else:
    # Fallback : calculer sur les CSV locaux
    st.info("📂 Métriques de qualité calculées depuis les CSV locaux.", icon="📂")
    for fname in ["customers.csv", "orders.csv", "order_items.csv", "products.csv"]:
        path = os.path.join(CSV_DIR, fname)
        try:
            df_local = pd.read_csv(path)
            null_info = pd.DataFrame({
                "colonne":   df_local.columns,
                "taux_null": (df_local.isna().sum() / len(df_local) * 100).round(2).values,
                "nb_nulls":  df_local.isna().sum().values,
                "nb_lignes": len(df_local),
            })
            with st.expander(f"📋 {fname}"):
                col_c, col_t = st.columns([2, 1])
                with col_c:
                    st.plotly_chart(chart_null_rates(null_info), use_container_width=True)
                with col_t:
                    st.dataframe(null_info, use_container_width=True, hide_index=True)
        except FileNotFoundError:
            st.warning(f"Fichier introuvable : {fname}", icon="⚠️")

st.divider()

# ============================================================================
# 4. Statut Airflow
# ============================================================================
st.header("🌀 État du pipeline Airflow")

if not AIRFLOW_URL:
    st.info(
        "La variable d'environnement `AIRFLOW_URL` n'est pas définie. "
        "Ajoutez-la dans votre `.env` pour afficher l'état du pipeline.",
        icon="ℹ️",
    )
else:
    @st.cache_data(ttl=120, show_spinner="Interrogation de l'API Airflow…")
    def _fetch_airflow_dag_runs(
        base_url: str,
        dag_id: str,
        user: str,
        password: str,
    ) -> list[dict]:
        """Récupère les derniers runs du DAG via l'API REST Airflow."""
        url = f"{base_url.rstrip('/')}/api/v1/dags/{dag_id}/dagRuns"
        resp = requests.get(
            url,
            auth=(user, password),
            params={"order_by": "-start_date", "limit": 5},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("dag_runs", [])

    try:
        runs = _fetch_airflow_dag_runs(AIRFLOW_URL, AIRFLOW_DAG_ID, AIRFLOW_USER, AIRFLOW_PASSWORD)
        if not runs:
            st.info(f"Aucun run trouvé pour le DAG `{AIRFLOW_DAG_ID}`.", icon="ℹ️")
        else:
            # Dernier run
            last_run = runs[0]
            state    = last_run.get("state", "unknown")
            start    = last_run.get("start_date", "")
            end      = last_run.get("end_date", "") or "En cours…"

            state_icon = {
                "success": "✅",
                "failed":  "❌",
                "running": "⏳",
            }.get(state, "❓")

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("Statut du dernier run", f"{state_icon} {state.capitalize()}")
            with col_s2:
                try:
                    dt_start = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    st.metric("Démarré le", dt_start.strftime("%d/%m/%Y %H:%M"))
                except Exception:
                    st.metric("Démarré le", start)
            with col_s3:
                st.metric("Terminé le", end if end == "En cours…" else end[:19])

            # Historique des runs
            st.subheader("Historique des runs récents")
            runs_df = pd.DataFrame([
                {
                    "Run ID":    r.get("run_id", ""),
                    "Statut":    r.get("state", ""),
                    "Début":     r.get("start_date", "")[:19],
                    "Fin":       (r.get("end_date") or "—")[:19],
                }
                for r in runs
            ])
            st.dataframe(runs_df, use_container_width=True, hide_index=True)

    except requests.exceptions.ConnectionError:
        st.warning(
            f"Impossible de joindre Airflow à `{AIRFLOW_URL}`. "
            "Vérifiez que le service est démarré et que `AIRFLOW_URL` est correcte.",
            icon="⚠️",
        )
    except requests.exceptions.HTTPError as exc:
        st.warning(
            f"Erreur HTTP lors de l'appel à l'API Airflow : {exc}. "
            "Vérifiez `AIRFLOW_USER` et `AIRFLOW_PASSWORD`.",
            icon="⚠️",
        )
    except Exception as exc:
        st.error(f"Erreur inattendue lors de l'appel Airflow : {exc}", icon="❌")
