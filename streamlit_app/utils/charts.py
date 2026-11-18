"""
charts.py — Fonctions de visualisation Plotly Express réutilisables.

Toutes les fonctions retournent un go.Figure Plotly prêt à l'affichage.
La palette de couleurs et le template sont définis dans config.py.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.config import COLOR_PALETTE, PLOTLY_TEMPLATE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_layout(fig: go.Figure, title: str = "") -> go.Figure:
    """Applique le layout commun (template, marges, titre) à une figure."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title={"text": title, "x": 0.03, "font": {"size": 16}},
        margin={"t": 60, "l": 20, "r": 20, "b": 40},
        font={"family": "Inter, Arial, sans-serif"},
        legend={"orientation": "h", "y": -0.15},
    )
    return fig


# ---------------------------------------------------------------------------
# Daily Revenue
# ---------------------------------------------------------------------------

def chart_daily_revenue(
    df: pd.DataFrame,
    ma_window: int = 7,
    agg: str = "Journalier",
) -> go.Figure:
    """Graphique ligne/area du chiffre d'affaires avec moyenne mobile.

    Args:
        df:        DataFrame avec colonnes order_date et total_price.
        ma_window: Fenêtre de la moyenne mobile en jours.
        agg:       Agrégation temporelle : 'Journalier', 'Hebdomadaire', 'Mensuel'.

    Returns:
        Figure Plotly.
    """
    if df.empty:
        return _empty_fig("Aucune donnée de revenu disponible")

    df = df.copy().sort_values("order_date")

    if agg == "Hebdomadaire":
        df = df.resample("W", on="order_date")["total_price"].sum().reset_index()
    elif agg == "Mensuel":
        df = df.resample("ME", on="order_date")["total_price"].sum().reset_index()

    df["ma"] = df["total_price"].rolling(window=ma_window, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["order_date"],
        y=df["total_price"],
        name="CA",
        fill="tozeroy",
        line={"color": COLOR_PALETTE[0], "width": 2},
        fillcolor=f"rgba(76,120,168,0.15)",
        hovertemplate="%{x|%d/%m/%Y}<br>CA : %{y:,.0f} €<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["order_date"],
        y=df["ma"],
        name=f"Moy. mobile {ma_window}j",
        line={"color": COLOR_PALETTE[1], "width": 2, "dash": "dash"},
        hovertemplate="%{x|%d/%m/%Y}<br>MM{ma_window}j : %{y:,.0f} €<extra></extra>",
    ))
    fig.update_yaxes(title_text="Chiffre d'affaires (€)", tickformat=",.0f")
    fig.update_xaxes(title_text="Date")
    return _base_layout(fig, f"Chiffre d'affaires — {agg}")


# ---------------------------------------------------------------------------
# Status Order Count
# ---------------------------------------------------------------------------

def chart_status_donut(df: pd.DataFrame) -> go.Figure:
    """Donut chart des commandes par statut.

    Args:
        df: DataFrame avec colonnes order_status et nb_orders.

    Returns:
        Figure Plotly.
    """
    if df.empty:
        return _empty_fig("Aucune donnée de statut disponible")

    fig = px.pie(
        df,
        names="order_status",
        values="nb_orders",
        hole=0.5,
        color_discrete_sequence=COLOR_PALETTE,
    )
    fig.update_traces(
        textinfo="percent+label",
        hovertemplate="%{label}<br>Commandes : %{value:,}<br>%{percent}<extra></extra>",
    )
    return _base_layout(fig, "Répartition des commandes par statut")


def chart_status_bar(df: pd.DataFrame) -> go.Figure:
    """Bar chart horizontal des commandes par statut avec pourcentages.

    Args:
        df: DataFrame avec colonnes order_status et nb_orders.

    Returns:
        Figure Plotly.
    """
    if df.empty:
        return _empty_fig("Aucune donnée de statut disponible")

    df = df.copy()
    total = df["nb_orders"].sum()
    df["pct"] = (df["nb_orders"] / total * 100).round(1)
    df = df.sort_values("nb_orders", ascending=True)

    fig = px.bar(
        df,
        x="nb_orders",
        y="order_status",
        orientation="h",
        text=df["pct"].map(lambda x: f"{x:.1f} %"),
        color="order_status",
        color_discrete_sequence=COLOR_PALETTE,
    )
    fig.update_traces(textposition="outside")
    fig.update_xaxes(title_text="Nombre de commandes")
    fig.update_yaxes(title_text="Statut")
    fig.update_layout(showlegend=False)
    return _base_layout(fig, "Nombre de commandes par statut")


