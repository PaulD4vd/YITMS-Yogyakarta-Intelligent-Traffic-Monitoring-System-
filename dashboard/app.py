import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import pytz

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Traffic Intelligence · Yogyakarta",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── HELPER: hex → rgba ──────────────────────────────────────────────────────
def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

# ─── GLOBAL CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background: #080b13;
    color: #dde3f0;
}

section[data-testid="stSidebar"] {
    background: #0b0f1c !important;
    border-right: 1px solid #151e30;
}
section[data-testid="stSidebar"] * { color: #b8c2d8 !important; }
section[data-testid="stSidebar"] label {
    font-size: .75rem !important;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: #3d4d6a !important;
}

.main .block-container {
    background: #080b13;
    padding-top: 1.8rem;
    max-width: 1380px;
}

.kpi-card {
    background: #0d1120;
    border: 1px solid #181f32;
    border-top: 2px solid var(--accent);
    border-radius: 10px;
    padding: 1.2rem 1.4rem 1rem;
    height: 100%;
}
.kpi-eyebrow {
    font-size: .65rem;
    font-weight: 600;
    letter-spacing: .16em;
    text-transform: uppercase;
    color: #3d4d6a;
    margin-bottom: .55rem;
}
.kpi-number {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.3rem;
    font-weight: 500;
    color: #eef1f8;
    line-height: 1;
    margin-bottom: .35rem;
}
.kpi-desc {
    font-size: .74rem;
    color: #3d4d6a;
    margin-bottom: .55rem;
}
.kpi-tag {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: .62rem;
    padding: .2rem .55rem;
    border-radius: 4px;
    background: var(--tag-bg);
    color: var(--accent);
    letter-spacing: .04em;
}

.sec-title {
    font-size: .68rem;
    font-weight: 600;
    letter-spacing: .2em;
    text-transform: uppercase;
    color: #3d4d6a;
    margin: 2rem 0 .9rem;
    padding-bottom: .5rem;
    border-bottom: 1px solid #131a28;
}

.sub-title {
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: #3d4d6a;
    margin-bottom: .7rem;
}

.pg-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #eef1f8;
    letter-spacing: -.025em;
    line-height: 1.2;
    margin: 0;
}
.pg-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: .7rem;
    color: #3d4d6a;
    margin-top: .45rem;
    letter-spacing: .02em;
}

.sb-brand {
    font-size: 1.05rem;
    font-weight: 700;
    color: #eef1f8 !important;
    letter-spacing: -.01em;
    margin-bottom: .05rem;
}
.sb-sub {
    font-size: .7rem;
    color: #2e3d58 !important;
    margin-bottom: 1rem;
}

hr { border-color: #131a28 !important; }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
CAM_MAP = {"cam1": "Demangan", "cam3": "Yos Sudarso", "cam4": "Titik Nol"}

OBJ_LABELS = {
    "motor":    "Motor",
    "mobil":    "Mobil",
    "bus_truk": "Bus / Truk",
    "sepeda":   "Sepeda",
}

LOC_COLORS = {
    "Demangan":    "#3b82f6",
    "Yos Sudarso": "#22c55e",
    "Titik Nol":   "#f97316",
}

OBJ_COLORS = {
    "Motor":      "#f59e0b",
    "Mobil":      "#3b82f6",
    "Bus / Truk": "#ef4444",
    "Sepeda":     "#22c55e",
}

BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Space Grotesk, sans-serif", color="#6b7a99", size=11),
    margin=dict(l=4, r=4, t=28, b=4),
    legend=dict(
        bgcolor="rgba(11,15,28,.9)",
        bordercolor="#1a2236",
        borderwidth=1,
        font=dict(size=11, color="#b8c2d8"),
    ),
    hoverlabel=dict(
        bgcolor="#0f1525",
        bordercolor="#1e2a40",
        font=dict(family="Space Grotesk", size=12, color="#dde3f0"),
    ),
)

AXIS_BASE = dict(
    gridcolor="#101828",
    gridwidth=1,
    zeroline=False,
    showline=False,
    tickfont=dict(family="JetBrains Mono", size=10, color="#4a5870"),
    title_font=dict(family="Space Grotesk", size=11, color="#4a5870"),
)

# ─── DATA ────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data():
    import pathlib
    base = pathlib.Path(__file__).parent.parent  # root of repo
    # Try full dataset first, fall back to sample data for demo/CI
    for candidate in ["data_cctv_clean_v1.csv", "data/data_bersih.csv", "data/sample_data.csv"]:
        path = base / candidate
        if path.exists():
            df = pd.read_csv(path)
            break
    else:
        st.error("❌ File data tidak ditemukan. Letakkan `data_cctv_clean_v1.csv` di folder `data/`.")
        st.stop()
    jkt = pytz.timezone("Asia/Jakarta")
    df["dt"] = (
        pd.to_datetime(df["detection_timestamp"], errors="coerce")
        .dt.tz_localize("UTC")
        .dt.tz_convert(jkt)
    )
    df = df[df["camera_id"].isin(CAM_MAP)].copy()
    df["location_name"] = df["camera_id"].map(CAM_MAP)
    df["object_label"]  = df["object"].map(OBJ_LABELS).fillna(df["object"])
    df["hour"] = df["dt"].dt.hour
    df["date"] = df["dt"].dt.date
    return df

