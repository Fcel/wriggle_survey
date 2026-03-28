from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import pandas as pd
import math
import io
import uuid

from wriggle_core import compute_wriggle_survey

app = FastAPI(title="Wriggle Survey API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for generated Excel files (keyed by download_id)
export_store: dict[str, bytes] = {}


def safe_val(v):
    """Convert numpy/nan values to JSON-safe Python types."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return str(v)


@app.post("/api/compute")
async def compute(
    file: UploadFile = File(...),
    dia_design: float = Form(3.396),
    direction: str = Form("DIRECT"),
):
    if direction not in ("DIRECT", "REVERSE"):
        raise HTTPException(status_code=400, detail="direction must be DIRECT or REVERSE")

    contents = await file.read()
    buf = io.BytesIO(contents)

    try:
        df_wrs = pd.read_excel(buf, sheet_name="Import Wriggle Data")
        buf.seek(0)
        df_dta = pd.read_excel(buf, sheet_name="Import Tunnel Axis (DTA)")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Excel okuma hatası: {e}")

    try:
        df_result, df_backup = compute_wriggle_survey(df_wrs, df_dta, dia_design, direction)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hesaplama hatası: {e}")

    # ── Generate Excel output ───────────────────────────────────────────────
    download_id = str(uuid.uuid4())
    out_buf = io.BytesIO()
    with pd.ExcelWriter(out_buf, engine="openpyxl") as writer:
        df_result.to_excel(writer, sheet_name="WRIGGLE RESULT", index=False)
        df_backup.to_excel(writer, sheet_name="WRIGGLE BACKUP", index=False)
    export_store[download_id] = out_buf.getvalue()

    # ── Build table results ─────────────────────────────────────────────────
    results = [
        {k: safe_val(v) for k, v in row.items()}
        for row in df_result.to_dict(orient="records")
    ]

    # ── Build chart data (per-ring cross-section) ───────────────────────────
    chart_data = []
    for _, row in df_backup.iterrows():
        num_pnt = int(row.get("NUM.PNT", 0))
        xc = safe_val(row.get("X_C"))
        yc_raw = safe_val(row.get("Y_C"))
        yc = (yc_raw - 100) if yc_raw is not None else None
        avg_r = safe_val(row.get("AVG.R"))
        design_r = safe_val(row.get("DESING.CL-R"))

        points = []
        for t in range(1, num_pnt + 1):
            xv = safe_val(row.get(f"X_P{t}"))
            yv_raw = safe_val(row.get(f"Y_P{t}"))
            yv = (yv_raw - 100) if yv_raw is not None else None
            rdbc = safe_val(row.get(f"RDBC_P{t}"))
            ang  = safe_val(row.get(f"ANG_P{t}"))
            r    = safe_val(row.get(f"R_P{t}"))
            if xv is not None and yv is not None:
                # Relative to center for cross-section plot
                points.append({
                    "x": round(xv - xc, 6) if xc is not None else xv,
                    "y": round(yv - yc, 6) if yc is not None else yv,
                    "rdbc": rdbc,
                    "ang": ang,
                    "r": r,
                    "label": f"P{t}",
                })

        chart_data.append({
            "ring_no": str(row.get("RING NO.", "")),
            "center_x": xc,
            "center_y": yc,
            "avg_radius": avg_r,
            "design_radius": design_r,
            "hor_deviation": safe_val(row.get("DH")),
            "ver_deviation": safe_val(row.get("DV")),
            "chainage": safe_val(row.get("CH")),
            "points": points,
        })

    return {
        "results": results,
        "chart_data": chart_data,
        "download_id": download_id,
    }


@app.get("/api/download/{download_id}")
async def download(download_id: str):
    data = export_store.get(download_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı veya süresi doldu.")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Export_Wriggle_Survey.xlsx"},
    )
