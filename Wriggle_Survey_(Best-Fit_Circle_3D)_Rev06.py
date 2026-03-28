# Topic; Wriggle Survey (Best-Fit Circle 3D)
# Created By; Suben Mukem (SBM) as Survey Engineer.
# Updated; 10/04/2024

# Import Module
import math # for General Survey Function
import numpy as np
import pandas as pd
import time

t0 = time.time() # Start time

#---------------------------- All Function ----------------------------#
## General Survey ##
# Convert Degrees to Radians
def DegtoRad(d):
    ang = d * math.pi / 180.0
    return ang

# Convert Radians to Degrees
def RadtoDeg(d):
    ang = d * 180 / math.pi
    return ang

# Compute Distance and Azimuth from 2 Points
def DirecAziDist(EStart, NStart, EEnd, NEnd):
    dE = EEnd - EStart
    dN = NEnd - NStart
    Dist = math.sqrt(dE**2 + dN**2)

    if dN != 0:
        ang = math.atan2(dE, dN)
    else:
        Azi = False

    if ang >= 0:
        Azi = RadtoDeg(ang)
    else:
        Azi = RadtoDeg(ang) + 360
    return Dist, Azi

# Compute Grid Coordinate (E, N) by Local Coordinate (Y, X), Coordinate of Center and Azimuth.
def CoorYXtoNE(ECL, NCL, AZCL, Y, X):
    Ei = ECL + Y * math.sin(DegtoRad(AZCL)) + X * math.sin(DegtoRad(90 + AZCL))
    Ni = NCL + Y * math.cos(DegtoRad(AZCL)) + X * math.cos(DegtoRad(90 + AZCL))
    return Ei, Ni

# Compute Local Coordinate (Y, X, L) by Grid Coordinate (E, N) and Azimuth.
def CoorNEtoYXL(ECL, NCL, AZCL, EA, NA):
    dE = EA - ECL
    dN = NA - NCL
    Liner = math.sqrt(dE**2 + dN**2)

    if dN != 0:
        ang = math.atan2(dE, dN)
    else:
        AzLinear = False

    if ang >= 0:
        AzLinear = RadtoDeg(ang)
    else:
        AzLinear = RadtoDeg(ang) + 360 

    Delta = AzLinear - AZCL
    Y = Liner * math.cos(DegtoRad(Delta))
    X = Liner * math.sin(DegtoRad(Delta))
    return Y, X

## Wriggle Survey ##
# Compute pitching
def Pitching(ChStart, ZStrat, ChEnd, ZEnd):
    Pitch = (ZEnd - ZStrat) / (ChEnd - ChStart)
    return Pitch

# Compute Vertical Deviation
def DeviateVt(ChD, ZD, Pitching, ChA, ZA):
    ZFind = ZD + Pitching * (ChA - ChD)
    DeviateVt = ZA - ZFind
    return DeviateVt
#------------------------ End All Function ------------------------#

#------------------- Main Wriggle Survey Computation ------------------#
# Path files
Import_data_path = "Import Wriggle Survey&Tunnel Axis Data.xlsx"
Export_data_path = "Export Wriggle Survey.xlsx"

# Tunnel Diameter Design (m.)
DiaDesign = 3.396

# Excavation Direction : Select : DIRECT / REVERSE
Direction = "DIRECT"

if Direction == "DIRECT":
    Excavate_Direc = 1
elif Direction == "REVERSE":
    Excavate_Direc = -1
else:
    Excavate_Direc = False

# Import data excel file to Data frame 
df_WRS_DATA = pd.read_excel(Import_data_path, "Import Wriggle Data")
df_DTA_DATA = pd.read_excel(Import_data_path, "Import Tunnel Axis (DTA)") # DTA : Data of Tunnel Axis

# Count data
totalWRS = df_WRS_DATA["NUM. POINTS"].count() - 1
totalDTA = df_DTA_DATA["CHAINAGE"].count() - 1