with st.spinner("Memuat data CCTV…"):
    df_raw = load_data()

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="sb-brand">🚦 Traffic Intel</p>', unsafe_allow_html=True)
    st.markdown('<p class="sb-sub">Monitoring Lalu Lintas · Yogyakarta</p>', unsafe_allow_html=True)
    st.markdown("---")

    available_dates = sorted(df_raw["date"].unique())
    selected_date = st.date_input(
        "Tanggal",
        value=available_dates[0],
        min_value=available_dates[0],
        max_value=available_dates[-1],
    )
    st.markdown(" ")

    hour_range = st.slider("Jam Operasional (WIB)", 0, 23, (0, 23), format="%d:00")
    st.markdown(" ")

    all_locs = list(CAM_MAP.values())
    selected_locs = st.multiselect("Lokasi", all_locs, default=all_locs)
    st.markdown(" ")

    all_objs = list(OBJ_LABELS.values())
    selected_objs = st.multiselect("Jenis Kendaraan", all_objs, default=all_objs)

    st.markdown("---")
    st.markdown(
        f'<p style="font-size:.67rem;color:#1e2a3a;font-family:JetBrains Mono,monospace">'
        f'{len(available_dates)} hari &nbsp;·&nbsp; {len(df_raw):,} records<br>GMT+7 (WIB)</p>',
        unsafe_allow_html=True,
    )

if not selected_locs:
    st.warning("Pilih minimal satu lokasi di sidebar.")
    st.stop()

# ─── FILTER ──────────────────────────────────────────────────────────────────
df = df_raw[
    (df_raw["date"] == selected_date) &
    (df_raw["hour"] >= hour_range[0]) &
    (df_raw["hour"] <= hour_range[1]) &
    (df_raw["location_name"].isin(selected_locs)) &
    (df_raw["object_label"].isin(selected_objs))
].copy()

# ─── HEADER ──────────────────────────────────────────────────────────────────
st.markdown(
    f'<h1 class="pg-title">Traffic Intelligence Dashboard</h1>'
    f'<p class="pg-meta">'
    f'{selected_date.strftime("%A, %d %B %Y").upper()}'
    f'&nbsp;&nbsp;/&nbsp;&nbsp;{hour_range[0]:02d}:00 – {hour_range[1]:02d}:59 WIB'
    f'&nbsp;&nbsp;/&nbsp;&nbsp;{" · ".join(selected_locs)}'
    f'</p>',
    unsafe_allow_html=True,
)
st.markdown("---")

# ─── KPI ─────────────────────────────────────────────────────────────────────
total_vol = df["track_id"].nunique() if not df.empty else 0

if not df.empty:
    vol_per_loc    = df.groupby("location_name")["track_id"].nunique()
    busiest_loc    = vol_per_loc.idxmax()
    busiest_vol    = int(vol_per_loc.max())
    obj_counts     = df.groupby("object_label")["track_id"].nunique()
    top_obj        = obj_counts.idxmax()
    top_pct        = int(obj_counts.max() / obj_counts.sum() * 100) if obj_counts.sum() else 0
    peak_hr_series = df.groupby("hour")["track_id"].nunique()
    peak_hour      = int(peak_hr_series.idxmax())
    peak_hr_vol    = int(peak_hr_series.max())
else:
    busiest_loc = "–"; busiest_vol = 0
    top_obj = "–";     top_pct = 0
    peak_hour = 0;     peak_hr_vol = 0


def kpi(eyebrow, number, desc, accent, tag):
    tag_bg = hex_to_rgba(accent, 0.12)
    return (
        f'<div class="kpi-card" style="--accent:{accent}">'
        f'<div class="kpi-eyebrow">{eyebrow}</div>'
        f'<div class="kpi-number">{number}</div>'
        f'<div class="kpi-desc">{desc}</div>'
        f'<div class="kpi-tag" style="--tag-bg:{tag_bg}">{tag}</div>'
        f'</div>'
    )


k1, k2, k3, k4 = st.columns(4, gap="small")
with k1:
    st.markdown(kpi("Total Volume", f"{total_vol:,}",
        f"{len(selected_locs)} lokasi aktif", "#3b82f6",
        f"↑ {len(selected_locs)} LOKASI"), unsafe_allow_html=True)
