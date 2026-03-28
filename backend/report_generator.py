"""
Wriggle Survey — A4 PDF Report Generator
Matches the professional report template layout.
"""

import io
import math
from datetime import date

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import matplotlib.lines as mlines
import numpy as np


# ── Utilities ─────────────────────────────────────────────────────────────────

def _fmt_ch(ch):
    """9848.214  →  9+848.214"""
    try:
        ch = float(ch)
    except (TypeError, ValueError):
        return '—'
    km = int(ch // 1000)
    m  = ch % 1000
    return f'{km}+{m:07.3f}'


def _s(row, key, default=None):
    """Safe float extraction from a dict/Series row."""
    v = row.get(key, default) if hasattr(row, 'get') else getattr(row, key, default)
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def _ax_off(ax):
    """Turn off axis decorations for a text/drawing panel."""
    ax.axis('off')


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _draw_outer_border(fig):
    """Draw a thin rectangle around the entire figure."""
    fig.patches.append(mpatches.FancyBboxPatch(
        (0.01, 0.01), 0.98, 0.98,
        boxstyle='square,pad=0',
        linewidth=1.5, edgecolor='black', facecolor='none',
        transform=fig.transFigure, zorder=10,
    ))


def _box(ax, x, y, w, h, fc='#f0f0f0', ec='black', lw=0.8, zorder=1):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle='square,pad=0',
        linewidth=lw, edgecolor=ec, facecolor=fc,
        transform=ax.transAxes, zorder=zorder,
    ))


def _txt(ax, x, y, s, **kw):
    kw.setdefault('transform', ax.transAxes)
    kw.setdefault('va', 'center')
    kw.setdefault('fontsize', 8)
    ax.text(x, y, s, **kw)


# ── Section drawing functions ─────────────────────────────────────────────────

def _draw_title_bar(ax, ring_no, chainage, metadata):
    """Top section: title + ring info + metadata boxes."""
    _ax_off(ax)

    # Title
    ax.text(0.5, 0.85, 'WRIGGLE SURVEY REPORT',
            transform=ax.transAxes, ha='center', va='top',
            fontsize=14, fontweight='bold')

    # Left: Ring No & Chainage
    ax.text(0.02, 0.50, f'Ring No. :',  transform=ax.transAxes, va='center', fontsize=9, fontweight='bold')
    ax.text(0.15, 0.50, ring_no,         transform=ax.transAxes, va='center', fontsize=9)
    ax.text(0.02, 0.18, 'Chainage :',   transform=ax.transAxes, va='center', fontsize=9, fontweight='bold')
    ax.text(0.15, 0.18, _fmt_ch(chainage), transform=ax.transAxes, va='center', fontsize=9)

    # Right: metadata table
    right_x = 0.38
    col1_w  = 0.13   # label column width
    col2_w  = 0.30   # value column width
    col3_lx = right_x + col1_w + col2_w + 0.01
    col3_w  = 0.10
    col4_w  = 0.16
    row_h   = 0.28
    rows    = [0.68, 0.35]

    labels   = ['Department :', 'Location :']
    values   = [metadata.get('department', ''), metadata.get('location', '')]
    labels2  = ['Computed by :', 'Calculated Date :']
    values2  = [metadata.get('computed_by', ''), date.today().strftime('%d/%m/%Y')]

    for i, (lbl, val, lbl2, val2) in enumerate(zip(labels, values, labels2, values2)):
        ry = rows[i]
        # Col1: label
        _box(ax, right_x, ry - 0.06, col1_w, row_h, fc='white')
        _txt(ax, right_x + 0.005, ry + 0.08, lbl, fontsize=7.5, fontweight='bold')
        # Col2: value (colored)
        fc_val = '#fff2cc' if i == 0 else '#dce6f1'
        _box(ax, right_x + col1_w, ry - 0.06, col2_w, row_h, fc=fc_val)
        _txt(ax, right_x + col1_w + 0.01, ry + 0.08, val, fontsize=7.5)
        # Col3: label2
        _box(ax, col3_lx, ry - 0.06, col3_w, row_h, fc='white')
        _txt(ax, col3_lx + 0.005, ry + 0.08, lbl2, fontsize=7)
        # Col4: value2
        _box(ax, col3_lx + col3_w, ry - 0.06, col4_w, row_h, fc='#fff2cc')
        _txt(ax, col3_lx + col3_w + 0.01, ry + 0.08, val2, fontsize=7.5)

    # Horizontal separator under title
    ax.plot([0, 1], [0.0, 0.0], color='black', lw=0.8, transform=ax.transAxes, clip_on=False)


