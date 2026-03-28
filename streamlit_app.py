"""
Wriggle Survey — Streamlit Web Application
Best-Fit Circle 3D (Kasa Method) | Tunnel Survey Analysis
"""

import sys
import os
import io
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ── Backend path ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from wriggle_core import compute_wriggle_survey
from landxml_parser import parse_landxml_to_dta, list_alignments

# ═══════════════════════════════════════════════════════════════════════════════
# Page config
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Wriggle Survey",
    page_icon="⭕",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { min-width: 280px; }
div[data-testid="metric-container"] { background:#1e293b; border-radius:10px; padding:12px; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Sidebar — Configuration
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⭕ Wriggle Survey")
    st.caption("Best-Fit Circle 3D — Kasa Method")
    st.divider()

    st.markdown("### ⚙️ Hesaplama Ayarları")
    dia_design = st.number_input(
        "Tasarım Çapı (m)", value=3.396, min_value=0.1,
        step=0.001, format="%.3f",
        help="Tünel tasarım çapı (metre)"
    )
    direction = st.selectbox(
        "Kazı Yönü",
        ["DIRECT", "REVERSE"],
        help="DIRECT: ileri yön, REVERSE: geri yön (sapma işareti)"
    )

    st.divider()
    st.markdown("### 🗺️ LandXML Ayarları")
    sample_interval = st.number_input(
        "Örnekleme Aralığı (m)", value=1.0, min_value=0.1,
        step=0.5, format="%.1f",
        help="LandXML güzergahından nokta örnekleme adımı"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("# ⭕ Wriggle Survey")
st.caption("Tünel kesit analizi — Best-Fit Circle 3D (Kasa Method)")
st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# Input section
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("### 📂 Veri Girişi")

input_mode = st.radio(
    "Giriş Formatı",
    ["Tek Excel (birleşik)", "Ayrı Dosyalar"],
    horizontal=True,
    help=(
        "**Tek Excel**: 'Import Wriggle Data' ve 'Import Tunnel Axis (DTA)' "
        "sayfalarını içeren tek bir dosya.\n\n"
        "**Ayrı Dosyalar**: Ölçüm verisi Excel + Güzergah Excel veya LandXML."
    ),
)

wrs_bytes = None
dta_bytes = None
dta_is_xml = False

if input_mode == "Tek Excel (birleşik)":
    combined = st.file_uploader(
        "Birleşik Excel dosyası yükle (.xlsx)",
        type=["xlsx", "xls"],
        help="Dosya 2 sayfa içermeli: 'Import Wriggle Data' ve 'Import Tunnel Axis (DTA)'",
    )
    if combined:
        wrs_bytes = combined.getvalue()
        dta_bytes = combined.getvalue()

else:
    col_wrs, col_dta = st.columns(2)

    with col_wrs:
        st.markdown("**Wriggle Ölçüm Verisi**")
        wrs_file = st.file_uploader(
            "Wriggle Excel yükle (.xlsx)",
            type=["xlsx", "xls"],
            key="wrs",
        )
        if wrs_file:
            wrs_bytes = wrs_file.getvalue()

    with col_dta:
        st.markdown("**Tünel Güzergahı (DTA)**")
        dta_fmt = st.radio(
            "Format", ["Excel (.xlsx)", "LandXML (.xml)"],
            horizontal=True, key="dta_fmt",
        )
        dta_is_xml = dta_fmt == "LandXML (.xml)"

        if dta_is_xml:
            dta_file = st.file_uploader(
                "LandXML dosyası yükle",
                type=["xml", "landxml"],
                key="dta_xml",
                help="AutoCAD Civil 3D, Trimble, Leica vb. yazılımların çıktısı",
            )
        else:
            dta_file = st.file_uploader(
                "DTA Excel yükle (.xlsx)",
                type=["xlsx", "xls"],
                key="dta_xl",
            )
        if dta_file:
            dta_bytes = dta_file.getvalue()

# ── LandXML alignment preview ─────────────────────────────────────────────────
if dta_is_xml and dta_bytes:
    alignment_names = list_alignments(dta_bytes)
    if alignment_names:
        st.info(
            f"**{len(alignment_names)} güzergah bulundu** — "
            f"ilk güzergah kullanılacak: `{alignment_names[0]}`"
            + (f" (diğerleri: {', '.join(alignment_names[1:])})" if len(alignment_names) > 1 else "")
        )

st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# Helper functions (must be defined before button handler)
# ═══════════════════════════════════════════════════════════════════════════════
def _safe(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _build_chart_data(df_backup: pd.DataFrame) -> list[dict]:
    rows = []
    for _, row in df_backup.iterrows():
        num_pnt = int(row.get("NUM.PNT", 0) or 0)
        xc = _safe(row.get("X_C"))
        yc_raw = _safe(row.get("Y_C"))
        yc = (yc_raw - 100) if yc_raw is not None else None

        points = []
        for t in range(1, num_pnt + 1):
            xv = _safe(row.get(f"X_P{t}"))
            yv_raw = _safe(row.get(f"Y_P{t}"))
            yv = (yv_raw - 100) if yv_raw is not None else None
            rdbc = _safe(row.get(f"RDBC_P{t}"))
            r    = _safe(row.get(f"R_P{t}"))
            if xv is not None and yv is not None and xc is not None and yc is not None:
                points.append({
                    "label": f"P{t}",
                    "x": round(xv - xc, 6),
                    "y": round(yv - yc, 6),
                    "rdbc": rdbc,
                    "r": r,
                })

        rows.append({
            "ring_no":       str(row.get("RING NO.", "")),
            "chainage":      _safe(row.get("CH")),
            "avg_radius":    _safe(row.get("AVG.R")),
            "design_radius": _safe(row.get("DESING.CL-R")),
            "hor_dev":       _safe(row.get("DH")),
            "ver_dev":       _safe(row.get("DV")),
            "points":        points,
        })
    return rows


# ── Compute button ────────────────────────────────────────────────────────────
can_compute = wrs_bytes is not None and dta_bytes is not None
compute_btn = st.button("▶ Hesapla", type="primary", disabled=not can_compute, use_container_width=False)

if compute_btn:
    with st.spinner("Hesaplanıyor..."):
        try:
            # Read Wriggle data
            df_wrs = pd.read_excel(io.BytesIO(wrs_bytes), sheet_name="Import Wriggle Data")

            # Read DTA data
            if dta_is_xml:
                df_dta = parse_landxml_to_dta(dta_bytes, sample_interval)
                st.success(f"LandXML → {len(df_dta)} güzergah noktası okundu.")
            else:
                df_dta = pd.read_excel(io.BytesIO(dta_bytes), sheet_name="Import Tunnel Axis (DTA)")

            # Compute
            df_result, df_backup = compute_wriggle_survey(df_wrs, df_dta, dia_design, direction)

            # Build chart data
            chart_data = _build_chart_data(df_backup)

            # Generate download Excel
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                df_result.to_excel(writer, sheet_name="WRIGGLE RESULT",  index=False)
                df_backup.to_excel(writer, sheet_name="WRIGGLE BACKUP",  index=False)

            # Persist in session state
            st.session_state.update({
                "df_result":   df_result,
                "df_backup":   df_backup,
                "chart_data":  chart_data,
                "dia_design":  dia_design,
                "excel_bytes": excel_buf.getvalue(),
            })

        except Exception as exc:
            st.error(f"**Hata:** {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# Results section
# ═══════════════════════════════════════════════════════════════════════════════
if "df_result" not in st.session_state:
    st.stop()

df_result  = st.session_state["df_result"]
df_backup  = st.session_state["df_backup"]
chart_data = st.session_state["chart_data"]
design_dia = st.session_state["dia_design"]

# ── Summary metrics ───────────────────────────────────────────────────────────
n_rings = len(df_result)
dh_vals = df_result["HOR.DEVIATION (M.)"].dropna().values
dv_vals = df_result["VER.DEVIATION (M.)"].dropna().values
dia_vals = df_result["AVG.DIAMETER (M.)"].dropna().values

st.markdown("### 📊 Sonuçlar")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Ring Sayısı",           f"{n_rings}")
m2.metric("Maks. Yatay Sapma",     f"{np.max(np.abs(dh_vals)):.4f} m" if len(dh_vals) else "—")
m3.metric("Maks. Dikey Sapma",     f"{np.max(np.abs(dv_vals)):.4f} m" if len(dv_vals) else "—")
m4.metric("Ort. Çap",              f"{np.mean(dia_vals):.4f} m"       if len(dia_vals) else "—")
m5.metric("Çap Farkı (ort−tasarım)",
          f"{np.mean(dia_vals) - design_dia:+.4f} m"                  if len(dia_vals) else "—")

# ── Download ──────────────────────────────────────────────────────────────────
st.download_button(
    label="⬇ Excel Olarak İndir",
    data=st.session_state["excel_bytes"],
    file_name="Export_Wriggle_Survey.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_table, tab_dev, tab_dia, tab_cross = st.tabs([
    "📋 Sonuç Tablosu",
    "📉 Sapmalar",
    "⭕ Çap Analizi",
    "🔵 Kesit Görünümü",
])

PLOTLY_THEME = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0f172a",
    font=dict(color="#94a3b8", size=12),
    margin=dict(l=50, r=30, t=40, b=50),
)


# ── Tab 1: Sonuç Tablosu ──────────────────────────────────────────────────────
with tab_table:
    # Colour deviations
    def colour_dev(val):
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return ""
        return "color: #4ade80" if float(val) >= 0 else "color: #f87171"

    styled = (
        df_result.style
        .applymap(colour_dev, subset=["HOR.DEVIATION (M.)", "VER.DEVIATION (M.)"])
        .format({
            "TUN.CL-EASTING (M.)":  "{:.3f}",
            "TUN.CL-NORTHING (M.)": "{:.3f}",
            "TUN.CL-ELEVATION (M.)":"{:.3f}",
            "CHAINAGE (M.)":        "{:.3f}",
            "HOR.DEVIATION (M.)":   "{:.4f}",
            "VER.DEVIATION (M.)":   "{:.4f}",
            "AVG.RADIUS (M.)":      "{:.4f}",
            "AVG.DIAMETER (M.)":    "{:.4f}",
        }, na_rep="—")
    )
    st.dataframe(styled, use_container_width=True, height=450)


# ── Tab 2: Sapmalar ───────────────────────────────────────────────────────────
with tab_dev:
    rings   = [d["ring_no"]  for d in chart_data]
    hor_dev = [d["hor_dev"]  for d in chart_data]
    ver_dev = [d["ver_dev"]  for d in chart_data]

    fig_dev = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Yatay Sapma (m)", "Dikey Sapma (m)"),
        horizontal_spacing=0.1,
    )

    c_hor = ["#4ade80" if (v or 0) >= 0 else "#f87171" for v in hor_dev]
    c_ver = ["#4ade80" if (v or 0) >= 0 else "#f87171" for v in ver_dev]

    fig_dev.add_trace(
        go.Bar(x=rings, y=hor_dev, marker_color=c_hor, name="Yatay Sapma",
               text=[f"{v:.4f}" for v in hor_dev], textposition="outside", textfont_size=10),
        row=1, col=1,
    )
    fig_dev.add_trace(
        go.Bar(x=rings, y=ver_dev, marker_color=c_ver, name="Dikey Sapma",
               text=[f"{v:.4f}" for v in ver_dev], textposition="outside", textfont_size=10),
        row=1, col=2,
    )
    for col_i in (1, 2):
        fig_dev.add_hline(y=0, line_color="#475569", line_width=1, row=1, col=col_i)

    fig_dev.update_layout(height=420, showlegend=False, **PLOTLY_THEME)
    fig_dev.update_xaxes(tickangle=-45)
    st.plotly_chart(fig_dev, use_container_width=True)


# ── Tab 3: Çap Analizi ────────────────────────────────────────────────────────
with tab_dia:
    diameters = [(d["avg_radius"] or 0) * 2 for d in chart_data]

    fig_dia = go.Figure()
    fig_dia.add_hline(
        y=design_dia, line_dash="dash", line_color="#f59e0b", line_width=2,
        annotation_text=f" Tasarım {design_dia:.3f} m",
        annotation_font_color="#f59e0b",
    )
    fig_dia.add_trace(go.Scatter(
        x=rings, y=diameters,
        mode="lines+markers+text",
        name="Ort. Çap",
        line=dict(color="#60a5fa", width=2.5),
        marker=dict(size=7, color="#60a5fa"),
        text=[f"{v:.4f}" for v in diameters],
        textposition="top center",
        textfont=dict(size=10),
    ))
    fig_dia.update_layout(
        height=420,
        yaxis_title="Çap (m)",
        xaxis_title="Ring",
        xaxis_tickangle=-45,
        **PLOTLY_THEME,
    )
    st.plotly_chart(fig_dia, use_container_width=True)

    # Per-ring stats table
    st.markdown("**Ring başına çap ve sapma özeti**")
    summary_df = pd.DataFrame({
        "Ring":         rings,
        "Chainage (m)": [f"{d['chainage']:.3f}" if d['chainage'] else "—" for d in chart_data],
        "Ort. Çap (m)": [f"{d['avg_radius']*2:.4f}" if d['avg_radius'] else "—" for d in chart_data],
        "Tasarım Çapı": [f"{design_dia:.4f}"] * len(chart_data),
        "Δ Çap (m)":    [f"{d['avg_radius']*2 - design_dia:+.4f}" if d['avg_radius'] else "—" for d in chart_data],
        "Hor. Sapma":   [f"{d['hor_dev']:+.4f}" if d['hor_dev'] is not None else "—" for d in chart_data],
        "Ver. Sapma":   [f"{d['ver_dev']:+.4f}" if d['ver_dev'] is not None else "—" for d in chart_data],
    })
    st.dataframe(summary_df, use_container_width=True, hide_index=True)


# ── Tab 4: Kesit Görünümü ─────────────────────────────────────────────────────
with tab_cross:
    ring_labels = [
        f"{d['ring_no']}  (CH={d['chainage']:.2f}m)" if d['chainage'] else d['ring_no']
        for d in chart_data
    ]
    col_sel, col_info = st.columns([2, 3])
    with col_sel:
        sel_idx = st.selectbox("Ring Seç", range(len(chart_data)), format_func=lambda i: ring_labels[i])

    ring = chart_data[sel_idx]
    avg_r  = ring["avg_radius"]  or 0
    des_r  = ring["design_radius"] or 0

    with col_info:
        ci1, ci2, ci3 = st.columns(3)
        ci1.metric("Best-fit Yarıçap", f"{avg_r:.4f} m")
        ci2.metric("Tasarım Yarıçapı", f"{des_r:.4f} m")
        ci3.metric("Δ Yarıçap",        f"{avg_r - des_r:+.4f} m")

    # Generate circle points
    theta = np.linspace(0, 2 * np.pi, 200)

    fig_cs = go.Figure()

    # Design circle (dashed yellow)
    fig_cs.add_trace(go.Scatter(
        x=des_r * np.sin(theta),
        y=des_r * np.cos(theta),
        mode="lines",
        name="Tasarım Dairesi",
        line=dict(color="#f59e0b", width=1.5, dash="dash"),
    ))

    # Best-fit circle (blue)
    fig_cs.add_trace(go.Scatter(
        x=avg_r * np.sin(theta),
        y=avg_r * np.cos(theta),
        mode="lines",
        name="Best-fit Daire (Kasa)",
        line=dict(color="#60a5fa", width=2.5),
    ))

    # Measured points
    pts = ring["points"]
    if pts:
        fig_cs.add_trace(go.Scatter(
            x=[p["x"] for p in pts],
            y=[p["y"] for p in pts],
            mode="markers+text",
            name="Ölçüm Noktaları",
            marker=dict(color="#f97316", size=9, line=dict(color="#1e293b", width=1)),
            text=[p["label"] for p in pts],
            textposition="top right",
            textfont=dict(size=10, color="#f97316"),
            customdata=[[p.get("r"), p.get("rdbc")] for p in pts],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "x: %{x:.4f} m<br>"
                "y: %{y:.4f} m<br>"
                "Yarıçap: %{customdata[0]:.4f} m<br>"
                "RDBC: %{customdata[1]:.4f} m"
                "<extra></extra>"
            ),
        ))

    # Center cross
    fig_cs.add_trace(go.Scatter(
        x=[0], y=[0],
        mode="markers",
        name="Merkez",
        marker=dict(symbol="cross-thin", size=14, color="#e2e8f0", line=dict(width=2, color="#e2e8f0")),
        showlegend=True,
    ))

    fig_cs.update_layout(
        height=550,
        xaxis=dict(title="Yatay (m)", scaleanchor="y", scaleratio=1, zeroline=True, zerolinecolor="#334155"),
        yaxis=dict(title="Dikey (m)",  zeroline=True, zerolinecolor="#334155"),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
        **PLOTLY_THEME,
    )
    st.plotly_chart(fig_cs, use_container_width=True)

    # Per-point deviation table
    if pts:
        st.markdown("**Nokta başına yarıçap sapmaları (RDBC)**")
        rdbc_df = pd.DataFrame([
            {
                "Nokta":      p["label"],
                "Yarıçap (m)": f"{p['r']:.4f}"   if p['r']    is not None else "—",
                "RDBC (m)":    f"{p['rdbc']:+.4f}" if p['rdbc'] is not None else "—",
                "x (m)":       f"{p['x']:.4f}",
                "y (m)":       f"{p['y']:.4f}",
            }
            for p in pts
        ])
        st.dataframe(rdbc_df, use_container_width=True, hide_index=True, height=280)