with k2:
    lc = LOC_COLORS.get(busiest_loc, "#f97316")
    st.markdown(kpi("Lokasi Terpadat", busiest_loc,
        f"{busiest_vol:,} kendaraan unik", lc,
        "HIGHEST VOLUME"), unsafe_allow_html=True)
with k3:
    oc = OBJ_COLORS.get(top_obj, "#f59e0b")
    st.markdown(kpi("Kendaraan Dominan", top_obj,
        "dari total trafik terpilih", oc,
        f"{top_pct}% SHARE"), unsafe_allow_html=True)
with k4:
    st.markdown(kpi("Jam Puncak", f"{peak_hour:02d}:00",
        f"{peak_hr_vol:,} kendaraan pada jam ini", "#22c55e",
        "PEAK HOUR"), unsafe_allow_html=True)

# ─── LINE CHART ──────────────────────────────────────────────────────────────
st.markdown('<p class="sec-title">Tren Volume per Jam</p>', unsafe_allow_html=True)

if df.empty:
    st.info("Tidak ada data untuk rentang yang dipilih.")
else:
    all_hours = list(range(hour_range[0], hour_range[1] + 1))
    hourly = df.groupby(["hour", "location_name"])["track_id"].nunique().reset_index(name="volume")
    idx = pd.MultiIndex.from_product([all_hours, selected_locs], names=["hour", "location_name"])
    hourly = (
        hourly.set_index(["hour", "location_name"])
        .reindex(idx, fill_value=0)
        .reset_index()
    )

    fig_line = go.Figure()
    for loc in selected_locs:
        sub = hourly[hourly["location_name"] == loc].sort_values("hour")
        clr = LOC_COLORS.get(loc, "#aaa")
        fig_line.add_trace(go.Scatter(
            x=sub["hour"], y=sub["volume"],
            mode="lines+markers",
            name=loc,
            line=dict(color=clr, width=2.5, shape="spline"),
            marker=dict(size=5, color=clr, line=dict(color="#080b13", width=1.5)),
            fill="tozeroy",
            fillcolor=hex_to_rgba(clr, 0.07),  # ← FIXED
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "Jam %{x:02d}:00  →  <b>%{y:,}</b> kendaraan<extra></extra>"
            ),
        ))

    fig_line.update_layout(BASE_LAYOUT)

    fig_line.update_layout(
        height=320,
        xaxis=dict(**AXIS_BASE, title="Jam (WIB)", tickmode="linear", dtick=1),
        yaxis=dict(**AXIS_BASE, title="Kendaraan Unik"),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.25, x=0),
    )
    st.plotly_chart(fig_line, width="stretch", config={"displayModeBar": False})

# ─── BAR + DONUT ─────────────────────────────────────────────────────────────
st.markdown('<p class="sec-title">Komparasi &amp; Komposisi</p>', unsafe_allow_html=True)
col_bar, col_donut = st.columns(2, gap="large")

with col_bar:
    st.markdown('<p class="sub-title">Volume Antar Lokasi</p>', unsafe_allow_html=True)
    if not df.empty:
        bd = (
            df.groupby("location_name")["track_id"]
            .nunique()
            .reindex(selected_locs, fill_value=0)
            .reset_index()
        )
        bd.columns = ["location_name", "volume"]
        bd = bd.sort_values("volume", ascending=True)
        fig_bar = go.Figure(go.Bar(
            y=bd["location_name"], x=bd["volume"],
            orientation="h",
            marker=dict(
                color=[LOC_COLORS.get(l, "#888") for l in bd["location_name"]],
                opacity=0.5,
                line=dict(color="rgba(0,0,0,0)"),
            ),
            text=bd["volume"].apply(lambda v: f"{v:,}"),
            textposition="outside",
            textfont=dict(family="JetBrains Mono", size=11, color="#6b7a99"),
            hovertemplate="<b>%{y}</b><br>%{x:,} kendaraan<extra></extra>",
        ))
        fig_bar.update_layout(
            **BASE_LAYOUT, height=260,
            xaxis=dict(**AXIS_BASE),
            yaxis=dict(AXIS_BASE, tickfont=dict(family="Space Grotesk", size=13, color="#b8c2d8")),
            bargap=0.38,
        )
        st.plotly_chart(fig_bar, width="stretch", config={"displayModeBar": False})

