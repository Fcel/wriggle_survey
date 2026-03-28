# Wriggle Survey Core Computation
# Refactored from: Wriggle_Survey_(Best-Fit_Circle_3D)_Rev06.py
# Original Author: Suben Mukem (Survey Engineer)

import math
import numpy as np
import pandas as pd


# ─── Utility Functions ───────────────────────────────────────────────────────

def DegtoRad(d):
    return d * math.pi / 180.0

def RadtoDeg(d):
    return d * 180 / math.pi

def DirecAziDist(EStart, NStart, EEnd, NEnd):
    dE = EEnd - EStart
    dN = NEnd - NStart
    Dist = math.sqrt(dE**2 + dN**2)
    ang = math.atan2(dE, dN)
    Azi = RadtoDeg(ang) if ang >= 0 else RadtoDeg(ang) + 360
    return Dist, Azi

def CoorYXtoNE(ECL, NCL, AZCL, Y, X):
    Ei = ECL + Y * math.sin(DegtoRad(AZCL)) + X * math.sin(DegtoRad(90 + AZCL))
    Ni = NCL + Y * math.cos(DegtoRad(AZCL)) + X * math.cos(DegtoRad(90 + AZCL))
    return Ei, Ni

def CoorNEtoYXL(ECL, NCL, AZCL, EA, NA):
    dE = EA - ECL
    dN = NA - NCL
    Liner = math.sqrt(dE**2 + dN**2)
    ang = math.atan2(dE, dN)
    AzLinear = RadtoDeg(ang) if ang >= 0 else RadtoDeg(ang) + 360
    Delta = AzLinear - AZCL
    Y = Liner * math.cos(DegtoRad(Delta))
    X = Liner * math.sin(DegtoRad(Delta))
    return Y, X

def Pitching(ChStart, ZStart, ChEnd, ZEnd):
    return (ZEnd - ZStart) / (ChEnd - ChStart)

def DeviateVt(ChD, ZD, pitch, ChA, ZA):
    ZFind = ZD + pitch * (ChA - ChD)
    return ZA - ZFind


# ─── Main Computation ─────────────────────────────────────────────────────────