# When compute wriggle survey finish then record to Data Frame
ColumnNames_WSR_RESULT = ["RING NO.", "TUN.CL-EASTING (M.)", "TUN.CL-NORTHING (M.)", "TUN.CL-ELEVATION (M.)", "CHAINAGE (M.)",
                          "HOR.DEVIATION (M.)", "VER.DEVIATION (M.)", "AVG.RADIUS (M.)", "AVG.DIAMETER (M.)"]
df_WSR_RESULT = pd.DataFrame(columns= ColumnNames_WSR_RESULT)

ColumnNames_WSR_BACKUP = ["INDEX", "RING NO.", "TUN.CL-E", "TUN.CL-N", "TUN.CL-Z", "CH", "DH", "DV", "AVG.R", "AVG.DIA",
                          "E_P1", "N_P1", "Z_P1", "E_P2", "N_P2", "Z_P2", "E_P3", "N_P3", "Z_P3", "E_P4", "N_P4", "Z_P4",
                          "E_P5", "N_P5", "Z_P5", "E_P6", "N_P6", "Z_P6", "E_P7", "N_P7", "Z_P7", "E_P8", "N_P8", "Z_P8",
                          "E_P9", "N_P9", "Z_P9", "E_P10", "N_P10", "Z_P10", "E_P11", "N_P11", "Z_P11", "E_P12", "N_P12", "Z_P12",
                          "E_P13", "N_P13", "Z_P13", "E_P14", "N_P14", "Z_P14", "E_P15", "N_P15", "Z_P15", "E_P16", "N_P16", "Z_P16",
                          "DESING.CL-E", "DESING.CL-N", "DESING.CL-Z", "DESING.CL-R", "DESING.CL-DIA",
                          "X_C", "Y_C", "X_P1", "Y_P1", "X_P2", "Y_P2", "X_P3", "Y_P3", "X_P4", "Y_P4",
                          "X_P5", "Y_P5", "X_P6", "Y_P6", "X_P7", "Y_P7", "X_P8", "Y_P8",
                          "X_P9", "Y_P9", "X_P10", "Y_P10", "X_P11", "Y_P11", "X_P12", "Y_P12",
                          "X_P13", "Y_P13", "X_P14", "Y_P14", "X_P15", "Y_P15", "X_P16", "Y_P16",
                          "R_P1", "R_P2", "R_P3", "R_P4", "R_P5", "R_P6", "R_P7", "R_P8",
                          "R_P9", "R_P10", "R_P11", "R_P12", "R_P13", "R_P14", "R_P15", "R_P16",
                          "RDBC_P1", "RDBC_P2", "RDBC_P3", "RDBC_P4", "RDBC_P5", "RDBC_P6", "RDBC_P7", "RDBC_P8",
                          "RDBC_P9", "RDBC_P10", "RDBC_P11", "RDBC_P12", "RDBC_P13", "RDBC_P14", "RDBC_P15", "RDBC_P16",
                          "ANG_P1", "ANG_P2", "ANG_P3", "ANG_P4", "ANG_P5", "ANG_P6", "ANG_P7", "ANG_P8",
                          "ANG_P9", "ANG_P10", "ANG_P11", "ANG_P12", "ANG_P13", "ANG_P14", "ANG_P15", "ANG_P16",
                          "E_P", "N_P", "E_Q", "N_Q", "OFFSET", "NUM.PNT"]
df_WSR_BACKUP = pd.DataFrame(columns= ColumnNames_WSR_BACKUP)