def _draw_cross_section(ax, ring_no, points, avg_r, des_r, hor_dev, ver_dev):
    """Main cross-section chart."""
    ax.set_aspect('equal', adjustable='datalim')

    margin = avg_r * 0.35
    lim = avg_r + margin + 0.25
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    ax.set_xlabel('', fontsize=7)
    ax.tick_params(labelsize=7)
    ax.grid(True, linestyle='--', linewidth=0.4, alpha=0.4, color='gray')

    # Axis cross-hair
    ax.axhline(0, color='gray', lw=0.5, zorder=1)
    ax.axvline(0, color='gray', lw=0.5, zorder=1)

    # ── Design circle (centered at origin = design axis) ─────────────────────
    design_patch = mpatches.Circle(
        (0, 0), des_r,
        fill=False, edgecolor='black', linewidth=1.5, linestyle='-', zorder=3,
    )
    ax.add_patch(design_patch)

    # ── Best-fit circle (centered at deviation from design) ──────────────────
    bf_cx = hor_dev or 0.0
    bf_cy = ver_dev or 0.0
    bestfit_patch = mpatches.Circle(
        (bf_cx, bf_cy), avg_r,
        fill=False, edgecolor='red', linewidth=1.5, linestyle='--', zorder=3,
    )
    ax.add_patch(bestfit_patch)

    # ── Best-fit center marker (+) ────────────────────────────────────────────
    ax.plot(bf_cx, bf_cy, 'k+', markersize=12, markeredgewidth=1.5, zorder=5)

    # Deviation label at best-fit center
    ax.text(bf_cx, bf_cy - avg_r * 0.12,
            f'H:{hor_dev:+.3f}, V:{ver_dev:+.3f}',
            ha='center', va='top', fontsize=7.5,
            color='red', style='italic', fontweight='bold', zorder=6)

    # ── Measured points ───────────────────────────────────────────────────────
    label_r = avg_r + 0.18
    ring_num = ring_no.replace('R', '')

    for pt in points:
        ang_deg = pt.get('ang')
        rdbc    = pt.get('rdbc')
        t       = pt.get('no')

        # Point position in design-centered coords
        if ang_deg is not None:
            ang_rad = math.radians(ang_deg)
            r = pt.get('r') or avg_r
            px = bf_cx + r * math.sin(ang_rad)
            py = bf_cy + r * math.cos(ang_rad)
        else:
            px = bf_cx + (pt.get('x') or 0)
            py = bf_cy + (pt.get('y') or 0)

        ax.plot(px, py, 'kx', markersize=7, markeredgewidth=1.5, zorder=4)

        # Label placement: outside best-fit circle
        if ang_deg is not None:
            ang_rad = math.radians(ang_deg)
            lx = bf_cx + label_r * math.sin(ang_rad)
            ly = bf_cy + label_r * math.cos(ang_rad)
            rdbc_str = f'{rdbc:+.3f}' if rdbc is not None else '—'
            label = f'R{ring_num}.{t}, {rdbc_str}'

            # Align based on quadrant
            ha = 'center'
            va = 'center'
            sin_a = math.sin(ang_rad)
            cos_a = math.cos(ang_rad)
            if abs(sin_a) > abs(cos_a):
                ha = 'left' if sin_a > 0 else 'right'
            else:
                va = 'bottom' if cos_a > 0 else 'top'

            ax.text(lx, ly, label, ha=ha, va=va, fontsize=6.5, zorder=5)

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_handles = [
        mlines.Line2D([], [], color='black', lw=1.5, linestyle='-',  label='Design Circle'),
        mlines.Line2D([], [], color='red',   lw=1.5, linestyle='--', label='Best Fit Circle'),
        mlines.Line2D([], [], color='black', marker='+', markersize=9,
                      markeredgewidth=1.5, lw=0, label='Best Fit Center'),
        mlines.Line2D([], [], color='black', marker='x', markersize=7,
                      markeredgewidth=1.5, lw=0, label='Measured Points'),
    ]
    ax.legend(handles=legend_handles, loc='upper right', fontsize=7,
              framealpha=0.9, edgecolor='gray')

    ax.set_title('', pad=2)


