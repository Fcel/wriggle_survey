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


def normalise_dta_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename DTA Excel columns to the standard names expected by wriggle_core.
    Handles case-insensitive and unit-suffix variations.
    """
    rename_map = {}
    for col in df.columns:
        c = col.strip().lower().replace(" ", "").replace("_", "")
        if c in ("chainage", "chainage(m)", "ch", "station", "station(m)"):
            rename_map[col] = "CHAINAGE"
        elif c in ("easting", "easting(m)", "easting(m.)", "e", "e(m)"):
            rename_map[col] = "EASTING (M.)"
        elif c in ("northing", "northing(m)", "northing(m.)", "n", "n(m)"):
            rename_map[col] = "NORTHING (M.)"
        elif c in ("elevation", "elevation(m)", "elevation(m.)", "z", "z(m)", "elev", "elev(m)"):
            rename_map[col] = "ELEVATION (M.)"
        elif c in ("pointno", "pointno.", "pointnumber", "no", "no.", "id"):
            rename_map[col] = "POINT NO."
        # Azimuth column: keep but not required by wriggle_core
    df = df.rename(columns=rename_map)
    # Add POINT NO. if missing
    if "POINT NO." not in df.columns:
        df.insert(0, "POINT NO.", range(1, len(df) + 1))
    # Add ELEVATION if missing
    if "ELEVATION (M.)" not in df.columns:
        df["ELEVATION (M.)"] = 0.0
    return df


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
        swap_en = st.checkbox(
            "E/N sırasını ters çevir",
            value=False,
            help="LandXML Start/Center koordinatları 'Easting Northing' sırasındaysa işaretle")
        dta_file = st.file_uploader(
            "LandXML yükle", type=["xml","landxml"], key="dta_xml",
            help="AutoCAD Civil 3D, Trimble, Leica vb.")
    else:
        sample_interval = 1.0
        swap_en = False
        dta_file = st.file_uploader(
            "DTA Excel yükle (.xlsx)", type=["xlsx","xls"], key="dta_xl",
            help="Sütunlar: POINT NO. | CHAINAGE | EASTING | NORTHING | ELEVATION")

    dta_bytes = dta_file.getvalue() if dta_file else None

    if dta_is_xml and dta_bytes:
        names = list_alignments(dta_bytes)
        if names:
            st.info(f"Güzergah: **{names[0]}**" +
                    (f" (+{len(names)-1} diğer)" if len(names) > 1 else ""))

    # ── Koordinat Tanılama ────────────────────────────────────────────────────
    if wrs_bytes and dta_bytes:
        with st.expander("🔍 Koordinat Tanılama", expanded=False):
            try:
                _df_wrs_p = pd.read_excel(io.BytesIO(wrs_bytes), sheet_name=0)
                if "EASTING (M.)" not in _df_wrs_p.columns:
                    _df_wrs_p = prepare_wrs_data(_df_wrs_p, int(points_per_ring), float(prism_offset))
                st.caption("**Wriggle Verisi (E/N aralığı):**")
                st.write(f"E: `{_df_wrs_p['EASTING (M.)'].min():.3f}` → `{_df_wrs_p['EASTING (M.)'].max():.3f}`")
                st.write(f"N: `{_df_wrs_p['NORTHING (M.)'].min():.3f}` → `{_df_wrs_p['NORTHING (M.)'].max():.3f}`")
            except Exception as _e:
                st.warning(f"WRS parse hatası: {_e}")
            try:
                if dta_is_xml:
                    _df_dta_p = parse_landxml_to_dta(dta_bytes, float(sample_interval), swap_en=swap_en)
                else:
                    _df_dta_p = normalise_dta_columns(pd.read_excel(io.BytesIO(dta_bytes), sheet_name=0))
                st.caption("**DTA / Güzergah (E/N / Chainage aralığı):**")
                st.write(f"E: `{_df_dta_p['EASTING (M.)'].min():.3f}` → `{_df_dta_p['EASTING (M.)'].max():.3f}`")
                st.write(f"N: `{_df_dta_p['NORTHING (M.)'].min():.3f}` → `{_df_dta_p['NORTHING (M.)'].max():.3f}`")
                st.write(f"Chainage: `{_df_dta_p['CHAINAGE'].min():.3f}` → `{_df_dta_p['CHAINAGE'].max():.3f}`")
                # Check overlap
                wrs_e_ok = (_df_wrs_p['EASTING (M.)'].min()  < _df_dta_p['EASTING (M.)'].max() and
                            _df_wrs_p['EASTING (M.)'].max()  > _df_dta_p['EASTING (M.)'].min())
                wrs_n_ok = (_df_wrs_p['NORTHING (M.)'].min() < _df_dta_p['NORTHING (M.)'].max() and
                            _df_wrs_p['NORTHING (M.)'].max() > _df_dta_p['NORTHING (M.)'].min())
                if wrs_e_ok and wrs_n_ok:
                    st.success("✅ E/N aralıkları örtüşüyor")
                else:
                    st.error("❌ E/N aralıkları örtüşmüyor — koordinat sistemi uyumsuz olabilir!")
            except Exception as _e:
                st.warning(f"DTA parse hatası: {_e}")

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
                df_dta = parse_landxml_to_dta(dta_bytes, float(sample_interval), swap_en=swap_en)
            else:
                df_dta = normalise_dta_columns(pd.read_excel(io.BytesIO(dta_bytes), sheet_name=0))

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

# ── Koordinat uyumsuzluğu uyarısı ─────────────────────────────────────────────
if len(dh_vals) and np.max(np.abs(dh_vals)) > 2.0:
    st.warning(
        f"⚠️ **Koordinat uyumsuzluğu?** "
        f"Maks. yatay sapma `{np.max(np.abs(dh_vals)):.3f} m` — bu tünel için çok büyük.\n\n"
        "Sol paneldeki **🔍 Koordinat Tanılama** bölümünü açarak WRS ve DTA koordinat "
        "aralıklarının örtüşüp örtüşmediğini kontrol edin.\n\n"
        "**Olası nedenler:**\n"
        "- LandXML dosyasında E/N sırası ters (Easting önce, Northing sonra)\n"
        "- WRS ve DTA farklı koordinat sisteminde (UTM zone farkı vb.)\n"
        "- DTA staStart değeri yanlış"
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

    def colour_dist(val):
        try:
            v = float(val)
            if v > 10:   return "background-color: #7f1d1d; color: white"
            if v > 2:    return "background-color: #78350f; color: white"
            return ""
        except Exception:
            return ""

    # Build display table: result + MIN_DIST_DTA from backup
    df_display = df_result.copy()
    if "MIN_DIST_DTA" in df_backup.columns:
        df_display["MIN_DIST_DTA (m)"] = df_backup["MIN_DIST_DTA"].values
        df_display["TUN.CL-E (m)"]     = df_backup["TUN.CL-E"].values
        df_display["TUN.CL-N (m)"]     = df_backup["TUN.CL-N"].values

    fmt = {
        "TUN.CL-EASTING (M.)":   "{:.3f}",
        "TUN.CL-NORTHING (M.)":  "{:.3f}",
        "TUN.CL-ELEVATION (M.)": "{:.3f}",
        "CHAINAGE (M.)":         "{:.3f}",
        "HOR.DEVIATION (M.)":    "{:+.4f}",
        "VER.DEVIATION (M.)":    "{:+.4f}",
        "AVG.RADIUS (M.)":       "{:.4f}",
        "AVG.DIAMETER (M.)":     "{:.4f}",
    }
    subset_dev  = ["HOR.DEVIATION (M.)", "VER.DEVIATION (M.)"]
    subset_dist = ["MIN_DIST_DTA (m)"] if "MIN_DIST_DTA (m)" in df_display.columns else []

    if subset_dist:
        fmt["MIN_DIST_DTA (m)"] = "{:.3f}"
        fmt["TUN.CL-E (m)"]     = "{:.3f}"
        fmt["TUN.CL-N (m)"]     = "{:.3f}"

    styled = df_display.style.map(colour_dev, subset=subset_dev)
    if subset_dist:
        styled = styled.map(colour_dist, subset=subset_dist)
    styled = styled.format(fmt, na_rep="—")

    if subset_dist:
        max_dist = df_display["MIN_DIST_DTA (m)"].max()
        if max_dist > 2:
            st.error(
                f"**MIN_DIST_DTA** sütunu: ring merkezi ile en yakın DTA noktası arası mesafe. "
                f"Maksimum `{max_dist:.2f} m` — bu değer büyükse WRS ve DTA koordinatları uyumsuz demektir.\n\n"
                f"**Beklenen**: < 2 m  |  **Hesaplanan**: {max_dist:.2f} m"
            )
        else:
            st.success(f"DTA koordinat eşleşmesi iyi (maks. dist = {max_dist:.2f} m)")

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
