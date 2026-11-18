"""
3_Ventes.py — Analyse des ventes depuis les marts dbt.

Sections :
  1. Daily_Order_Revenue  : série temporelle CA + moyenne mobile
  2. Status_Order_Count   : donut + barres par statut
  3. Countries_Quantities : top N pays + carte choroplèthe
  4. Customer_Segmentation: distribution RFM

Fallback : si Snowflake est indisponible, recalcul depuis les CSV locaux.
"""

from __future__ import annotations

import os
from datetime import date

import pandas as pd
import streamlit as st

from utils.charts import (
    chart_countries_bar,
    chart_countries_map,
    chart_daily_revenue,
    chart_segment_bar,
    chart_segment_donut,
    chart_status_bar,
    chart_status_donut,
)
from utils.config import APP_TITLE, CSV_DIR

# ---------------------------------------------------------------------------
# Configuration de la page
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=f"Analyse des ventes — {APP_TITLE}",
    page_icon="📈",
    layout="wide",
)

st.markdown(
    """
    <style>
      h2 { color: #16213e; border-bottom: 2px solid #4C78A8; padding-bottom: 6px; }
      h3 { color: #2c3e50; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Fallback CSV — recalcul des marts depuis les fichiers locaux
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def _demo_daily_revenue() -> pd.DataFrame:
    """Recalcule Daily_Order_Revenue depuis les CSV."""
    orders = pd.read_csv(os.path.join(CSV_DIR, "orders.csv"), parse_dates=["order_date"])
    items  = pd.read_csv(os.path.join(CSV_DIR, "order_items.csv"))
    items["total_price"] = items["quantity"] * items["unit_price"]
    merged = items.merge(orders[["id", "order_date"]], left_on="order_id", right_on="id")
    df = merged.groupby("order_date")["total_price"].sum().reset_index()
    df.columns = ["order_date", "total_price"]
    return df.sort_values("order_date")


@st.cache_data(ttl=600)
def _demo_status_count() -> pd.DataFrame:
    """Recalcule Status_Order_Count depuis les CSV."""
    orders = pd.read_csv(os.path.join(CSV_DIR, "orders.csv"))
    items  = pd.read_csv(os.path.join(CSV_DIR, "order_items.csv"))
    merged = orders.merge(items, left_on="id", right_on="order_id", how="left")
    df = merged.groupby("status")["id_y"].count().reset_index()
    df.columns = ["order_status", "nb_orders"]
    return df


@st.cache_data(ttl=600)
def _demo_countries_qty() -> pd.DataFrame:
    """Recalcule Countries_Quantities depuis les CSV."""
    customers = pd.read_csv(os.path.join(CSV_DIR, "customers.csv"))
    orders    = pd.read_csv(os.path.join(CSV_DIR, "orders.csv"))
    items     = pd.read_csv(os.path.join(CSV_DIR, "order_items.csv"))
    merged = (
        customers.merge(orders, left_on="id", right_on="customer_id")
                 .merge(items, left_on="id_y", right_on="order_id")
    )
    df = merged.groupby("country")["quantity"].sum().reset_index()
    df.columns = ["country", "total_quantities"]
    return df.sort_values("total_quantities", ascending=False)


@st.cache_data(ttl=600)
def _demo_customer_seg() -> pd.DataFrame:
    """Recalcule Customer_Segmentation (RFM simplifié) depuis les CSV."""
    customers = pd.read_csv(os.path.join(CSV_DIR, "customers.csv"))
    orders    = pd.read_csv(os.path.join(CSV_DIR, "orders.csv"), parse_dates=["order_date"])
    items     = pd.read_csv(os.path.join(CSV_DIR, "order_items.csv"))
    items["total_price"] = items["quantity"] * items["unit_price"]

    cte = (
        customers.merge(orders, left_on="id", right_on="customer_id")
                 .merge(items, left_on="id_y", right_on="order_id")
        .groupby("id_x")
        .agg(
            recency=("order_date", lambda x: (pd.Timestamp.now() - x.max()).days),
            frequency=("id_y", "count"),
            monetary=("total_price", "sum"),
        )
        .reset_index()
        .rename(columns={"id_x": "customer_id"})
    )
    for col, asc in [("recency", False), ("frequency", True), ("monetary", True)]:
        cte[col + "_r"] = pd.qcut(cte[col].rank(method="first"), 5, labels=False, duplicates="drop") + 1

    cte["rfm_score"] = (
        cte[["recency_r", "frequency_r", "monetary_r"]].mean(axis=1).round()
    ).astype(int)

    cte["customer_segment"] = cte["rfm_score"].map(
        lambda s: "Lost Customers" if s <= 2 else ("Need Attention" if s == 3 else "VIP Customers")
    )
    return cte[["customer_id", "customer_segment"]]


# ---------------------------------------------------------------------------
# Chargement des données avec gestion d'erreur
# ---------------------------------------------------------------------------

def _load_data(fetch_fn, demo_fn, label: str):
    """Essaie Snowflake, retombe sur CSV en cas d'erreur."""
    try:
        return fetch_fn(), False
    except Exception as exc:
        st.warning(
            f"⚠️ Snowflake indisponible pour **{label}** — mode démo activé.\n\n`{exc}`",
            icon="⚠️",
        )
        try:
            return demo_fn(), True
        except Exception as exc2:
            st.error(f"Impossible de charger les données démo pour {label} : {exc2}", icon="❌")
            return pd.DataFrame(), True


def _export_button(df: pd.DataFrame, filename: str) -> None:
    """Bouton de téléchargement CSV."""
    st.download_button(
        label="⬇️ Exporter (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Page principale
# ---------------------------------------------------------------------------
st.title("📈 Analyse des ventes")
st.markdown("Visualisations basées sur les marts dbt — données directement depuis Snowflake.")
st.divider()

try:
    from utils.db import (
        fetch_countries_quantities,
        fetch_customer_segmentation,
        fetch_daily_revenue,
        fetch_status_order_count,
    )
    _sf_available = True
except Exception:
    _sf_available = False

# ============================================================================
# SECTION 1 — Daily_Order_Revenue
# ============================================================================
st.header("📅 Chiffre d'affaires journalier")
st.markdown("*Mart : `Daily_Order_Revenue` · Grain : une ligne = une date de commande*")

rev_df, rev_demo = _load_data(
    fetch_fn=fetch_daily_revenue if _sf_available else _demo_daily_revenue,
    demo_fn=_demo_daily_revenue,
    label="Daily_Order_Revenue",
)

if not rev_df.empty:
    # --- Filtres ---
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        min_d = rev_df["order_date"].min().date() if not rev_df.empty else date(2025, 1, 1)
        max_d = rev_df["order_date"].max().date() if not rev_df.empty else date.today()
        date_range = st.date_input(
            "Plage de dates",
            value=(min_d, max_d),
            min_value=min_d,
            max_value=max_d,
            key="rev_date_range",
        )
    with col_f2:
        agg_choice = st.selectbox(
            "Agrégation temporelle",
            ["Journalier", "Hebdomadaire", "Mensuel"],
            key="rev_agg",
        )
    with col_f3:
        ma_window = st.slider("Fenêtre MM (jours)", 2, 30, 7, key="rev_ma")

    # Filtrage par date
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        d_start, d_end = date_range
        filtered_rev = rev_df[
            (rev_df["order_date"].dt.date >= d_start) &
            (rev_df["order_date"].dt.date <= d_end)
        ]
    else:
        filtered_rev = rev_df

    # Graphique
    fig_rev = chart_daily_revenue(filtered_rev, ma_window=ma_window, agg=agg_choice)
    st.plotly_chart(fig_rev, use_container_width=True)

    # --- Meilleures / pires journées ---
    if not filtered_rev.empty:
        col_best, col_worst = st.columns(2)
        idx_best  = filtered_rev["total_price"].idxmax()
        idx_worst = filtered_rev["total_price"].idxmin()
        with col_best:
            st.metric(
                "📈 Meilleure journée",
                pd.Timestamp(filtered_rev.loc[idx_best, "order_date"]).strftime("%d/%m/%Y"),
                delta=f"{filtered_rev.loc[idx_best, 'total_price']:,.0f} €".replace(",", " "),
            )
        with col_worst:
            st.metric(
                "📉 Journée la plus faible",
                pd.Timestamp(filtered_rev.loc[idx_worst, "order_date"]).strftime("%d/%m/%Y"),
                delta=f"{filtered_rev.loc[idx_worst, 'total_price']:,.0f} €".replace(",", " "),
                delta_color="inverse",
            )

    # --- Table exportable ---
    with st.expander("📋 Voir les données brutes"):
        st.dataframe(
            filtered_rev.sort_values("order_date", ascending=False)
                        .assign(order_date=lambda d: d["order_date"].dt.strftime("%d/%m/%Y"))
                        .rename(columns={"order_date": "Date", "total_price": "CA (€)"})
                        .reset_index(drop=True),
            use_container_width=True,
        )
        _export_button(filtered_rev, "daily_revenue.csv")

st.divider()

# ============================================================================
# SECTION 2 — Status_Order_Count
# ============================================================================
st.header("🏷️ Répartition des statuts de commande")
st.markdown("*Mart : `Status_Order_Count` · Grain : une ligne = un statut*")

status_df, _ = _load_data(
    fetch_fn=fetch_status_order_count if _sf_available else _demo_status_count,
    demo_fn=_demo_status_count,
    label="Status_Order_Count",
)

if not status_df.empty:
    col_donut, col_bar = st.columns(2)
    with col_donut:
        st.plotly_chart(chart_status_donut(status_df), use_container_width=True)
    with col_bar:
        st.plotly_chart(chart_status_bar(status_df), use_container_width=True)

    with st.expander("📋 Voir les données brutes"):
        total_s = status_df["nb_orders"].sum()
        display_s = status_df.copy()
        display_s["% du total"] = (display_s["nb_orders"] / total_s * 100).round(1)
        display_s.columns = ["Statut", "Nb commandes", "% du total"]
        st.dataframe(display_s, use_container_width=True, hide_index=True)
        _export_button(status_df, "status_order_count.csv")

st.divider()

# ============================================================================
# SECTION 3 — Countries_Quantities
# ============================================================================
st.header("🌍 Quantités par pays")
st.markdown("*Mart : `Countries_Quantities` · Grain : une ligne = un pays*")

cty_df, _ = _load_data(
    fetch_fn=fetch_countries_quantities if _sf_available else _demo_countries_qty,
    demo_fn=_demo_countries_qty,
    label="Countries_Quantities",
)

if not cty_df.empty:
    top_n = st.slider(
        "Nombre de pays (Top N)",
        min_value=5,
        max_value=min(50, len(cty_df)),
        value=min(15, len(cty_df)),
        key="cty_topn",
    )

    col_bar_cty, col_map = st.columns([1, 1])
    with col_bar_cty:
        st.plotly_chart(chart_countries_bar(cty_df, top_n=top_n), use_container_width=True)
    with col_map:
        st.plotly_chart(chart_countries_map(cty_df), use_container_width=True)

    with st.expander("📋 Voir les données brutes"):
        st.dataframe(
            cty_df.rename(columns={"country": "Pays", "total_quantities": "Quantités totales"}),
            use_container_width=True,
            hide_index=True,
        )
        _export_button(cty_df, "countries_quantities.csv")

st.divider()

# ============================================================================
# SECTION 4 — Customer_Segmentation (RFM)
# ============================================================================
st.header("👤 Segmentation clients (RFM)")
st.markdown(
    "*Mart : `Customer_Segmentation` · Grain : une ligne = un client · "
    "Segments : VIP Customers, Need Attention, Lost Customers*"
)

seg_df, _ = _load_data(
    fetch_fn=fetch_customer_segmentation if _sf_available else _demo_customer_seg,
    demo_fn=_demo_customer_seg,
    label="Customer_Segmentation",
)

if not seg_df.empty:
    col_seg_donut, col_seg_bar = st.columns(2)
    with col_seg_donut:
        st.plotly_chart(chart_segment_donut(seg_df), use_container_width=True)
    with col_seg_bar:
        st.plotly_chart(chart_segment_bar(seg_df), use_container_width=True)

    # Métriques par segment
    st.subheader("Métriques par segment")
    seg_counts = seg_df["customer_segment"].value_counts()
    total_seg  = len(seg_df)

    seg_cols = st.columns(len(seg_counts))
    colors = {
        "VIP Customers":    "🟢",
        "Need Attention":   "🟡",
        "Lost Customers":   "🔴",
    }
    for i, (seg, cnt) in enumerate(seg_counts.items()):
        with seg_cols[i]:
            icon = colors.get(seg, "⚪")
            pct  = cnt / total_seg * 100
            st.metric(
                label=f"{icon} {seg}",
                value=f"{cnt} clients",
                delta=f"{pct:.1f} % du total",
            )

    with st.expander("📋 Voir les données brutes"):
        st.dataframe(
            seg_df.rename(columns={"customer_id": "ID Client", "customer_segment": "Segment"}),
            use_container_width=True,
            hide_index=True,
        )
        _export_button(seg_df, "customer_segmentation.csv")