def _draw_info_panel(ax, title, rows, title_fc='#dce6f1'):
    """Generic info panel with label/value rows."""
    _ax_off(ax)
    # Border
    _box(ax, 0, 0, 1, 1, fc='white', ec='black', lw=1)
    # Title bar
    _box(ax, 0, 0.88, 1, 0.12, fc=title_fc, ec='black', lw=0.8)
    _txt(ax, 0.5, 0.935, title, ha='center', fontsize=8.5, fontweight='bold')

    n = len(rows)
    row_h = 0.88 / n
    for i, (lbl, val) in enumerate(rows):
        y = 0.88 - (i + 0.5) * row_h
        _txt(ax, 0.05, y, lbl, fontsize=8)
        fc_val = '#e8f0fe' if i % 2 == 0 else '#f5f5f5'
        _box(ax, 0.52, y - row_h * 0.44, 0.46, row_h * 0.88, fc=fc_val, ec='#cccccc', lw=0.5)
        _txt(ax, 0.75, y, val, ha='center', fontsize=8, fontweight='bold')


def _draw_point_table(ax, points, ring_no):
    """Point details table at the bottom."""
    _ax_off(ax)

    ring_num = ring_no.replace('R', '')
    headers = ['Point No.', 'Easting (m.)', 'Northing (m.)', 'Elevation (m.)',
               'Radius (m.)', 'Angle (deg.)', 'RDBC (m.)']
    col_xs  = [0.01, 0.11, 0.25, 0.39, 0.53, 0.66, 0.79]
    col_ws  = [0.10, 0.14, 0.14, 0.14, 0.13, 0.13, 0.13]

    n_rows = len(points) + 1  # +1 for header
    row_h  = 1.0 / max(n_rows, 1)
    header_y = 1.0 - row_h * 0.5

    # Header background
    _box(ax, 0, 1.0 - row_h, 1.0, row_h, fc='#1F4E79', ec='black', lw=0.8)
    for j, (hdr, cx, cw) in enumerate(zip(headers, col_xs, col_ws)):
        _txt(ax, cx + cw * 0.5, header_y, hdr,
             ha='center', fontsize=7, fontweight='bold', color='white')

    # Data rows
    for i, pt in enumerate(points):
        y_center = 1.0 - (i + 1.5) * row_h
        y_top    = 1.0 - (i + 1)   * row_h
        fc = '#eaf3fb' if i % 2 == 0 else 'white'
        _box(ax, 0, y_top - row_h, 1.0, row_h, fc=fc, ec='#cccccc', lw=0.4)

        pno = f'R{ring_num}.{pt["no"]}'
        vals = [
            pno,
            f'{pt["e"]:.3f}'    if pt.get("e")    is not None else '—',
            f'{pt["n"]:.3f}'    if pt.get("n")    is not None else '—',
            f'{pt["z"]:.3f}'    if pt.get("z")    is not None else '—',
            f'{pt["r"]:.4f}'    if pt.get("r")    is not None else '—',
            f'{pt["ang"]:.3f}'  if pt.get("ang")  is not None else '—',
            f'{pt["rdbc"]:+.4f}' if pt.get("rdbc") is not None else '—',
        ]
        for val, cx, cw in zip(vals, col_xs, col_ws):
            _txt(ax, cx + cw * 0.5, y_center, val, ha='center', fontsize=7)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_ring_report(
    backup_row,
    result_row,
    metadata: dict = None,
    dpi: int = 150,
) -> bytes:
    """
    Generate an A4 PDF/PNG report for a single ring.

    Parameters
    ----------
    backup_row : dict/Series  — one row from df_backup
    result_row : dict/Series  — corresponding row from df_result
    metadata   : dict         — department, location, computed_by
    dpi        : int          — output resolution

    Returns
    -------
    bytes — PDF file content
    """
    if metadata is None:
        metadata = {}

    # ── Parse backup row ──────────────────────────────────────────────────────
    def s(k, d=None): return _s(backup_row, k, d)

    ring_no  = str(backup_row.get('RING NO.', 'R?') if hasattr(backup_row, 'get') else getattr(backup_row, 'RING NO.', 'R?'))
    num_pnt  = int(s('NUM.PNT', 0) or 0)
    chainage = s('CH', 0)
    hor_dev  = s('DH', 0) or 0.0
    ver_dev  = s('DV', 0) or 0.0
    avg_r    = s('AVG.R', 0) or 0.0
    avg_dia  = avg_r * 2
    des_r    = s('DESING.CL-R', 0) or 0.0
    des_dia  = s('DESING.CL-DIA', 0) or des_r * 2
    des_e    = s('DESING.CL-E', 0)
    des_n    = s('DESING.CL-N', 0)
    des_z    = s('DESING.CL-Z', 0)
    xc       = s('X_C', 0) or 0.0
    yc_raw   = s('Y_C', 0) or 0.0
    yc       = yc_raw - 100

    # Best-fit from result row
    def rs(k, d=None): return _s(result_row, k, d)
    bf_e = rs('TUN.CL-EASTING (M.)',  des_e)
    bf_n = rs('TUN.CL-NORTHING (M.)', des_n)
    bf_z = rs('TUN.CL-ELEVATION (M.)', des_z)

    # Parse measured points
    points = []
    for t in range(1, num_pnt + 1):
        xv    = s(f'X_P{t}')
        yv_rw = s(f'Y_P{t}')
        if xv is None or yv_rw is None:
            continue
        points.append({
            'no':  t,
            'x':   xv - xc,
            'y':   yv_rw - 100 - yc,
            'r':   s(f'R_P{t}'),
            'rdbc': s(f'RDBC_P{t}'),
            'ang': s(f'ANG_P{t}'),
            'e':   s(f'E_P{t}'),
            'n':   s(f'N_P{t}'),
            'z':   s(f'Z_P{t}'),
        })

    # ── Figure layout ─────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(8.27, 11.69), facecolor='white', dpi=dpi)
    _draw_outer_border(fig)

    gs = gridspec.GridSpec(
        4, 1, figure=fig,
        height_ratios=[0.08, 0.49, 0.18, 0.25],
        hspace=0.04,
        top=0.97, bottom=0.02, left=0.04, right=0.96,
    )

    # Row 0 — Title + metadata header
    ax_hdr = fig.add_subplot(gs[0])
    _draw_title_bar(ax_hdr, ring_no, chainage, metadata)

    # Row 1 — Cross-section chart
    ax_cs = fig.add_subplot(gs[1])
    _draw_cross_section(ax_cs, ring_no, points, avg_r, des_r, hor_dev, ver_dev)

    # Row 2 — Info panels
    gs_info = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs[2], wspace=0.03)
    ax_des = fig.add_subplot(gs_info[0])
    ax_bf  = fig.add_subplot(gs_info[1])

    _draw_info_panel(ax_des, 'Design (Tunnel Center)', [
        ('Easting (m.)',  f'{des_e:.3f}' if des_e is not None else '—'),
        ('Northing (m.)', f'{des_n:.3f}' if des_n is not None else '—'),
        ('Elevation (m.)',f'{des_z:.3f}' if des_z is not None else '—'),
        ('Radius (m.)',   f'{des_r:.4f}'),
        ('Diameter (m.)', f'{des_dia:.4f}'),
        ('Method',        'Circle'),
        ('Slope',         'Vertical Section to Tunnel Axis'),
    ], title_fc='#dce6f1')

    _draw_info_panel(ax_bf, 'Best Fit Circle Result (Tunnel Center)', [
        ('Easting (m.)',            f'{bf_e:.3f}' if bf_e is not None else '—'),
        ('Northing (m.)',           f'{bf_n:.3f}' if bf_n is not None else '—'),
        ('Elevation (m.)',          f'{bf_z:.3f}' if bf_z is not None else '—'),
        ('Average Radius (m.)',     f'{avg_r:.4f}'),
        ('Average Diameter (m.)',   f'{avg_dia:.4f}'),
        ('Chainage (m.)',           _fmt_ch(chainage)),
        ('Horizontal Deviation (m.)', f'{hor_dev:+.4f}'),
        ('Vertical Deviation (m.)',   f'{ver_dev:+.4f}'),
    ], title_fc='#e2efda')

    # Row 3 — Point table
    ax_tbl = fig.add_subplot(gs[3])
    _draw_point_table(ax_tbl, points, ring_no)

    # ── Render to PDF bytes ───────────────────────────────────────────────────
    buf = io.BytesIO()
    fig.savefig(buf, format='pdf', bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_ring_figure(backup_row, result_row, metadata=None, dpi=120):
    """
    Same as generate_ring_report but returns the matplotlib Figure
    so Streamlit can display it inline with st.pyplot().
    """
    if metadata is None:
        metadata = {}

    def s(k, d=None): return _s(backup_row, k, d)

    ring_no  = str(backup_row.get('RING NO.', 'R?') if hasattr(backup_row, 'get') else getattr(backup_row, 'RING NO.', 'R?'))
    num_pnt  = int(s('NUM.PNT', 0) or 0)
    chainage = s('CH', 0)
    hor_dev  = s('DH', 0) or 0.0
    ver_dev  = s('DV', 0) or 0.0
    avg_r    = s('AVG.R', 0) or 0.0
    avg_dia  = avg_r * 2
    des_r    = s('DESING.CL-R', 0) or 0.0
    des_dia  = s('DESING.CL-DIA', 0) or des_r * 2
    des_e    = s('DESING.CL-E', 0)
    des_n    = s('DESING.CL-N', 0)
    des_z    = s('DESING.CL-Z', 0)
    xc       = s('X_C', 0) or 0.0
    yc_raw   = s('Y_C', 0) or 0.0
    yc       = yc_raw - 100

    def rs(k, d=None): return _s(result_row, k, d)
    bf_e = rs('TUN.CL-EASTING (M.)',  des_e)
    bf_n = rs('TUN.CL-NORTHING (M.)', des_n)
    bf_z = rs('TUN.CL-ELEVATION (M.)', des_z)

    points = []
    for t in range(1, num_pnt + 1):
        xv    = s(f'X_P{t}')
        yv_rw = s(f'Y_P{t}')
        if xv is None or yv_rw is None:
            continue
        points.append({
            'no': t, 'x': xv - xc, 'y': yv_rw - 100 - yc,
            'r': s(f'R_P{t}'), 'rdbc': s(f'RDBC_P{t}'),
            'ang': s(f'ANG_P{t}'),
            'e': s(f'E_P{t}'), 'n': s(f'N_P{t}'), 'z': s(f'Z_P{t}'),
        })

    fig = plt.figure(figsize=(8.27, 11.69), facecolor='white', dpi=dpi)
    _draw_outer_border(fig)

    gs = gridspec.GridSpec(
        4, 1, figure=fig,
        height_ratios=[0.08, 0.49, 0.18, 0.25],
        hspace=0.04,
        top=0.97, bottom=0.02, left=0.04, right=0.96,
    )

    ax_hdr = fig.add_subplot(gs[0])
    _draw_title_bar(ax_hdr, ring_no, chainage, metadata)

    ax_cs = fig.add_subplot(gs[1])
    _draw_cross_section(ax_cs, ring_no, points, avg_r, des_r, hor_dev, ver_dev)

    gs_info = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs[2], wspace=0.03)
    ax_des = fig.add_subplot(gs_info[0])
    ax_bf  = fig.add_subplot(gs_info[1])

    _draw_info_panel(ax_des, 'Design (Tunnel Center)', [
        ('Easting (m.)',  f'{des_e:.3f}' if des_e is not None else '—'),
        ('Northing (m.)', f'{des_n:.3f}' if des_n is not None else '—'),
        ('Elevation (m.)',f'{des_z:.3f}' if des_z is not None else '—'),
        ('Radius (m.)',   f'{des_r:.4f}'),
        ('Diameter (m.)', f'{des_dia:.4f}'),
        ('Method',        'Circle'),
        ('Slope',         'Vertical Section to Tunnel Axis'),
    ], title_fc='#dce6f1')

    _draw_info_panel(ax_bf, 'Best Fit Circle Result (Tunnel Center)', [
        ('Easting (m.)',            f'{bf_e:.3f}' if bf_e is not None else '—'),
        ('Northing (m.)',           f'{bf_n:.3f}' if bf_n is not None else '—'),
        ('Elevation (m.)',          f'{bf_z:.3f}' if bf_z is not None else '—'),
        ('Average Radius (m.)',     f'{avg_r:.4f}'),
        ('Average Diameter (m.)',   f'{avg_dia:.4f}'),
        ('Chainage (m.)',           _fmt_ch(chainage)),
        ('Horizontal Deviation (m.)', f'{hor_dev:+.4f}'),
        ('Vertical Deviation (m.)',   f'{ver_dev:+.4f}'),
    ], title_fc='#e2efda')

    ax_tbl = fig.add_subplot(gs[3])
    _draw_point_table(ax_tbl, points, ring_no)

    return fig