def compute_wriggle_survey(df_WRS_DATA, df_DTA_DATA, DiaDesign=3.396, Direction="DIRECT"):
    """
    Compute Wriggle Survey (Best-Fit Circle 3D).

    Parameters
    ----------
    df_WRS_DATA : pd.DataFrame  — wriggle survey measurement points
    df_DTA_DATA : pd.DataFrame  — tunnel axis design data
    DiaDesign   : float         — design tunnel diameter (m)
    Direction   : str           — "DIRECT" or "REVERSE"

    Returns
    -------
    df_WSR_RESULT : pd.DataFrame  — summary results per ring
    df_WSR_BACKUP : pd.DataFrame  — detailed backup data per ring
    """

    # Reset indices to guarantee 0-based integer indexing
    df_WRS_DATA = df_WRS_DATA.reset_index(drop=True)
    df_DTA_DATA = df_DTA_DATA.reset_index(drop=True)

    Excavate_Direc = 1 if Direction == "DIRECT" else -1

    totalWRS = int(df_WRS_DATA["NUM. POINTS"].count()) - 1
    totalDTA = int(df_DTA_DATA["CHAINAGE"].count()) - 1

    ColumnNames_WSR_RESULT = [
        "RING NO.", "TUN.CL-EASTING (M.)", "TUN.CL-NORTHING (M.)",
        "TUN.CL-ELEVATION (M.)", "CHAINAGE (M.)",
        "HOR.DEVIATION (M.)", "VER.DEVIATION (M.)",
        "AVG.RADIUS (M.)", "AVG.DIAMETER (M.)"
    ]
    result_rows = []

    ColumnNames_WSR_BACKUP = [
        "INDEX", "RING NO.", "TUN.CL-E", "TUN.CL-N", "TUN.CL-Z",
        "CH", "DH", "DV", "AVG.R", "AVG.DIA",
        *[f"{c}_P{t}" for t in range(1, 17) for c in ("E", "N", "Z")],
        "DESING.CL-E", "DESING.CL-N", "DESING.CL-Z", "DESING.CL-R", "DESING.CL-DIA",
        "X_C", "Y_C",
        *[f"{c}_P{t}" for t in range(1, 17) for c in ("X", "Y")],
        *[f"R_P{t}" for t in range(1, 17)],
        *[f"RDBC_P{t}" for t in range(1, 17)],
        *[f"ANG_P{t}" for t in range(1, 17)],
        "E_P", "N_P", "E_Q", "N_Q", "OFFSET", "NUM.PNT", "MIN_DIST_DTA"
    ]
    backup_rows = []

    u = 0  # current row pointer in df_WRS_DATA
    w = 0  # ring index

    for i in range(totalWRS + 1):
        numPnt = int(df_WRS_DATA["NUM. POINTS"][u])

        # Read ring measurement points
        WSR = []
        for k in range(numPnt):
            row = df_WRS_DATA.iloc[u + k]
            WSR.append([
                row["RING NO."], row["POINT NO."],
                row["EASTING (M.)"], row["NORTHING (M.)"],
                row["ELEVATION (M.)"], row["OFFSET (M.)"]
            ])
        WSR = np.array(WSR, dtype=float)
        Rngi = WSR[:, 0]; Pi = WSR[:, 1]
        Ei = WSR[:, 2]; Ni = WSR[:, 3]; Zi = WSR[:, 4]; OSi = WSR[:, 5]

        RngName = 'R' + str(int(np.average(Rngi)))
        avgOSi = float(np.average(OSi))

        # Linear regression (least square) through horizontal plane
        m, b = np.polyfit(Ei, Ni, 1)
        EMin = float(np.amin(Ei)) * 0.999999
        EMax = float(np.amax(Ei)) * 1.0000005
        EP, NP = EMin, m * EMin + b
        EQ, NQ = EMax, m * EMax + b

        # Local coordinates along PQ line
        DistPQ, AzPQ = DirecAziDist(EP, NP, EQ, NQ)
        Local_XYd = []
        for k in range(numPnt):
            Xi_k, di_k = CoorNEtoYXL(EP, NP, AzPQ, float(Ei[k]), float(Ni[k]))
            Yi_k = float(Zi[k]) + 100   # shift so that elevation < 0 is handled
            Local_XYd.append([Xi_k, Yi_k, di_k])
        Local_XYd = np.array(Local_XYd)
        Xi = Local_XYd[:, 0]; Yi = Local_XYd[:, 1]; di = Local_XYd[:, 2]

        # Best-fit circle (2D) — Kasa Method (least squares)
        sumX = sumY = sumX2 = sumY2 = sumXY = 0
        sumXY2 = sumX3 = sumYX2 = sumY3 = 0
        for k in range(numPnt):
            x, y = Xi[k], Yi[k]
            sumX  += x;    sumY  += y
            sumX2 += x**2; sumY2 += y**2; sumXY += x * y
            sumXY2 += x * y**2; sumX3 += x**3
            sumYX2 += y * x**2; sumY3 += y**3

        KM1 = 2 * (sumX**2 - numPnt * sumX2)
        KM2 = 2 * (sumX * sumY - numPnt * sumXY)
        KM3 = 2 * (sumY**2 - numPnt * sumY2)
        KM4 = sumX2 * sumX - numPnt * sumX3 + sumX * sumY2 - numPnt * sumXY2
        KM5 = sumX2 * sumY - numPnt * sumY3 + sumY * sumY2 - numPnt * sumYX2

        denom = KM1 * KM3 - KM2**2
        Xc = (KM4 * KM3 - KM5 * KM2) / denom
        Yc = (KM1 * KM5 - KM2 * KM4) / denom
        Radius = float(np.sqrt(
            Xc**2 + Yc**2 +
            (sumX2 - 2 * Xc * sumX + sumY2 - 2 * Yc * sumY) / numPnt
        ))

        # Per-point radius, deviation, angle
        RDA = []
        for k in range(numPnt):
            Ri_k, ANGi_k = DirecAziDist(Xc, Yc, Xi[k], Yi[k])
            RDBCi_k = Ri_k - Radius
            RDA.append([Ri_k, RDBCi_k, ANGi_k])
        RDA = np.array(RDA)
        Ri = RDA[:, 0]; RDBCi = RDA[:, 1]; ANGi = RDA[:, 2]

        # Transform circle center back to grid coordinates
        Ec, Nc = CoorYXtoNE(EP, NP, AzPQ, Xc, 0)
        Zc = float(Yc) - 100

        # Extended (offset-corrected) point coordinates
        extWSR = []
        for k in range(numPnt):
            extRi_k = float(Ri[k]) + float(OSi[k])
            extXi_k = Xc + extRi_k * np.sin(DegtoRad(ANGi[k]))
            extYi_k = Yc + extRi_k * np.cos(DegtoRad(ANGi[k]))
            extEi_k, extNi_k = CoorYXtoNE(Ec, Nc, AzPQ, extXi_k - Xc, float(di[k]))
            extZi_k = extYi_k - 100
            extWSR.append([extRi_k, extXi_k, extYi_k, extEi_k, extNi_k, extZi_k])
        extWSR = np.array(extWSR)
        extRi  = extWSR[:, 0]; extXi = extWSR[:, 1]; extYi = extWSR[:, 2]
        extEi  = extWSR[:, 3]; extNi = extWSR[:, 4]; extZi = extWSR[:, 5]

        # Find nearest tunnel axis point and compute chainage + deviations
        PntDTA = df_DTA_DATA["POINT NO."]
        ChDTA  = df_DTA_DATA["CHAINAGE"]
        EDTA   = df_DTA_DATA["EASTING (M.)"]
        NDTA   = df_DTA_DATA["NORTHING (M.)"]
        ZDTA   = df_DTA_DATA["ELEVATION (M.)"]

        Linear = [
            float(np.sqrt((EDTA[d] - Ec)**2 + (NDTA[d] - Nc)**2))
            for d in range(totalDTA + 1)
        ]
        minDist  = min(Linear)
        minIndex = Linear.index(minDist)

        # Guard against edge indices
        minIndex = max(1, min(minIndex, totalDTA - 1))

        ChB = ChDTA[minIndex - 1]; EB = EDTA[minIndex - 1]; NB = NDTA[minIndex - 1]; ZB = ZDTA[minIndex - 1]
        ChM = ChDTA[minIndex];     EM = EDTA[minIndex];     NM = NDTA[minIndex];     ZM = ZDTA[minIndex]
        ChH = ChDTA[minIndex + 1]; EH = EDTA[minIndex + 1]; NH = NDTA[minIndex + 1]; ZH = ZDTA[minIndex + 1]

        DistAC, _ = DirecAziDist(EB, NB, Ec, Nc)
        DistHC, _ = DirecAziDist(EH, NH, Ec, Nc)

        DistBM, AzBM = DirecAziDist(EB, NB, EM, NM)
        PitchBM = Pitching(ChB, ZB, ChM, ZM)

        DistMH, AzMH = DirecAziDist(EM, NM, EH, NH)
        PitchMH = Pitching(ChM, ZM, ChH, ZH)

        if DistAC < DistHC:
            dCh, OsC = CoorNEtoYXL(EM, NM, AzBM, Ec, Nc)
            ChC = dCh + ChM
            VtC = DeviateVt(ChM, ZM, PitchBM, ChC, Zc)
            Ed, Nd = CoorYXtoNE(EM, NM, AzBM, ChC - ChM, 0)
            ZD = ZM + PitchBM * (ChC - ChM)
        else:
            dCh, OsC = CoorNEtoYXL(EM, NM, AzMH, Ec, Nc)
            ChC = dCh + ChM
            VtC = DeviateVt(ChM, ZM, PitchMH, ChC, Zc)
            Ed, Nd = CoorYXtoNE(EM, NM, AzMH, ChC - ChM, 0)
            ZD = ZM + PitchMH * (ChC - ChM)

        AvgR   = Radius + avgOSi
        AvgDia = AvgR * 2

        # ── Result row ──────────────────────────────────────────────────────
        result_rows.append([
            RngName, Ec, Nc, Zc, ChC,
            OsC * Excavate_Direc, VtC, AvgR, AvgDia
        ])

        # ── Backup row ───────────────────────────────────────────────────────
        backup = [w, RngName, Ec, Nc, Zc, ChC, OsC * Excavate_Direc, VtC, AvgR, AvgDia]

        for t in range(16):
            if t < numPnt:
                backup += [float(extEi[t]), float(extNi[t]), float(extZi[t])]
            else:
                backup += [None, None, None]

        backup += [Ed, Nd, ZD, DiaDesign / 2, DiaDesign, Xc, Yc]

        for t in range(16):
            if t < numPnt:
                backup += [float(extXi[t]), float(extYi[t])]
            else:
                backup += [None, None]

        for t in range(16):
            backup.append(float(Ri[t] + OSi[t]) if t < numPnt else None)
        for t in range(16):
            backup.append(float(RDBCi[t]) if t < numPnt else None)
        for t in range(16):
            backup.append(float(ANGi[t]) if t < numPnt else None)

        backup += [EP, NP, EQ, NQ, avgOSi, numPnt, minDist]
        backup_rows.append(backup)

        w += 1
        u += numPnt

    df_WSR_RESULT = pd.DataFrame(result_rows, columns=ColumnNames_WSR_RESULT)
    df_WSR_BACKUP = pd.DataFrame(backup_rows, columns=ColumnNames_WSR_BACKUP)
    return df_WSR_RESULT, df_WSR_BACKUP
