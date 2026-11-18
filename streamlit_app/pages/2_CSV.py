"""
2_CSV.py — Exploration des fichiers CSV sources.

Fonctionnalités :
  - Onglets : customers, orders, order_items, products + uploader ad hoc.
  - Pour chaque fichier : aperçu, dimensions, types, valeurs manquantes,
    describe(), doublons, graphique auto (histogramme ou barres), téléchargement.
  - Vérification de l'intégrité référentielle entre fichiers.
"""

from __future__ import annotations

import os
from io import StringIO

import pandas as pd
import streamlit as st

from utils.charts import chart_bar_categorical, chart_histogram
from utils.config import APP_TITLE, CSV_DIR

# ---------------------------------------------------------------------------
# Configuration de la page
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=f"Exploration CSV — {APP_TITLE}",
    page_icon="📂",
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
# Chargement des CSV
# ---------------------------------------------------------------------------

CSV_FILES: dict[str, str] = {
    "customers":   "customers.csv",
    "orders":      "orders.csv",
    "order_items": "order_items.csv",
    "products":    "products.csv",
}

PARSE_DATES: dict[str, list[str]] = {
    "orders": ["order_date"],
}


@st.cache_data(show_spinner=False)
def _load_csv(filename: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    """Charge un CSV depuis le dossier monté."""
    path = os.path.join(CSV_DIR, filename)
    return pd.read_csv(path, parse_dates=parse_dates or [])


def _load_all_csvs() -> dict[str, pd.DataFrame | None]:
    dfs: dict[str, pd.DataFrame | None] = {}
    for key, fname in CSV_FILES.items():
        try:
            dfs[key] = _load_csv(fname, PARSE_DATES.get(key))
        except FileNotFoundError:
            dfs[key] = None
    return dfs


# ---------------------------------------------------------------------------
# Helpers d'affichage
# ---------------------------------------------------------------------------

def _show_file_analysis(df: pd.DataFrame, label: str) -> None:
    """Affiche l'analyse complète d'un DataFrame CSV."""
    if df is None:
        st.error(f"Fichier introuvable : {CSV_FILES.get(label, label)}")
        return

    # --- Métriques rapides ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Lignes", f"{df.shape[0]:,}".replace(",", " "))
    col2.metric("Colonnes", df.shape[1])
    col3.metric("Valeurs manquantes", int(df.isna().sum().sum()))
    col4.metric("Doublons complets", int(df.duplicated().sum()))

    # --- Aperçu ---
    st.subheader("Aperçu")
    n_rows = st.slider(
        "Nombre de lignes à afficher",
        min_value=5,
        max_value=min(100, len(df)),
        value=10,
        key=f"slider_{label}",
    )
    st.dataframe(df.head(n_rows), use_container_width=True)

    # --- Types et valeurs manquantes ---
    with st.expander("📋 Types de colonnes & valeurs manquantes"):
        info_df = pd.DataFrame({
            "Colonne":    df.columns,
            "Type":       df.dtypes.astype(str).values,
            "Nb nulls":   df.isna().sum().values,
            "% nulls":    (df.isna().sum() / len(df) * 100).round(2).values,
            "Nb uniques": df.nunique().values,
        })
        st.dataframe(info_df, use_container_width=True, hide_index=True)

    # --- Statistiques descriptives ---
    with st.expander("📊 Statistiques descriptives"):
        num_cols = df.select_dtypes("number").columns.tolist()
        if num_cols:
            st.dataframe(df[num_cols].describe().T.round(2), use_container_width=True)
        else:
            st.info("Aucune colonne numérique.")

    # --- Graphique automatique ---
    st.subheader("Visualisation rapide")
    all_cols = df.columns.tolist()
    selected_col = st.selectbox(
        "Colonne à visualiser",
        options=all_cols,
        key=f"viz_col_{label}",
    )
    if selected_col:
        if pd.api.types.is_numeric_dtype(df[selected_col]):
            fig = chart_histogram(df, selected_col)
        else:
            fig = chart_bar_categorical(df, selected_col)
        st.plotly_chart(fig, use_container_width=True)

    # --- Téléchargement ---
    st.subheader("Téléchargement")
    _download_button(df, f"{label}_export.csv")


def _download_button(df: pd.DataFrame, filename: str) -> None:
    """Affiche un bouton de téléchargement CSV."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Télécharger (CSV)",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Vérification de l'intégrité référentielle
# ---------------------------------------------------------------------------

def _referential_integrity_check(dfs: dict[str, pd.DataFrame | None]) -> None:
    """Vérifie et affiche les violations d'intégrité entre fichiers CSV."""
    st.header("🔗 Intégrité référentielle")

    checks = [
        {
            "label":   "Commandes → Clients",
            "detail":  "orders.customer_id non trouvé dans customers.id",
            "left":    "orders",
            "right":   "customers",
            "left_col": "customer_id",
            "right_col": "id",
        },
        {
            "label":   "Lignes de commande → Commandes",
            "detail":  "order_items.order_id non trouvé dans orders.id",
            "left":    "order_items",
            "right":   "orders",
            "left_col": "order_id",
            "right_col": "id",
        },
        {
            "label":   "Lignes de commande → Produits",
            "detail":  "order_items.product_id non trouvé dans products.id",
            "left":    "order_items",
            "right":   "products",
            "left_col": "product_id",
            "right_col": "id",
        },
    ]

    cols = st.columns(len(checks))
    for col, check in zip(cols, checks, strict=False):
        left_df  = dfs.get(check["left"])
        right_df = dfs.get(check["right"])

        with col:
            st.markdown(f"**{check['label']}**")
            st.caption(check["detail"])
            if left_df is None or right_df is None:
                st.warning("Données manquantes")
                continue

            right_keys = set(right_df[check["right_col"]].dropna().unique())
            orphans    = left_df[~left_df[check["left_col"]].isin(right_keys)]
            count      = len(orphans)

            if count == 0:
                st.success(f"✅ OK — 0 orphelin")
            else:
                st.error(f"❌ {count} orphelin(s) détecté(s)")
                with st.expander("Voir les lignes orphelines"):
                    st.dataframe(orphans.head(50), use_container_width=True)


# ---------------------------------------------------------------------------
# Page principale
# ---------------------------------------------------------------------------
st.title("📂 Exploration des fichiers CSV")
st.markdown("Analyse exploratoire des données sources avant chargement dans Snowflake.")
st.divider()

# Chargement
dfs = _load_all_csvs()
missing = [k for k, v in dfs.items() if v is None]
if missing:
    st.warning(
        f"Fichier(s) introuvable(s) dans `{CSV_DIR}` : {', '.join(missing)}. "
        "Vérifiez le volume Docker et la variable d'environnement `CSV_DIR`.",
        icon="⚠️",
    )

# Onglets
tab_labels = ["👥 Customers", "🛒 Orders", "📦 Order Items", "🏷️ Products", "📤 Uploader"]
tab_cust, tab_orders, tab_items, tab_prod, tab_upload = st.tabs(tab_labels)

with tab_cust:
    _show_file_analysis(dfs.get("customers"), "customers")

with tab_orders:
    _show_file_analysis(dfs.get("orders"), "orders")

with tab_items:
    _show_file_analysis(dfs.get("order_items"), "order_items")

with tab_prod:
    _show_file_analysis(dfs.get("products"), "products")

with tab_upload:
    st.subheader("📤 Charger un fichier CSV personnalisé")
    uploaded = st.file_uploader("Sélectionnez un fichier CSV", type=["csv"])
    if uploaded is not None:
        try:
            custom_df = pd.read_csv(uploaded)
            st.success(f"Fichier chargé : {uploaded.name} ({custom_df.shape[0]} lignes, {custom_df.shape[1]} colonnes)")
            _show_file_analysis(custom_df, uploaded.name.replace(".csv", ""))
        except Exception as exc:
            st.error(f"Erreur lors du chargement : {exc}", icon="❌")
    else:
        st.info("Aucun fichier chargé. Glissez-déposez un CSV ci-dessus.", icon="📂")

# Intégrité référentielle
st.divider()
_referential_integrity_check(dfs)
