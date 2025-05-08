#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
simulate_soc(df_pred, t_night, t_even)
  → DataFrame із batt_kw, soc_pct, grid_import_kw
"""

BAT_CAP = 5.0       # kWh
ETA_C   = 0.95
ETA_D   = 0.90
SOC_MIN, SOC_MAX = 10, 95   # %

import pandas as pd

def simulate_soc(df: pd.DataFrame, t_night: int, t_even: int) -> pd.DataFrame:
    soc = SOC_MAX
    batt_kw, soc_list, grid_imp = [], [], []

    for _, r in df.iterrows():
        h, pv, load = r["timestamp"].hour, r["pv_kw"], r["load_kw"]

        if h < t_night:                      # ніч → розряд
            delta = -load / ETA_D
            grid  = 0.0
        elif h < t_even:                     # день → PV
            diff = pv - load
            if diff >= 0:
                delta = diff * ETA_C
                grid  = 0.0
            else:
                delta = 0.0
                grid  = -diff
        else:                                # вечір → заряд від мережі
            need_pct = SOC_MAX - soc
            need_kwh = need_pct * BAT_CAP / 100
            delta    = need_kwh
            grid     = load + need_kwh / ETA_C

        soc += delta * 100 / BAT_CAP
        soc  = min(max(soc, SOC_MIN), SOC_MAX)

        batt_kw.append(delta)
        soc_list.append(soc)
        grid_imp.append(grid)

    out = df.copy()
    out["batt_kw"]        = batt_kw
    out["soc_pct"]        = soc_list
    out["grid_import_kw"] = grid_imp
    return out
