"""
app.py — Point d'entrée de l'application Streamlit.

Exécuter avec :
    streamlit run app.py

Structure des pages (numérotées pour le tri automatique) :
    pages/1_Accueil.py
    pages/2_CSV.py
    pages/3_Ventes.py
    pages/4_Qualite.py
"""

import streamlit as st

from utils.config import APP_TITLE, APP_SUBTITLE

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": f"**{APP_TITLE}** — {APP_SUBTITLE}",
    },
)

# CSS global — KPI cards + sidebar branding
st.markdown(
    """
    <style>
      /* ---- KPI cards ---- */
      div[data-testid="metric-container"] {
          background: #ffffff;
          border: 1px solid #e8eaed;
          border-radius: 12px;
          padding: 18px 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.07);
      }
      div[data-testid="metric-container"] > label {
          font-size: 0.82rem;
          color: #666;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
      }
      div[data-testid="metric-container"] > div {
          font-size: 1.7rem;
          font-weight: 700;
          color: #1a1a2e;
      }

      /* ---- Sidebar ---- */
      section[data-testid="stSidebar"] {
          background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
      }
      section[data-testid="stSidebar"] * {
          color: #e8eaed !important;
      }
      section[data-testid="stSidebar"] .stSelectbox label,
      section[data-testid="stSidebar"] p {
          color: #adb5bd !important;
      }

      /* ---- General ---- */
      .block-container { padding-top: 1.5rem; }
      h1 { color: #1a1a2e; }
      h2 { color: #16213e; border-bottom: 2px solid #4C78A8; padding-bottom: 6px; }
      h3 { color: #2c3e50; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — navigation & branding
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 📊 Sales Pipeline")
    st.markdown(f"*{APP_SUBTITLE}*")
    st.divider()
    st.markdown(
        """
        **Navigation**
        - 🏠 Accueil & KPI
        - 📂 Exploration des CSV
        - 📈 Analyse des ventes
        - 🔍 Qualité & Pipeline
        """,
    )
    st.divider()
    st.caption("Données rafraîchies toutes les 10 min.")

# ---------------------------------------------------------------------------
# Page d'accueil par défaut (redirigée vers pages/1_Accueil.py)
# ---------------------------------------------------------------------------
st.title("📊 Sales Data Pipeline")
st.info(
    "👈 Sélectionnez une page dans le menu latéral pour commencer.",
    icon="ℹ️",
)
