"""
Wriggle Survey — Streamlit Application
Sol panel: veri girişi / Orta alan: rapor önizlemesi
"""

import sys, os, io, math
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from wriggle_core import compute_wriggle_survey
from landxml_parser import parse_landxml_to_dta, list_alignments
from report_generator import generate_ring_figure, generate_ring_report

# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Wriggle Survey",
    page_icon="⭕",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
[data-testid="stSidebar"] { min-width: 300px; max-width: 340px; }
[data-testid="stSidebar"] .stButton > button { width: 100%; }
section[data-testid="stSidebarContent"] { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _safe(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def prepare_wrs_data(df: pd.DataFrame, points_per_ring: int, prism_offset: float) -> pd.DataFrame:
    required = {"EASTING (M.)", "NORTHING (M.)", "ELEVATION (M.)"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"Eksik sütunlar: {missing}")
    df = df.reset_index(drop=True)
    total = len(df)
    rows = []
    for i, src in df.iterrows():
        pos      = i % points_per_ring
        ring_no  = i // points_per_ring
        is_first = pos == 0
        pts      = min(points_per_ring, total - ring_no * points_per_ring)
        rows.append({
            "RING NO.":       ring_no,
            "POINT NO.":      pos + 1,
            "EASTING (M.)":   src["EASTING (M.)"],
            "NORTHING (M.)":  src["NORTHING (M.)"],
            "ELEVATION (M.)": src["ELEVATION (M.)"],
            "OFFSET (M.)":    prism_offset,
            "NUM. POINTS":    pts if is_first else None,
        })
    return pd.DataFrame(rows)


def build_chart_data(df_backup: pd.DataFrame) -> list[dict]:
    rows = []
    for _, row in df_backup.iterrows():
        num_pnt = int(row.get("NUM.PNT", 0) or 0)
        xc = _safe(row.get("X_C"))
        yc = (_safe(row.get("Y_C")) or 0) - 100
        points = []
        for t in range(1, num_pnt + 1):
            xv = _safe(row.get(f"X_P{t}"))
            yv_r = _safe(row.get(f"Y_P{t}"))
            yv = (yv_r - 100) if yv_r is not None else None
            if xv is not None and yv is not None and xc is not None:
                points.append({
                    "label": f"P{t}",
                    "x": round(xv - xc, 6),
                    "y": round(yv - yc, 6),
                    "rdbc": _safe(row.get(f"RDBC_P{t}")),
                    "r":    _safe(row.get(f"R_P{t}")),
                    "ang":  _safe(row.get(f"ANG_P{t}")),
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


# ═══════════════════════════════════════════════════════════════════════════════
# LEFT SIDEBAR — TÜM GİRİŞLER
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⭕ Wriggle Survey")
    st.caption("Best-Fit Circle 3D — Kasa Method")
    st.divider()

    # ── 1. Tünel Bilgileri ────────────────────────────────────────────────────
    st.markdown("### 🏗️ Tünel Bilgileri")
    dia_design = st.number_input(
        "Tasarım Çapı (m)", value=3.396, min_value=0.1, step=0.001, format="%.3f")
    direction = st.selectbox("Kazı Yönü", ["DIRECT", "REVERSE"])

    st.divider()

    # ── 2. Ölçüm Ayarları ────────────────────────────────────────────────────
    st.markdown("### 📐 Ölçüm Ayarları")
    points_per_ring = st.number_input(
        "Ring başına nokta sayısı", value=8, min_value=3, max_value=16, step=1)
    prism_offset = st.number_input(
        "Prizma Offset (m)", value=0.038, min_value=0.0, step=0.001, format="%.3f")

    st.divider()

    # ── 3. Wriggle Ölçüm Verisi ──────────────────────────────────────────────
    st.markdown("### 📍 Wriggle Ölçüm Verisi")
    st.caption("Sütunlar: POINT NO. | EASTING | NORTHING | ELEVATION")
    wrs_file = st.file_uploader(
        "Excel yükle (.xlsx)", type=["xlsx","xls"], key="wrs",
        help="İlk sayfa okunur. 4 sütun yeterli — ring gruplaması otomatik.")
    wrs_bytes = wrs_file.getvalue() if wrs_file else None

    st.divider()

    # ── 4. Güzergah (DTA) ────────────────────────────────────────────────────
    st.markdown("### 🗺️ Tünel Güzergahı (DTA)")
    dta_fmt = st.radio("Format", ["LandXML (.xml)", "Excel (.xlsx)"], horizontal=True)
    dta_is_xml = dta_fmt == "LandXML (.xml)"

    if dta_is_xml:
        sample_interval = st.number_input(
            "Örnekleme Aralığı (m)", value=1.0, min_value=0.1, step=0.5, format="%.1f")
        dta_file = st.file_uploader(
            "LandXML yükle", type=["xml","landxml"], key="dta_xml",
            help="AutoCAD Civil 3D, Trimble, Leica vb.")
    else:
        sample_interval = 1.0
        dta_file = st.file_uploader(
            "DTA Excel yükle (.xlsx)", type=["xlsx","xls"], key="dta_xl",
            help="Sütunlar: POINT NO. | CHAINAGE | EASTING | NORTHING | ELEVATION")

    dta_bytes = dta_file.getvalue() if dta_file else None

    if dta_is_xml and dta_bytes:
        names = list_alignments(dta_bytes)
        if names:
            st.info(f"Güzergah: **{names[0]}**" +
                    (f" (+{len(names)-1} diğer)" if len(names) > 1 else ""))

    st.divider()

    # ── 5. Rapor Bilgileri ───────────────────────────────────────────────────
    st.markdown("### 📋 Rapor Bilgileri")
    meta_dept = st.text_input("Department",  value="Survey Section")
    meta_loc  = st.text_input("Location",    value="")
    meta_by   = st.text_input("Computed by", value="")

    st.divider()

    # ── 6. Hesapla butonu ─────────────────────────────────────────────────────
    can_compute = wrs_bytes is not None and dta_bytes is not None
    compute_btn = st.button("▶ Hesapla", type="primary", disabled=not can_compute)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPUTE
# ═══════════════════════════════════════════════════════════════════════════════
if compute_btn:
    with st.spinner("Hesaplanıyor..."):
        try:
            df_wrs_raw = pd.read_excel(io.BytesIO(wrs_bytes), sheet_name=0)
            if "NUM. POINTS" in df_wrs_raw.columns:
                df_wrs = df_wrs_raw
            else:
                df_wrs = prepare_wrs_data(df_wrs_raw, int(points_per_ring), float(prism_offset))

            if dta_is_xml:
                df_dta = parse_landxml_to_dta(dta_bytes, float(sample_interval))
            else:
                df_dta = pd.read_excel(io.BytesIO(dta_bytes), sheet_name=0)

            df_result, df_backup = compute_wriggle_survey(df_wrs, df_dta, dia_design, direction)

            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                df_result.to_excel(writer, sheet_name="WRIGGLE RESULT", index=False)
                df_backup.to_excel(writer, sheet_name="WRIGGLE BACKUP", index=False)

            st.session_state.update({
                "df_result":    df_result,
                "df_backup":    df_backup,
                "chart_data":   build_chart_data(df_backup),
                "dia_design":   dia_design,
                "excel_bytes":  excel_buf.getvalue(),
                "metadata":     {"department": meta_dept, "location": meta_loc, "computed_by": meta_by},
            })

        except Exception as exc:
            st.error(f"**Hata:** {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN AREA — RAPOR + ANALİZ
# ═══════════════════════════════════════════════════════════════════════════════
if "df_result" not in st.session_state:
    st.markdown("## ⭕ Wriggle Survey")
    st.info("**Sol panelden** veri yükleyin ve **Hesapla** butonuna basın.")
    st.stop()

df_result  = st.session_state["df_result"]
df_backup  = st.session_state["df_backup"]
chart_data = st.session_state["chart_data"]
design_dia = st.session_state["dia_design"]
metadata   = st.session_state["metadata"]

# ── Üst bar: özet metrikler + download ───────────────────────────────────────
n_rings  = len(df_result)
dh_vals  = df_result["HOR.DEVIATION (M.)"].dropna().values
dv_vals  = df_result["VER.DEVIATION (M.)"].dropna().values
dia_vals = df_result["AVG.DIAMETER (M.)"].dropna().values

top_left, top_right = st.columns([3, 1])
with top_left:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ring Sayısı",        f"{n_rings}")
    c2.metric("Maks. Yatay Sapma",  f"{np.max(np.abs(dh_vals)):.4f} m"  if len(dh_vals)  else "—")
    c3.metric("Maks. Dikey Sapma",  f"{np.max(np.abs(dv_vals)):.4f} m"  if len(dv_vals)  else "—")
    c4.metric("Ort. Çap",           f"{np.mean(dia_vals):.4f} m"        if len(dia_vals) else "—")
with top_right:
    st.download_button(
        "⬇ Excel İndir", data=st.session_state["excel_bytes"],
        file_name="Export_Wriggle_Survey.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.divider()

# ── Sekmeler ─────────────────────────────────────────────────────────────────
tab_report, tab_table, tab_charts = st.tabs([
    "📄 Wriggle Survey Report",
    "📋 Sonuç Tablosu",
    "📊 Grafikler",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — RAPOR ÖNİZLEME
# ─────────────────────────────────────────────────────────────────────────────
with tab_report:
    ring_labels = [
        f"{d['ring_no']}  —  CH {d['chainage']:.3f} m" if d['chainage'] else d['ring_no']
        for d in chart_data
    ]
    col_sel, col_dl = st.columns([3, 1])
    with col_sel:
        sel_idx = st.selectbox("Ring Seç", range(n_rings), format_func=lambda i: ring_labels[i])
    with col_dl:
        # PDF download for selected ring
        pdf_bytes = generate_ring_report(
            dict(df_backup.iloc[sel_idx]),
            dict(df_result.iloc[sel_idx]),
            metadata=metadata,
            dpi=150,
        )
        st.download_button(
            "⬇ PDF İndir (Bu Ring)",
            data=pdf_bytes,
            file_name=f"Wriggle_{df_result.iloc[sel_idx]['RING NO.']}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    # Rapor önizlemesi
    with st.spinner("Rapor oluşturuluyor..."):
        fig = generate_ring_figure(
            dict(df_backup.iloc[sel_idx]),
            dict(df_result.iloc[sel_idx]),
            metadata=metadata,
            dpi=110,
        )
    st.pyplot(fig, use_container_width=True)
    import matplotlib.pyplot as plt
    plt.close(fig)

    # Tüm ringler için PDF
    st.divider()
    if st.button("📦 Tüm Ringler için PDF Oluştur", use_container_width=False):
        import matplotlib.backends.backend_pdf as pdf_backend
        all_pdf = io.BytesIO()
        with pdf_backend.PdfPages(all_pdf) as pp:
            for i in range(n_rings):
                f = generate_ring_figure(
                    dict(df_backup.iloc[i]),
                    dict(df_result.iloc[i]),
                    metadata=metadata, dpi=120,
                )
                pp.savefig(f, bbox_inches='tight')
                plt.close(f)
        st.download_button(
            "⬇ Tüm Ringler PDF İndir",
            data=all_pdf.getvalue(),
            file_name="Wriggle_Survey_All_Rings.pdf",
            mime="application/pdf",
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — SONUÇ TABLOSU
# ─────────────────────────────────────────────────────────────────────────────
with tab_table:
    def colour_dev(val):
        try:
            return "color: #4ade80" if float(val) >= 0 else "color: #f87171"
        except Exception:
            return ""

    styled = (
        df_result.style
        .applymap(colour_dev, subset=["HOR.DEVIATION (M.)", "VER.DEVIATION (M.)"])
        .format({
            "TUN.CL-EASTING (M.)":   "{:.3f}",
            "TUN.CL-NORTHING (M.)":  "{:.3f}",
            "TUN.CL-ELEVATION (M.)": "{:.3f}",
            "CHAINAGE (M.)":         "{:.3f}",
            "HOR.DEVIATION (M.)":    "{:+.4f}",
            "VER.DEVIATION (M.)":    "{:+.4f}",
            "AVG.RADIUS (M.)":       "{:.4f}",
            "AVG.DIAMETER (M.)":     "{:.4f}",
        }, na_rep="—")
    )
    st.dataframe(styled, use_container_width=True, height=500)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — GRAFİKLER
# ─────────────────────────────────────────────────────────────────────────────
with tab_charts:
    THEME = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0f172a",
        font=dict(color="#94a3b8", size=11),
        margin=dict(l=50, r=20, t=40, b=50),
    )

    rings   = [d["ring_no"]  for d in chart_data]
    hor_dev = [d["hor_dev"]  for d in chart_data]
    ver_dev = [d["ver_dev"]  for d in chart_data]
    diam    = [(d["avg_radius"] or 0) * 2 for d in chart_data]

    # Deviation charts
    fig_dev = make_subplots(rows=1, cols=2,
        subplot_titles=("Yatay Sapma (m)", "Dikey Sapma (m)"),
        horizontal_spacing=0.1)
    from plotly.graph_objects import Bar
    fig_dev.add_trace(Bar(x=rings, y=hor_dev,
        marker_color=["#4ade80" if (v or 0)>=0 else "#f87171" for v in hor_dev],
        name="Yatay"), row=1, col=1)
    fig_dev.add_trace(Bar(x=rings, y=ver_dev,
        marker_color=["#4ade80" if (v or 0)>=0 else "#f87171" for v in ver_dev],
        name="Dikey"), row=1, col=2)
    fig_dev.add_hline(y=0, line_color="#475569", row=1, col=1)
    fig_dev.add_hline(y=0, line_color="#475569", row=1, col=2)
    fig_dev.update_layout(height=380, showlegend=False, **THEME)
    fig_dev.update_xaxes(tickangle=-45)
    st.plotly_chart(fig_dev, use_container_width=True)

    # Diameter chart
    from plotly.graph_objects import Scatter
    fig_dia = go.Figure()
    fig_dia.add_hline(y=design_dia, line_dash="dash", line_color="#f59e0b",
                      annotation_text=f"Tasarım {design_dia:.3f}m",
                      annotation_font_color="#f59e0b")
    fig_dia.add_trace(Scatter(x=rings, y=diam, mode="lines+markers+text",
        line=dict(color="#60a5fa", width=2), marker=dict(size=7),
        text=[f"{v:.4f}" for v in diam], textposition="top center", textfont_size=9))
    fig_dia.update_layout(height=360, yaxis_title="Çap (m)",
                          xaxis_tickangle=-45, **THEME)
    st.plotly_chart(fig_dia, use_container_width=True)
