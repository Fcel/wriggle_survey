# LandXML → Tunnel Axis (DTA) DataFrame parser
# Supports: Alignment with CoordGeom (Line, Curve) + Profile (PVI)
#           CgPoints fallback

import xml.etree.ElementTree as ET
import math
import re
import numpy as np
import pandas as pd


# ─── Namespace helpers ────────────────────────────────────────────────────────

def _detect_ns(root):
    """Return XML namespace of the root element (empty string if none)."""
    m = re.match(r'\{(.+)\}', root.tag)
    return m.group(1) if m else ""

def _t(ns, tag):
    """Build a namespaced tag string."""
    return f'{{{ns}}}{tag}' if ns else tag

def _strip_ns(tag):
    """Remove namespace from a tag."""
    return tag.split('}')[-1] if '}' in tag else tag

def _parse_pair(text):
    """
    Parse 'N E' or 'N E Z' coordinate text.
    LandXML CoordGeom uses Northing Easting order.
    Returns list of floats.
    """
    return [float(v) for v in text.strip().split()]


# ─── Vertical profile ─────────────────────────────────────────────────────────

def _parse_profile(alignment_elem, ns):
    """
    Parse <Profile>/<ProfAlign> and return sorted list of (station, elevation).
    Handles both attribute-style and text-style PVI elements.
    Ignores vertical curve smoothing (linear between PVIs).
    """
    pvs = []

    profile = alignment_elem.find(_t(ns, 'Profile'))
    if profile is None:
        return pvs

    prof_align = profile.find(_t(ns, 'ProfAlign'))
    if prof_align is None:
        return pvs

    for child in prof_align:
        tag = _strip_ns(child.tag)
        if tag not in ('PVI', 'CircCurve', 'ParaCurve'):
            continue

        # Attribute style: staAhead/elvPVI
        sta  = child.get('staAhead') or child.get('sta')
        elev = child.get('elvPVI')   or child.get('elv')

        if sta and elev:
            pvs.append((float(sta), float(elev)))
        elif child.text and child.text.strip():
            parts = child.text.strip().split()
            if len(parts) >= 2:
                pvs.append((float(parts[0]), float(parts[1])))

    return sorted(pvs, key=lambda x: x[0])


def _elev_at_station(pvs, sta):
    """Linear interpolation / extrapolation of elevation at a given station."""
    if not pvs:
        return 0.0
    if sta <= pvs[0][0]:
        return pvs[0][1]
    if sta >= pvs[-1][0]:
        return pvs[-1][1]
    for i in range(len(pvs) - 1):
        s0, z0 = pvs[i]
        s1, z1 = pvs[i + 1]
        if s0 <= sta <= s1:
            return z0 + (z1 - z0) * (sta - s0) / (s1 - s0)
    return pvs[-1][1]


# ─── Horizontal geometry ──────────────────────────────────────────────────────

def _parse_coord_geom(alignment_elem, ns):
    """
    Parse <CoordGeom> and return a list of geometry segment dicts.
    Supported types: Line, Curve  (Spiral elements are skipped).
    """
    segments = []
    sta_acc = 0.0

    coord_geom = alignment_elem.find(_t(ns, 'CoordGeom'))
    if coord_geom is None:
        return segments

    for child in coord_geom:
        tag = _strip_ns(child.tag)

        if tag == 'Line':
            length  = float(child.get('length', 0) or 0)
            dir_deg = float(child.get('dir',    0) or 0)

            start_e = child.find(_t(ns, 'Start'))
            n0 = e0 = None
            if start_e is not None and start_e.text:
                coords = _parse_pair(start_e.text)
                n0, e0 = coords[0], coords[1]  # LandXML: N E order

            segments.append({
                'type': 'line',
                'sta_start': sta_acc,
                'sta_end':   sta_acc + length,
                'length':    length,
                'n0': n0, 'e0': e0,
                'dir_deg': dir_deg,
            })
            sta_acc += length

        elif tag == 'Curve':
            length = float(child.get('length', 0) or 0)
            radius = float(child.get('radius', 0) or 0)
            rot    = (child.get('rot') or 'ccw').lower()

            start_e  = child.find(_t(ns, 'Start'))
            center_e = child.find(_t(ns, 'Center'))
            n0 = e0 = nc = ec = None

            if start_e is not None and start_e.text:
                coords = _parse_pair(start_e.text)
                n0, e0 = coords[0], coords[1]
            if center_e is not None and center_e.text:
                coords = _parse_pair(center_e.text)
                nc, ec = coords[0], coords[1]

            segments.append({
                'type': 'curve',
                'sta_start': sta_acc,
                'sta_end':   sta_acc + length,
                'length':    length,
                'n0': n0, 'e0': e0,
                'nc': nc, 'ec': ec,
                'radius': radius,
                'rot': rot,
            })
            sta_acc += length

        # Spiral/IrregularLine/other: skip

    return segments


