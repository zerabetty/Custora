"""
Custora — Müşteri Karar Destek Arayüzü

Çalıştırma:
    streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
FEATURES_PATH = BASE_DIR / "customer_features.csv"
RECS_PATH = BASE_DIR / "customer_recommendations.csv"

SEGMENT_BLURB = {
    "Accessory Shoppers": "Düşük sepet, aksesuar ağırlıklı",
    "Bike Buyers": "Yüksek ticket bisiklet alıcıları",
    "Clothing Shoppers": "Giyim odaklı, orta-düşük değer",
    "High-Value Customers": "Sık alan, yüksek hacimli müşteriler",
}

SAMPLE_CUSTOMERS = [
    {"id": 11003, "name": "Christy Zhu"},
    {"id": 29484, "name": "Gustavo Achong"},
    {"id": 11001, "name": "Eugene Huang"},
    {"id": 29701, "name": "Kirk DeGrasse"},
]

CHART_COLORS = ["#F08A6B", "#2EC4B6", "#F0C05A", "#7B9CFF"]
COLOR_INK = "#F4F1EA"
COLOR_MUTED = "#8E97A6"
COLOR_GOLD = "#F0C05A"
COLOR_IRIS = "#7B9CFF"
COLOR_CORAL = "#F08A6B"
CATEGORY_COLORS = {
    "Bikes": "#2EC4B6",
    "Accessories": "#F08A6B",
    "Clothing": "#F0C05A",
    "Components": "#7B9CFF",
}
COLOR_BG = "#0A0D13"
COLOR_LABEL = "#14161C"
MIN_PIE_LABEL_SHARE = 0.08
SEGMENT_SHORT = {
    "Accessory Shoppers": "Accessory",
    "Bike Buyers": "Bike",
    "Clothing Shoppers": "Clothing",
    "High-Value Customers": "High-Value",
}
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
    "scrollZoom": False,
}


def fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def fmt_pct(value: float) -> str:
    return f"%{value * 100:.1f}".replace(".", ",")


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            "customer_features.csv bulunamadı. Önce `python main.py` ile pipeline'ı çalıştırın."
        )
    features = pd.read_csv(FEATURES_PATH)
    recs = pd.read_csv(RECS_PATH) if RECS_PATH.exists() else pd.DataFrame()
    features["customerid"] = features["customerid"].astype(int)
    if not recs.empty:
        recs["customerid"] = recs["customerid"].astype(int)
    return features, recs


def churn_label(proba: float) -> str:
    if proba >= 0.70:
        return "Yüksek risk"
    if proba >= 0.40:
        return "Orta risk"
    return "Düşük risk"


def suggested_action(row: pd.Series) -> tuple[str, str]:
    high_churn = row["churn_proba"] >= 0.70
    segment = str(row["cltv_segment"])
    cluster = str(row["kmeans_segment"])

    if high_churn and segment == "A":
        return "warning", "Öncelikli elde tutma — yüksek CLTV ve yüksek kayıp riski. Kişisel teklif ve tamamlayıcı ürünle hemen temasa geçin."
    if high_churn and segment in {"B", "C"}:
        return "warning", f"Aktivasyon kampanyası — {cluster} davranışına uygun çapraz satış ve hatırlatma."
    if high_churn:
        return "info", "Düşük maliyetli hatırlatma — değer düşük, risk yüksek. Toplu iletişim yeterli."
    if segment == "A":
        return "success", "VIP sadakat — düşük riskli yüksek değerli müşteri. Premium deneyim ve ayrıcalık önerilir."
    return "info", "İzleme ve bakım — acil müdahale gerekmiyor."


def customer_recommendations(recs: pd.DataFrame, customer_id: int) -> pd.DataFrame:
    if recs.empty:
        return recs
    result = recs.loc[recs["customerid"] == customer_id].copy()
    if result.empty:
        return result
    return (
        result.sort_values(["lift", "confidence"], ascending=False)
        .head(3)
        .reset_index(drop=True)
    )


def inject_css() -> None:
    st.markdown(
        f"<style>{(BASE_DIR / 'assets' / 'style.css').read_text()}</style>",
        unsafe_allow_html=True,
    )


def on_sample_select() -> None:
    selected = st.session_state.get("sample_pills")
    if selected:
        st.session_state.customer_query = str(selected)


def clear_search() -> None:
    st.session_state.customer_query = ""
    st.session_state.sample_pills = None


def pie_percent_labels(values: list[float]) -> list[str]:
    total = float(sum(values)) or 1.0
    labels: list[str] = []
    for value in values:
        share = value / total
        if share < MIN_PIE_LABEL_SHARE:
            labels.append("")
        else:
            labels.append(f"%{share * 100:.1f}".replace(".", ","))
    return labels


def style_plotly(fig: go.Figure, height: int = 280, axes: bool = True) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR_INK, family="Outfit, sans-serif", size=13),
        height=height,
        autosize=True,
        margin=dict(t=64, b=28, l=28, r=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0.5,
            xanchor="center",
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12),
        ),
        uniformtext=dict(minsize=11, mode="hide"),
    )
    if axes:
        fig.update_xaxes(
            gridcolor="rgba(243,238,230,0.08)",
            zeroline=False,
            color=COLOR_MUTED,
            fixedrange=True,
        )
        fig.update_yaxes(
            gridcolor="rgba(243,238,230,0.08)",
            zeroline=False,
            color=COLOR_MUTED,
            fixedrange=True,
        )
    return fig


def show_chart(fig: go.Figure) -> None:
    height = int(fig.layout.height or 280)
    st.plotly_chart(
        fig,
        width="stretch",
        height=height,
        theme=None,
        config=PLOTLY_CONFIG,
    )


def render_portfolio_kpis(features: pd.DataFrame) -> None:
    avg_churn = float(features["churn_proba"].mean())
    avg_cltv = float(features["cltv_6m"].mean())
    median_cltv = float(features["cltv_6m"].median())
    customers, clusters, churn, cltv = st.columns(4, gap="medium")
    customers.metric("Müşteri", f"{len(features):,}", "Tüm portföy", delta_color="off")
    clusters.metric("K-Means kümesi", "4", "Davranışsal segment", delta_color="off")
    churn.metric("Ort. churn", fmt_pct(avg_churn), "6 aylık hedef pencere", delta_color="off")
    cltv.metric(
        "Ort. CLTV (6 ay)",
        fmt_money(avg_cltv),
        f"Medyan {fmt_money(median_cltv)}",
        delta_color="off",
    )


def render_donut(
    title: str,
    labels: list[str],
    values: list[float],
    *,
    hovertemplate: str,
    show_legend: bool,
    colors: list[str] | None = None,
    height: int = 300,
) -> None:
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.58,
            sort=False,
            marker=dict(
                colors=colors or CHART_COLORS[: len(labels)],
                line=dict(color=COLOR_BG, width=3),
            ),
            text=pie_percent_labels(values),
            textinfo="text",
            textposition="inside",
            insidetextorientation="horizontal",
            textfont=dict(size=13, color=COLOR_LABEL, family="Outfit, sans-serif"),
            hovertemplate=hovertemplate,
            showlegend=show_legend,
        )
    )
    fig.update_layout(title=dict(text=title, font=dict(size=16)))
    fig = style_plotly(fig, height=height, axes=False)
    if show_legend:
        fig.update_layout(
            height=height + 16,
            margin=dict(t=56, b=48, l=12, r=12),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.06,
                x=0.5,
                xanchor="center",
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
            ),
        )
    show_chart(fig)


def render_cluster_donut(features: pd.DataFrame) -> None:
    counts = (
        features["kmeans_segment"]
        .value_counts()
        .reindex(list(SEGMENT_BLURB.keys()))
        .fillna(0)
    )
    render_donut(
        "Küme dağılımı",
        list(counts.index),
        [float(v) for v in counts.values],
        hovertemplate="%{label}<br>%{value:,} müşteri (%{percent})<extra></extra>",
        show_legend=False,
        height=300,
    )


def render_segment_performance(features: pd.DataFrame) -> None:
    summary = (
        features.groupby("kmeans_segment", observed=True)
        .agg(churn=("churn_proba", "mean"), cltv=("cltv_6m", "mean"))
        .reindex(list(SEGMENT_BLURB.keys()))
        .reset_index()
    )
    short_labels = summary["kmeans_segment"].map(SEGMENT_SHORT)
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Ort. churn", "Ort. CLTV"),
        horizontal_spacing=0.14,
    )
    fig.add_trace(
        go.Bar(
            x=short_labels,
            y=summary["churn"] * 100,
            marker_color=CHART_COLORS,
            customdata=summary["kmeans_segment"],
            hovertemplate="%{customdata}<br>Churn %{y:.1f}%<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    max_cltv = float(summary["cltv"].max()) or 1.0
    fig.add_trace(
        go.Bar(
            x=short_labels,
            y=summary["cltv"],
            marker_color=CHART_COLORS,
            customdata=summary["kmeans_segment"],
            text=[
                f"${value:,.0f}" if value < max_cltv * 0.12 else ""
                for value in summary["cltv"]
            ],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{customdata}<br>CLTV $%{y:,.0f}<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    fig.update_layout(title=dict(text="Küme bazında churn ve CLTV", font=dict(size=16)))
    fig.update_yaxes(ticksuffix="%", row=1, col=1)
    fig.update_yaxes(tickprefix="$", row=1, col=2)
    fig = style_plotly(fig, height=320)
    fig.update_layout(margin=dict(t=72, b=40, l=40, r=28))
    show_chart(fig)


def render_churn_gauge(proba: float) -> None:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=proba * 100,
            number={"suffix": "%", "font": {"size": 28, "color": COLOR_INK}},
            title={"text": "Churn riski", "font": {"size": 16, "color": COLOR_INK}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": COLOR_MUTED},
                "bar": {"color": COLOR_GOLD, "thickness": 0.28},
                "bgcolor": "rgba(255,255,255,0.04)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40], "color": "rgba(46, 196, 182, 0.22)"},
                    {"range": [40, 70], "color": "rgba(240, 192, 90, 0.22)"},
                    {"range": [70, 100], "color": "rgba(240, 138, 107, 0.28)"},
                ],
                "threshold": {
                    "line": {"color": COLOR_CORAL, "width": 3},
                    "thickness": 0.8,
                    "value": 70,
                },
            },
        )
    )
    show_chart(style_plotly(fig, height=280, axes=False))


def render_category_donut(row: pd.Series) -> None:
    labels = ["Bikes", "Accessories", "Clothing", "Components"]
    values = [
        float(row["ratio_bikes"]),
        float(row["ratio_accessories"]),
        float(row["ratio_clothing"]),
        float(row["ratio_components"]),
    ]
    slices = [(label, value) for label, value in zip(labels, values) if value > 0]
    if not slices:
        slices = [("Bikes", 1.0)]
    total = sum(value for _, value in slices) or 1.0
    kept: list[tuple[str, float]] = []
    other = 0.0
    for label, value in slices:
        if value / total >= MIN_PIE_LABEL_SHARE:
            kept.append((label, value))
        else:
            other += value
    if other > 0:
        kept.append(("Diğer", other))
    slice_labels, slice_values = zip(*kept)
    colors = [
        CATEGORY_COLORS.get(label, COLOR_MUTED) for label in slice_labels
    ]
    render_donut(
        "Kategori tercihi",
        list(slice_labels),
        list(slice_values),
        hovertemplate="%{label}: %{percent}<extra></extra>",
        show_legend=True,
        colors=colors,
        height=300,
    )


def render_customer_vs_portfolio(
    proba: float, cltv: float, avg_churn: float, avg_cltv: float
) -> None:
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Churn", "CLTV"),
        horizontal_spacing=0.16,
    )
    fig.add_trace(
        go.Bar(
            name="Müşteri",
            x=["Churn"],
            y=[proba * 100],
            marker_color=COLOR_GOLD,
            hovertemplate="Müşteri<br>Churn %{y:.1f}%<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            name="Portföy",
            x=["Churn"],
            y=[avg_churn * 100],
            marker_color=COLOR_IRIS,
            hovertemplate="Portföy<br>Churn %{y:.1f}%<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            name="Müşteri",
            x=["CLTV"],
            y=[cltv],
            marker_color=COLOR_GOLD,
            hovertemplate="Müşteri<br>CLTV $%{y:,.0f}<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Bar(
            name="Portföy",
            x=["CLTV"],
            y=[avg_cltv],
            marker_color=COLOR_IRIS,
            hovertemplate="Portföy<br>CLTV $%{y:,.0f}<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    fig.update_layout(
        title=dict(text="Müşteri vs portföy", font=dict(size=16)),
        bargap=0.38,
        barmode="group",
    )
    fig.update_yaxes(ticksuffix="%", row=1, col=1)
    fig.update_yaxes(tickprefix="$", row=1, col=2)
    fig.update_xaxes(showticklabels=False)
    fig = style_plotly(fig, height=300)
    fig.update_layout(margin=dict(t=72, b=28, l=36, r=28))
    show_chart(fig)


def render_welcome(features: pd.DataFrame) -> None:
    st.subheader("Portföy kümeleri")
    counts = features["kmeans_segment"].value_counts()
    table = pd.DataFrame(
        {
            "Küme": list(SEGMENT_BLURB.keys()),
            "Müşteri": [int(counts.get(name, 0)) for name in SEGMENT_BLURB],
            "Pay": [
                counts.get(name, 0) / len(features)
                for name in SEGMENT_BLURB
            ],
            "Profil": list(SEGMENT_BLURB.values()),
        }
    )
    chart_col, table_col = st.columns([1.15, 1], gap="large")
    with chart_col:
        render_cluster_donut(features)
    with table_col:
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            column_config={
                "Pay": st.column_config.ProgressColumn(
                    format="percent", min_value=0, max_value=1
                ),
                "Müşteri": st.column_config.NumberColumn(format="localized"),
            },
        )
    render_segment_performance(features)


def render_products(customer_recs: pd.DataFrame) -> None:
    st.subheader("Önerilen ürünler")
    if customer_recs.empty:
        st.info(
            "Bu müşteri için eşleşen ürün önerisi yok. "
            "Öneriler; olgunlaşmış, CLTV A ve churn riski yüksek müşterilerde üretilir."
        )
        return

    display = customer_recs.rename(
        columns={
            "recommended_product": "Önerilen ürün",
            "based_on_product": "Kaynak ürün",
            "support": "Support",
            "confidence": "Confidence",
            "lift": "Lift",
        }
    )[["Önerilen ürün", "Kaynak ürün", "Support", "Confidence", "Lift"]]
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_config={
            "Support": st.column_config.NumberColumn(format="percent"),
            "Confidence": st.column_config.ProgressColumn(
                min_value=0, max_value=1, format="percent"
            ),
            "Lift": st.column_config.NumberColumn(format="localized"),
        },
    )


def render_customer(row: pd.Series, recs: pd.DataFrame, features: pd.DataFrame) -> None:
    segment = str(row["kmeans_segment"])
    proba = float(row["churn_proba"])
    cltv_6m = float(row["cltv_6m"])
    avg_churn = float(features["churn_proba"].mean())
    avg_cltv = float(features["cltv_6m"].mean())
    matured = int(row["is_matured"]) == 1

    identity, numbers = st.columns([0.95, 1.35], gap="large")
    with identity:
        st.subheader(row["customer_name"])
        st.caption(row["emailaddress"])
        profile = pd.DataFrame(
            {
                "Alan": [
                    "K-Means",
                    "Churn",
                    "CLTV",
                    "RFM",
                    "Profil",
                    "ID",
                    "Bölge",
                    "Recency",
                ],
                "Değer": [
                    segment,
                    churn_label(proba),
                    str(row["cltv_segment"]),
                    str(row["rfm_segment"]).replace("_", " ").title(),
                    "Olgun müşteri" if matured else "Taze müşteri",
                    str(int(row["customerid"])),
                    str(row["territory_name"]),
                    f"{int(row['recency_days'])} gün",
                ],
            }
        )
        st.dataframe(profile, hide_index=True, width="stretch")
        st.caption(SEGMENT_BLURB.get(segment, ""))

    with numbers:
        top_left, top_right = st.columns(2)
        top_left.metric("K-Means kümesi", segment, f"Cluster {int(row['cluster'])}", delta_color="off")
        top_right.metric(
            "Churn risk puanı",
            fmt_pct(proba),
            f"{(proba - avg_churn) * 100:+.1f} pp vs portföy",
            delta_color="inverse",
        )
        bottom_left, bottom_right = st.columns(2)
        bottom_left.metric(
            "Beklenen CLTV (6 ay)",
            fmt_money(cltv_6m),
            f"{cltv_6m - avg_cltv:+,.0f} vs portföy",
        )
        bottom_right.metric(
            "CLTV segmenti",
            str(row["cltv_segment"]),
            f"{int(row['total_orders'])} sipariş · {fmt_money(float(row['total_monetary']))}",
            delta_color="off",
        )
        st.progress(min(max(proba, 0.0), 1.0), text=f"Churn olasılığı {fmt_pct(proba)}")
        st.subheader("Önerilen aksiyon")
        level, message = suggested_action(row)
        getattr(st, level)(message)

    gauge, mix, versus = st.columns(3, gap="medium")
    with gauge:
        render_churn_gauge(proba)
    with mix:
        render_category_donut(row)
    with versus:
        render_customer_vs_portfolio(proba, cltv_6m, avg_churn, avg_cltv)

    render_products(customer_recommendations(recs, int(row["customerid"])))


def main() -> None:
    st.set_page_config(
        page_title="Custora",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    try:
        features, recs = load_data()
    except FileNotFoundError as exc:
        st.error(str(exc))
        return

    st.title("Custora")

    render_portfolio_kpis(features)

    search_col, query_col, clear_col = st.columns([5.2, 1, 1], vertical_alignment="bottom")
    with search_col:
        st.text_input("Müşteri ID", placeholder="11003", key="customer_query")
    with query_col:
        st.button("Sorgula", type="primary", width="stretch")
    with clear_col:
        st.button("Temizle", width="stretch", on_click=clear_search)

    st.pills(
        "Örnekler",
        options=[sample["id"] for sample in SAMPLE_CUSTOMERS],
        format_func=lambda cid: next(
            f"{sample['id']} · {sample['name']}"
            for sample in SAMPLE_CUSTOMERS
            if sample["id"] == cid
        ),
        key="sample_pills",
        on_change=on_sample_select,
        width="stretch",
        label_visibility="collapsed",
    )

    query = (st.session_state.get("customer_query") or "").strip()
    if not query:
        render_welcome(features)
        return

    if not query.isdigit():
        st.error("Müşteri ID yalnızca sayı olmalıdır.")
        return

    customer_id = int(query)
    match = features.loc[features["customerid"] == customer_id]
    if match.empty:
        st.error(f"{customer_id} numaralı müşteri portföyde bulunamadı.")
        return

    render_customer(match.iloc[0], recs, features)


if __name__ == "__main__":
    main()
