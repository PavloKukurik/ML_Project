#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
optimize_schedule(df_pred)
  → (str t_night, str t_evening, final_soc, total_import)
"""

from typing import Tuple
import pandas as pd
from .battery_simulator import simulate_soc

def _auto_evening(df: pd.DataFrame) -> int:
    """Година, починаючи з якої PV ≈ 0 кВт → кінець дня."""
    active = df[df["pv_kw"] > 0.05]["timestamp"].dt.hour
    return int(active.max()) + 1 if not active.empty else 20

def optimize_schedule(df_pred: pd.DataFrame) -> Tuple[str,str,float,float]:
    t_even = _auto_evening(df_pred)

    best = None
    for h in range(6):                    # 00…05
        sim = simulate_soc(df_pred, h, t_even)
        soc_end = sim["soc_pct"].iloc[-1]
        imp     = sim["grid_import_kw"].sum()
        if best is None or imp < best[3]:
            best = (h, t_even, soc_end, imp)

    h_opt, e_opt, soc, imp = best
    return f"{h_opt:02d}:00", f"{e_opt:02d}:00", soc, imp
