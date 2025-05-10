
from typing import Tuple
import numpy as np, pandas as pd
from .battery_simulator import simulate_soc

GAMMA  = 2.0
LAMBDA = 0.3      # штраф за пізнє нічне

def _evening(df_w: pd.DataFrame) -> float:
    """Остання година з SWR>20 Вт/м² → +1 год, clamp 17…23."""
    swr  = df_w["shortwave_radiation"].values
    hour = (pd.to_datetime(df_w["timestamp"], utc=True)
              .dt.tz_convert("Europe/Kyiv")
              .dt.hour.values)

    idx = np.where(swr > 20)[0]
    if len(idx) == 0:
        return 20.0
    te   = hour[idx[-1]] + 1
    return float(min(max(te, 17), 23))

def optimize_schedule(df_pred: pd.DataFrame,
                      df_weather: pd.DataFrame) -> Tuple[str,str,float,float]:
    t_even = _evening(df_weather)
    best = None
    for q in range(0, 25):     
        t_n = q * 0.25
        sim = simulate_soc(df_pred, t_n, t_even)
        imp   = sim["grid_import_kw"].sum()
        waste = sim["wasted_pv_kw"].sum()
        cost  = imp + GAMMA*waste + LAMBDA*t_n
        if best is None or cost < best[-1]:
            best = (t_n, t_even,
                    float(sim["soc_pct"].iloc[-1]), imp, cost)

    tn, te, soc_end, imp, _ = best
    tn_str = f"{int(tn):02d}:{int((tn%1)*60):02d}"
    te_str = f"{int(te):02d}:00"
    return tn_str, te_str, soc_end, imp