def _en_at_station(segments, sta_local):
    """
    Compute (E, N) at local station offset (from alignment staStart).
    Returns (E, N) or (None, None) if geometry is missing.
    """
    if not segments:
        return None, None

    for seg in segments:
        if sta_local <= seg['sta_end'] or seg is segments[-1]:
            s = max(0.0, min(sta_local - seg['sta_start'], seg['length']))

            if seg['type'] == 'line':
                n0, e0 = seg['n0'], seg['e0']
                if n0 is None or e0 is None:
                    return None, None
                dir_rad = math.radians(seg['dir_deg'])
                e = e0 + s * math.sin(dir_rad)
                n = n0 + s * math.cos(dir_rad)
                return e, n

            elif seg['type'] == 'curve':
                n0, e0, nc, ec = seg['n0'], seg['e0'], seg['nc'], seg['ec']
                radius = seg['radius']
                if any(v is None for v in (n0, e0, nc, ec)) or radius == 0:
                    return None, None
                # Standard math angle (CCW from East axis)
                ang_start = math.atan2(n0 - nc, e0 - ec)
                d_ang = s / radius
                ang = ang_start + (d_ang if seg['rot'] == 'ccw' else -d_ang)
                e = ec + radius * math.cos(ang)
                n = nc + radius * math.sin(ang)
                return e, n

    return None, None


# ─── CgPoints fallback ────────────────────────────────────────────────────────

def _try_cgpoints(root, ns):
    """Extract DTA from <CgPoints> elements. Returns DataFrame or None."""
    cg_elem = root.find(_t(ns, 'CgPoints'))
    if cg_elem is None:
        for survey in root.findall(_t(ns, 'Survey')):
            cg_elem = survey.find(_t(ns, 'CgPoints'))
            if cg_elem is not None:
                break

    if cg_elem is None:
        return None

    rows = []
    for i, pt in enumerate(cg_elem.findall(_t(ns, 'CgPoint'))):
        if not pt.text:
            continue
        coords = [float(v) for v in pt.text.strip().split()]
        if len(coords) >= 3:
            n, e, z = coords[0], coords[1], coords[2]
            rows.append({
                'POINT NO.':    i + 1,
                'CHAINAGE':     float(i),
                'EASTING (M.)':  e,
                'NORTHING (M.)': n,
                'ELEVATION (M.)': z,
            })

    return pd.DataFrame(rows) if rows else None


# ─── Public API ───────────────────────────────────────────────────────────────

def parse_landxml_to_dta(content_bytes: bytes, sample_interval: float = 1.0) -> pd.DataFrame:
    """
    Parse a LandXML file and return a tunnel axis DataFrame compatible
    with compute_wriggle_survey().

    Parameters
    ----------
    content_bytes   : bytes  — raw LandXML file content
    sample_interval : float  — chainage sampling step in metres (default 1.0 m)

    Returns
    -------
    pd.DataFrame with columns:
        POINT NO. | CHAINAGE | EASTING (M.) | NORTHING (M.) | ELEVATION (M.)

    Raises
    ------
    ValueError if no usable geometry is found.
    """
    try:
        root = ET.fromstring(content_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"XML ayrıştırma hatası: {exc}") from exc

    ns = _detect_ns(root)

    # ── Collect all <Alignment> elements ─────────────────────────────────────
    alignment_elems = []
    for alns_container in root.findall(_t(ns, 'Alignments')):
        alignment_elems.extend(alns_container.findall(_t(ns, 'Alignment')))
    alignment_elems.extend(root.findall(_t(ns, 'Alignment')))

    if alignment_elems:
        # Use the first alignment (typical for a tunnel project)
        alignment = alignment_elems[0]
        name    = alignment.get('name', 'Alignment 1')
        length  = float(alignment.get('length', 0) or 0)
        sta_start = float(alignment.get('staStart', 0) or 0)

        segments = _parse_coord_geom(alignment, ns)
        pvs      = _parse_profile(alignment, ns)

        if segments and length > 0:
            sta_locals = np.arange(0.0, length + sample_interval * 0.5, sample_interval)
            # Make sure last point is exactly at alignment end
            if sta_locals[-1] > length:
                sta_locals = np.append(sta_locals[:-1], length)

            rows = []
            for i, sta_local in enumerate(sta_locals):
                sta_abs = sta_start + sta_local
                e, n = _en_at_station(segments, sta_local)
                if e is None or n is None:
                    continue
                z = _elev_at_station(pvs, sta_abs) if pvs else 0.0
                rows.append({
                    'POINT NO.':     i + 1,
                    'CHAINAGE':      round(float(sta_abs),    4),
                    'EASTING (M.)':   round(float(e),          4),
                    'NORTHING (M.)':  round(float(n),          4),
                    'ELEVATION (M.)': round(float(z),          4),
                })

            if rows:
                return pd.DataFrame(rows)

    # ── Fallback: CgPoints ───────────────────────────────────────────────────
    df = _try_cgpoints(root, ns)
    if df is not None and len(df) >= 2:
        return df

    raise ValueError(
        "LandXML dosyasından güzergah verisi çıkarılamadı.\n"
        "Desteklenen elementler:\n"
        "  • <Alignments> → <Alignment> → <CoordGeom> (Line, Curve) + <Profile>\n"
        "  • <CgPoints> → <CgPoint> (N E Z)"
    )


def list_alignments(content_bytes: bytes) -> list[str]:
    """Return names of all alignments found in the LandXML file."""
    try:
        root = ET.fromstring(content_bytes)
    except ET.ParseError:
        return []

    ns = _detect_ns(root)
    names = []
    for alns in root.findall(_t(ns, 'Alignments')):
        for a in alns.findall(_t(ns, 'Alignment')):
            names.append(a.get('name', f'Alignment {len(names)+1}'))
    for a in root.findall(_t(ns, 'Alignment')):
        names.append(a.get('name', f'Alignment {len(names)+1}'))
    return names