# ---------------------------------------------------------------------------
# Countries Quantities
# ---------------------------------------------------------------------------

def chart_countries_bar(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Bar chart des top N pays par quantités commandées.

    Args:
        df:    DataFrame avec colonnes country et total_quantities.
        top_n: Nombre de pays à afficher.

    Returns:
        Figure Plotly.
    """
    if df.empty:
        return _empty_fig("Aucune donnée de pays disponible")

    df_top = df.nlargest(top_n, "total_quantities").sort_values(
        "total_quantities", ascending=True
    )
    fig = px.bar(
        df_top,
        x="total_quantities",
        y="country",
        orientation="h",
        color="total_quantities",
        color_continuous_scale=["#c6dbef", "#084594"],
        text="total_quantities",
    )
    fig.update_traces(textposition="outside")
    fig.update_coloraxes(showscale=False)
    fig.update_xaxes(title_text="Quantités totales")
    fig.update_yaxes(title_text="Pays")
    return _base_layout(fig, f"Top {top_n} pays — Quantités commandées")


def chart_countries_map(df: pd.DataFrame) -> go.Figure:
    """Choropleth mondial des quantités par pays.

    Args:
        df: DataFrame avec colonnes country et total_quantities.

    Returns:
        Figure Plotly.
    """
    if df.empty:
        return _empty_fig("Aucune donnée géographique disponible")

    fig = px.choropleth(
        df,
        locations="country",
        locationmode="country names",
        color="total_quantities",
        color_continuous_scale="Blues",
        labels={"total_quantities": "Quantités", "country": "Pays"},
        hover_name="country",
        hover_data={"total_quantities": ":,"},
    )
    fig.update_layout(
        geo={"showframe": False, "showcoastlines": True, "projection_type": "natural earth"},
        coloraxis_colorbar={"title": "Quantités"},
    )
    return _base_layout(fig, "Carte mondiale des quantités commandées")


# ---------------------------------------------------------------------------
# Customer Segmentation
# ---------------------------------------------------------------------------

def chart_segment_donut(df: pd.DataFrame) -> go.Figure:
    """Donut chart de la répartition des segments clients (RFM).

    Args:
        df: DataFrame avec colonnes customer_id et customer_segment.

    Returns:
        Figure Plotly.
    """
    if df.empty:
        return _empty_fig("Aucune donnée de segmentation disponible")

    counts = df["customer_segment"].value_counts().reset_index()
    counts.columns = ["segment", "nb_clients"]

    # Couleurs sémantiques
    color_map = {
        "VIP Customers":    COLOR_PALETTE[2],
        "Need Attention":   COLOR_PALETTE[1],
        "Lost Customers":   COLOR_PALETTE[3],
    }
    fig = px.pie(
        counts,
        names="segment",
        values="nb_clients",
        hole=0.5,
        color="segment",
        color_discrete_map=color_map,
    )
    fig.update_traces(
        textinfo="percent+label",
        hovertemplate="%{label}<br>Clients : %{value:,}<br>%{percent}<extra></extra>",
    )
    return _base_layout(fig, "Segmentation RFM des clients")


def chart_segment_bar(df: pd.DataFrame) -> go.Figure:
    """Bar chart de la répartition des segments clients (RFM).

    Args:
        df: DataFrame avec colonnes customer_id et customer_segment.

    Returns:
        Figure Plotly.
    """
    if df.empty:
        return _empty_fig("Aucune donnée de segmentation disponible")

    counts = df["customer_segment"].value_counts().reset_index()
    counts.columns = ["segment", "nb_clients"]
    total = counts["nb_clients"].sum()
    counts["pct"] = (counts["nb_clients"] / total * 100).round(1)

    color_map = {
        "VIP Customers":    COLOR_PALETTE[2],
        "Need Attention":   COLOR_PALETTE[1],
        "Lost Customers":   COLOR_PALETTE[3],
    }
    fig = px.bar(
        counts,
        x="segment",
        y="nb_clients",
        color="segment",
        text=counts["pct"].map(lambda x: f"{x:.1f} %"),
        color_discrete_map=color_map,
    )
    fig.update_traces(textposition="outside")
    fig.update_xaxes(title_text="Segment")
    fig.update_yaxes(title_text="Nombre de clients")
    fig.update_layout(showlegend=False)
    return _base_layout(fig, "Nombre de clients par segment RFM")


# ---------------------------------------------------------------------------
# CSV exploration helpers
# ---------------------------------------------------------------------------

def chart_histogram(df: pd.DataFrame, col: str) -> go.Figure:
    """Histogramme d'une colonne numérique.

    Args:
        df:  DataFrame source.
        col: Nom de la colonne numérique.

    Returns:
        Figure Plotly.
    """
    fig = px.histogram(
        df,
        x=col,
        nbins=30,
        color_discrete_sequence=[COLOR_PALETTE[0]],
    )
    fig.update_xaxes(title_text=col)
    fig.update_yaxes(title_text="Fréquence")
    return _base_layout(fig, f"Distribution de « {col} »")


def chart_bar_categorical(df: pd.DataFrame, col: str, top_n: int = 20) -> go.Figure:
    """Bar chart des top N modalités d'une colonne catégorielle.

    Args:
        df:    DataFrame source.
        col:   Nom de la colonne catégorielle.
        top_n: Nombre de modalités à afficher.

    Returns:
        Figure Plotly.
    """
    counts = df[col].value_counts().head(top_n).reset_index()
    counts.columns = ["valeur", "nb"]
    fig = px.bar(
        counts,
        x="valeur",
        y="nb",
        color_discrete_sequence=[COLOR_PALETTE[4]],
    )
    fig.update_xaxes(title_text=col, tickangle=-30)
    fig.update_yaxes(title_text="Nombre")
    return _base_layout(fig, f"Top {top_n} modalités de « {col} »")


# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------

def chart_null_rates(df: pd.DataFrame) -> go.Figure:
    """Bar chart des taux de nullité par colonne.

    Args:
        df: DataFrame avec colonnes colonne et taux_null.

    Returns:
        Figure Plotly.
    """
    if df.empty:
        return _empty_fig("Aucune donnée de qualité disponible")

    fig = px.bar(
        df,
        x="colonne",
        y="taux_null",
        color="taux_null",
        color_continuous_scale=["#2ecc71", "#e74c3c"],
        text=df["taux_null"].map(lambda x: f"{x:.1f}%"),
    )
    fig.update_traces(textposition="outside")
    fig.update_xaxes(title_text="Colonne", tickangle=-30)
    fig.update_yaxes(title_text="Taux de nullité (%)", range=[0, 105])
    fig.update_coloraxes(showscale=False)
    return _base_layout(fig, "Taux de nullité par colonne")


def chart_row_counts(df: pd.DataFrame) -> go.Figure:
    """Bar chart du nombre de lignes par table.

    Args:
        df: DataFrame avec colonnes table et nb_lignes.

    Returns:
        Figure Plotly.
    """
    if df.empty:
        return _empty_fig("Aucune donnée de volumétrie disponible")

    fig = px.bar(
        df.sort_values("nb_lignes", ascending=True),
        x="nb_lignes",
        y="table",
        orientation="h",
        color_discrete_sequence=[COLOR_PALETTE[0]],
        text="nb_lignes",
    )
    fig.update_traces(textposition="outside")
    fig.update_xaxes(title_text="Nombre de lignes")
    fig.update_yaxes(title_text="Table")
    return _base_layout(fig, "Volumétrie des tables")


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

def _empty_fig(message: str) -> go.Figure:
    """Retourne une figure vide avec un message centré."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font={"size": 14, "color": "#888"},
    )
    fig.update_layout(template=PLOTLY_TEMPLATE)
    return fig