## Compute Wriggle Survey ##
u = 0
w = 0
for i in range(totalWRS + 1):
    # Number of point
    numPnt = df_WRS_DATA["NUM. POINTS"][u]
    numPnt = numPnt.astype(int)
    WSR = []
    for k in range(numPnt):
        # Wriggle survey data
        Rngi = df_WRS_DATA["RING NO."][k + u]
        Pi = df_WRS_DATA["POINT NO."][k + u]
        Ei = df_WRS_DATA["EASTING (M.)"][k + u]
        Ni = df_WRS_DATA["NORTHING (M.)"][k + u]
        Zi = df_WRS_DATA["ELEVATION (M.)"][k + u]
        OSi = df_WRS_DATA["OFFSET (M.)"][k + u]
        WSR.append([Rngi, Pi, Ei, Ni, Zi, OSi])
    WSR = np.array(WSR) # Convert list to numpy array
    Rngi = WSR[:, 0]; Pi = WSR[:, 1]; Ei = WSR[:, 2]; Ni = WSR[:, 3]; Zi = WSR[:, 4]; OSi = WSR[:, 5]
    
    # Ring segment name
    RngName = 'R' + np.average(Rngi).astype(int).astype(str)

    # Average Prism Offset
    avgOSi= np.average(OSi)

    # Linear Regression by Least Square
    m, b = np.polyfit(Ei, Ni, 1)

    EMin = np.amin(Ei) * 0.999999
    EMax = np.amax(Ei) * 1.0000005

    # P and Q point on Linear Regression
    EP, NP = EMin, m * EMin + b
    EQ, NQ = EMax, m * EMax + b

    # Coordinates on PQ Line and Local coordinates Xi, Yi
    Local_XYd = []
    for k in range(numPnt):
        DistPQ, AzPQ = DirecAziDist(EP, NP, EQ, NQ)
        Xi, di = CoorNEtoYXL(EP, NP, AzPQ, Ei[k], Ni[k])
        Yi = Zi[k] + 100    # In case elevation < 0 m.
        Local_XYd.append([Xi, Yi, di])
    Local_XYd = np.array(Local_XYd) # Convert list to numpy array
    Xi = Local_XYd[:, 0]; Yi = Local_XYd[:, 1]; di = Local_XYd[:, 2]
    
    # Best-fit Circle (2D) least square by Kasa Method
    sumX = 0; sumY = 0; sumX2 = 0; sumY2 = 0; sumXY = 0; sumXY2 = 0; sumX3 = 0; sumYX2 = 0; sumY3 = 0
    for k in range(numPnt):
        sumX = sumX + Xi[k]
        sumY = sumY + Yi[k]
        sumX2 = sumX2 + Xi[k]**2
        sumY2 = sumY2 + Yi[k]**2
        sumXY = sumXY + Xi[k] * Yi[k]
        sumXY2 = sumXY2 + Xi[k] * Yi[k]**2
        sumX3 = sumX3 + Xi[k]**3
        sumYX2 = sumYX2 + Yi[k] * Xi[k]** 2
        sumY3 = sumY3 + Yi[k]**3

    KM1 = 2 * ((sumX**2) - numPnt * sumX2)
    KM2 = 2 * (sumX * sumY - numPnt * sumXY)
    KM3 = 2 * ((sumY**2) - numPnt * sumY2)
    KM4 = sumX2 * sumX - numPnt * sumX3 + sumX * sumY2 - numPnt * sumXY2
    KM5 = sumX2 * sumY - numPnt * sumY3 + sumY * sumY2 - numPnt * sumYX2
    
    # Best-fit Circle Result
    Xc = (KM4 * KM3 - KM5 * KM2) / (KM1 * KM3 - (KM2**2)) # Local coordinate X
    Yc = (KM1 * KM5 - KM2 * KM4) / (KM1 * KM3 - (KM2**2)) # Local coordinate Y
    Radius = np.sqrt((Xc**2) + (Yc**2) + (sumX2 - 2 * Xc * sumX + sumY2 - 2 * Yc * sumY) / numPnt) # Average Radius

    # Coordinates on PQ Line and Local coordinates Xi, Yi
    RDA = [] # Ri, RDBCi and ANGi
    for k in range(numPnt):
        Ri, ANGi = DirecAziDist(Xc, Yc, Xi[k], Yi[k]) # Radius of each point, Angle of each point
        RDBCi = Ri - Radius # Deviation Radius of each point
        RDA.append([Ri, RDBCi, ANGi])
    RDA = np.array(RDA) # Convert list to numpy array
    Ri = RDA[:, 0]; RDBCi = RDA[:, 1]; ANGi = RDA[:, 2]

    # Transform center coordinates Xc,Yc to Ec, Nc, Zc
    Ec, Nc = CoorYXtoNE(EP, NP, AzPQ, Xc, 0)
    Zc = Yc - 100

    # Compute wriggle survey extention data
    extWSR = []
    for k in range(numPnt):
        # Local coordinate Xi, Yi
        extRi = Ri[k] + OSi[k]
        extXi = Xc + extRi * np.sin(DegtoRad(ANGi[k]))
        extYi = Yc + extRi * np.cos(DegtoRad(ANGi[k]))
        # Grid coordinate Ei, Ni
        extEi, extNi = CoorYXtoNE(Ec, Nc, AzPQ, extXi - Xc, di[k])
        extZi = extYi - 100
        extWSR.append([extRi, extXi, extYi, extEi, extNi, extZi])
    extWSR = np.array(extWSR) # Convert list to numpy array
    extRi = extWSR[:, 0]; extXi = extWSR[:, 1]; extYi = extWSR[:, 2]; extEi = extWSR[:, 3]; extNi = extWSR[:, 4]; extZi = extWSR[:, 5]

    ## Compute Deviation of Tunnel Center and Chainage ##
    # DTA : Data of Tunnel Axis
    PntDTA = df_DTA_DATA["POINT NO."]
    ChDTA = df_DTA_DATA["CHAINAGE"]
    EDTA = df_DTA_DATA["EASTING (M.)"]
    NDTA = df_DTA_DATA["NORTHING (M.)"]
    ZDTA = df_DTA_DATA["ELEVATION (M.)"]

    Linear = []
    for d in range(totalDTA + 1):
        Li = np.sqrt((EDTA[d] - Ec)**2 + (NDTA[d] - Nc)**2)
        Linear.append(Li)
    
    # Find minimum linear from tunnel center to tunnel axis
    minLinear = np.amin(Linear)
    minIndex = Linear.index(minLinear)

    # Note : Point.B is back point, Point.M is middle point (nearly tunnel point), Point.H is ahead point. B------>M------>H
    # Point.B ; Point no., Chainage, Easting, Northing, Elevation
    PntB = PntDTA[minIndex - 1]
    ChB = ChDTA[minIndex - 1]
    EB = EDTA[minIndex - 1]
    NB = NDTA[minIndex - 1]
    ZB = ZDTA[minIndex - 1]

    # Point.M ; Point no., Chainage, Easting, Northing, Elevation
    PntM = PntDTA[minIndex]
    ChM = ChDTA[minIndex]
    EM = EDTA[minIndex]
    NM = NDTA[minIndex]
    ZM = ZDTA[minIndex]

    # Point.H ; Point no., Chainage, Easting, Northing, Elevation
    PntH = PntDTA[minIndex + 1]
    ChH = ChDTA[minIndex + 1]
    EH = EDTA[minIndex + 1]
    NH = NDTA[minIndex + 1]
    ZH = ZDTA[minIndex + 1]

    DistAC, AzAC = DirecAziDist(EB, NB, Ec, Nc)
    DistHC, AzHC = DirecAziDist(EH, NH, Ec, Nc)
    
    DistBM, AzBM = DirecAziDist(EB, NB, EM, NM)
    PitchBM = Pitching(ChB, ZB, ChM, ZM)

    DistMH, AzMH = DirecAziDist(EM, NM, EH, NH)
    PitchMH = Pitching(ChM, ZM, ChH, ZH)

    if DistAC < DistHC:
        dCh, OsC = CoorNEtoYXL(EM, NM, AzBM, Ec, Nc) # Diff chainage and Horizontal deviation of tunnel center
        ChC = dCh + ChM # Chainage of tunnel center
        VtC = DeviateVt(ChM, ZM, PitchBM, ChC, Zc) # Vertical deviation of tunnel center
        
        Ed, Nd = CoorYXtoNE(EM, NM, AzBM, ChC - ChM, 0) # Design Easting
        ZD = ZM + PitchBM * (ChC - ChM) # Design Elevation  
    else:
        dCh, OsC = CoorNEtoYXL(EM, NM, AzMH, Ec, Nc) # Diff chainage and Horizontal deviation of tunnel center
        ChC = dCh + ChM # Chainage of tunnel center
        VtC = DeviateVt(ChM, ZM, PitchMH, ChC, Zc) # Vertical deviation of tunnel center

        Ed, Nd = CoorYXtoNE(EM, NM, AzMH, ChC - ChM, 0) # Design Easting
        ZD = ZM + PitchMH * (ChC - ChM) # Design Elevation

    # Add wriggle survey data to data frame df_WSR_RESULT
    df_WSR_R = pd.DataFrame([[RngName, Ec, Nc, Zc, ChC, OsC * Excavate_Direc, VtC, Radius + avgOSi, (Radius + avgOSi) * 2]], columns=ColumnNames_WSR_RESULT)
    df_WSR_RESULT = df_WSR_RESULT._append(df_WSR_R, ignore_index=True)

    # Add wriggle survey data to data frame df_WSR_BACKUP
    WSR_BACKUP = [] # List of WSR BACKUP
    # INDEX
    WSR_BACKUP.append(w)
    # RING NO.
    WSR_BACKUP.append(RngName)
    # TUNNEL CENTER
    WSR_BACKUP.append(Ec)
    WSR_BACKUP.append(Nc)
    WSR_BACKUP.append(Zc)
    # CHAINAGE
    WSR_BACKUP.append(ChC)
    # DEVIATION
    WSR_BACKUP.append(OsC * Excavate_Direc)
    WSR_BACKUP.append(VtC)
    # AVERAGE
    WSR_BACKUP.append(Radius + avgOSi)
    WSR_BACKUP.append((Radius + avgOSi) * 2)
    # COORDINATE
    for t in range(16):
        if t < numPnt:
            WSR_BACKUP.append(extEi[t])
            WSR_BACKUP.append(extNi[t])
            WSR_BACKUP.append(extZi[t])
        else:
            WSR_BACKUP.append("")
            WSR_BACKUP.append("")
            WSR_BACKUP.append("")
    # DESIGN CENTER
    WSR_BACKUP.append(Ed)
    WSR_BACKUP.append(Nd)
    WSR_BACKUP.append(ZD)
    WSR_BACKUP.append(DiaDesign / 2)
    WSR_BACKUP.append(DiaDesign)
    # LOCAL COORDINATE
    WSR_BACKUP.append(Xc)
    WSR_BACKUP.append(Yc)
    for t in range(16):
        if t < numPnt:
            WSR_BACKUP.append(extXi[t])
            WSR_BACKUP.append(extYi[t])
        else:
            WSR_BACKUP.append("")
            WSR_BACKUP.append("")
    # RADIUS
    for t in range(16):
        if t < numPnt:
            WSR_BACKUP.append(Ri[t] + OSi[t])
        else:
            WSR_BACKUP.append("")
    # RDBC
    for t in range(16):
        if t < numPnt:
            WSR_BACKUP.append(RDBCi[t])
        else:
            WSR_BACKUP.append("")
    # ANGLE
    for t in range(16):
        if t < numPnt:
            WSR_BACKUP.append(ANGi[t])
        else:
            WSR_BACKUP.append("")
    # P
    WSR_BACKUP.append(EP)
    WSR_BACKUP.append(NP)
    # Q
    WSR_BACKUP.append(EQ)
    WSR_BACKUP.append(NQ)
    # OFFSET
    WSR_BACKUP.append(avgOSi)
    # NUM. POINT
    WSR_BACKUP.append(numPnt)
    df_WSR_B = pd.DataFrame([WSR_BACKUP], columns=ColumnNames_WSR_BACKUP)
    df_WSR_BACKUP = df_WSR_BACKUP._append(df_WSR_B, ignore_index=True)

    w = w + 1
    u = u + numPnt

# Export Wriggle Survey Result
with pd.ExcelWriter(Export_data_path) as writer:
    df_WSR_RESULT.to_excel(writer, sheet_name="WRIGGLE RESULT", index = False)
    df_WSR_BACKUP.to_excel(writer, sheet_name="WRIGGLE BACKUP", index = False)

t1 = time.time() # End time
print("Wriggle Survey was computed completely!, {:.3f}sec.".format(t1-t0))
#----------------- End Main Wriggle Survey Computation ----------------#