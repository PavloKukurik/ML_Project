#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
simulate_soc(df_pred, t_night, t_even)
→ DataFrame з batt_kw, soc_pct, grid_import_kw, wasted_pv_kw
"""

BAT_CAP   = 5.0   # kWh
ETA_C, ETA_D = 0.95, 0.90
SOC_MIN, SOC_MAX = 10, 95          # %

import pandas as pd, numpy as np

def _draw_from_battery(soc_pct, load_kwh):
    """повертає (delta_batt_kWh, grid_kWh, new_soc_pct)"""
    energy_avail = (soc_pct - SOC_MIN) * BAT_CAP / 100
    discharge = min(load_kwh / ETA_D, energy_avail)     # kWh, що реально візьмемо
    batt_kwh  = -discharge
    grid_kwh  = load_kwh - discharge * ETA_D
    soc_pct  -= discharge * 100 / BAT_CAP
    return batt_kwh, grid_kwh, soc_pct

def simulate_soc(df: pd.DataFrame,
                 t_night: float,
                 t_even:  float) -> pd.DataFrame:
    soc = SOC_MAX
    batt_kw = []; soc_pct = []; grid_imp = []; wasted = []

    for _, r in df.iterrows():
        h     = r["timestamp"].hour + r["timestamp"].minute/60
        pv_kW = r["pv_kw"]
        load  = r["load_kw"]

        # —‑‑‑‑ нічний розряд ‑‑‑‑‑
        if h < t_night:
            batt_kwh, grid_kwh, soc = _draw_from_battery(soc, load)
            waste = 0.0

        # —‑‑‑‑ день (PV) ‑‑‑‑‑
        elif h < t_even:
            diff = pv_kW - load                    # “надлишок” + / дефіцит –
            if diff >= 0:                          # маємо лишню PV
                cap_left = (SOC_MAX - soc) * BAT_CAP / 100
                store    = min(diff * ETA_C, cap_left)
                waste    = diff * ETA_C - store
                batt_kwh =  store
                grid_kwh = 0.0
                soc     += store * 100 / BAT_CAP
            else:                                  # дефіцит
                batt_kwh, grid_kwh, soc = _draw_from_battery(soc, -diff)
                waste = 0.0

        # —‑‑‑‑ вечірній заряд від мережі ‑‑‑‑‑
        else:
            need_kWh = (SOC_MAX - soc) * BAT_CAP / 100
            batt_kwh =  need_kWh
            grid_kwh =  load + need_kWh / ETA_C
            soc      =  SOC_MAX
            waste    = 0.0

        batt_kw.append(batt_kwh)
        grid_imp.append(grid_kwh)
        soc_pct.append(soc)
        wasted.append(waste)

    out = df.copy()
    out["batt_kw"]        = batt_kw
    out["soc_pct"]        = soc_pct
    out["grid_import_kw"] = grid_imp
    out["wasted_pv_kw"]   = wasted
    return out