with col_donut:
    st.markdown('<p class="sub-title">Komposisi Jenis Kendaraan</p>', unsafe_allow_html=True)
    if not df.empty:
        dd = (
            df.groupby("object_label")["track_id"]
            .nunique()
            .reindex(selected_objs, fill_value=0)
            .reset_index()
        )
        dd.columns = ["object_label", "volume"]
        dd = dd[dd["volume"] > 0]
        total_d = int(dd["volume"].sum())
        fig_donut = go.Figure(go.Pie(
            labels=dd["object_label"], values=dd["volume"],
            hole=0.60,
            marker=dict(
                colors=[OBJ_COLORS.get(o, "#888") for o in dd["object_label"]],
                line=dict(color="#080b13", width=3),
            ),
            textinfo="label+percent",
            textfont=dict(family="Space Grotesk", size=11, color="#b8c2d8"),
            insidetextorientation="radial",
            hovertemplate="<b>%{label}</b><br>%{value:,} kendaraan · %{percent}<extra></extra>",
        ))
        fig_donut.add_annotation(
            text=f"<b>{total_d:,}</b><br><span style='font-size:10px;color:#3d4d6a'>total</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(family="JetBrains Mono", size=17, color="#dde3f0"),
        )
        fig_donut.update_layout(**BASE_LAYOUT, height=260, showlegend=False)
        st.plotly_chart(fig_donut, width="stretch", config={"displayModeBar": False})

# ─── HEATMAP ─────────────────────────────────────────────────────────────────
st.markdown('<p class="sec-title">Heatmap Intensitas Trafik</p>', unsafe_allow_html=True)

if not df.empty:
    heat = (
        df.groupby(["location_name", "hour"])["track_id"]
        .nunique()
        .reset_index(name="volume")
    )
    locs_in_heat = [l for l in selected_locs if l in heat["location_name"].values]
    heat_piv = (
        heat.pivot(index="location_name", columns="hour", values="volume")
        .reindex(columns=list(range(hour_range[0], hour_range[1] + 1)), fill_value=0)
        .reindex(locs_in_heat)
        .fillna(0)
    )
    fig_heat = go.Figure(go.Heatmap(
        z=heat_piv.values,
        x=[f"{h:02d}:00" for h in heat_piv.columns],
        y=heat_piv.index.tolist(),
        colorscale=[
            [0.00, "#080b13"], [0.30, "#0a1e36"],
            [0.60, "#1a4a7a"], [0.85, "#2b6cb8"],
            [1.00, "#3b82f6"],
        ],
        hovertemplate="<b>%{y}</b> · %{x}<br>%{z:,} kendaraan<extra></extra>",
        showscale=True,
        colorbar=dict(
            thickness=10,
            title=dict(text="Kendaraan", font=dict(size=9, color="#4a5870"), side="right"),
            tickfont=dict(family="JetBrains Mono", size=9, color="#4a5870"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
        ),
    ))
    fig_heat.update_layout(BASE_LAYOUT)

    fig_heat.update_layout(
        height=190,
        margin=dict(l=4, r=4, t=12, b=4), # margin baru khusus heatmap
        xaxis=dict(AXIS_BASE),
        yaxis=dict(AXIS_BASE, tickfont=dict(family="Space Grotesk", size=13, color="#b8c2d8")),
    )
    st.plotly_chart(fig_heat, width="stretch", config={"displayModeBar": False})

# ─── STACKED BAR ─────────────────────────────────────────────────────────────
st.markdown('<p class="sec-title">Komposisi Kendaraan per Lokasi</p>', unsafe_allow_html=True)

if not df.empty:
    stack = (
        df.groupby(["location_name", "object_label"])["track_id"]
        .nunique()
        .reset_index(name="volume")
    )
    fig_stack = go.Figure()
    for obj in selected_objs:
        sub = (
            stack[stack["object_label"] == obj]
            .set_index("location_name")["volume"]
            .reindex(selected_locs, fill_value=0)
            .reset_index()
        )
        sub.columns = ["location_name", "volume"]
        fig_stack.add_trace(go.Bar(
            name=obj,
            x=sub["location_name"], y=sub["volume"],
            marker=dict(color=OBJ_COLORS.get(obj, "#888"), opacity=0.85),
            hovertemplate=f"<b>%{{x}}</b><br>{obj}: <b>%{{y:,}}</b><extra></extra>",
        ))
    fig_stack.update_layout(BASE_LAYOUT)

    fig_stack.update_layout(
        barmode="stack", 
        height=280,
        xaxis=dict(AXIS_BASE, tickfont=dict(family="Space Grotesk", size=13, color="#b8c2d8")),
        yaxis=dict(AXIS_BASE, title="Kendaraan Unik"),
        legend=dict(orientation="h", y=-0.3, x=0),
        bargap=0.38,
    )

    st.plotly_chart(fig_stack, width="stretch", config={"displayModeBar": False})


# ─── FOOTER ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="text-align:center;font-family:JetBrains Mono,monospace;'
    'font-size:.62rem;color:#1a2232;letter-spacing:.1em">'
    'TRAFFIC INTELLIGENCE · CCTV KOTA YOGYAKARTA · GMT+7 (WIB)'
    '</p>',
    unsafe_allow_html=True,
)
