#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
schedule_optimizer.py
---------------------
Пошук optimal t_night вночі (00–05:00, крок 15 хв),
t_evening фіксуємо як закінчення дня або теж ітеруємо.
"""

from pathlib import Path
import argparse, sys
import pandas as pd
from datetime import timedelta

def load_predictions(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext in (".parquet", ".pq"):
        df = pd.read_parquet(path)
    else:
        try:
            df = pd.read_csv(path, parse_dates=["timestamp"])
        except:
            df = pd.read_parquet(path)
    df = df.rename(columns=lambda c: c.strip())
    if "pv_kw_pred" in df.columns:
        df = df.rename(columns={"pv_kw_pred":"pv_kw","load_kw_pred":"load_kw"})
    return df.sort_values("timestamp")[["timestamp","pv_kw","load_kw"]]

def simulate_soc(df, t_night, t_evening):
    # скопійований блок із battery_simulator
    from battery_simulator import BAT_CAP_KWH, ETA_CHARGE, ETA_DISCHARGE, SOC_MIN, SOC_MAX
    soc = SOC_MAX
    total_imp = 0
    for _, r in df.iterrows():
        h, pv, load = r.timestamp.hour, r.pv_kw, r.load_kw
        if h < t_night:
            p_batt = -load; imp = 0; soc += p_batt*ETA_DISCHARGE*100/BAT_CAP_KWH
        elif h < t_evening:
            diff = pv-load
            if diff>=0:
                p_batt=diff; imp=0; soc+=diff*ETA_CHARGE*100/BAT_CAP_KWH
            else:
                p_batt=0;  imp=-diff
        else:
            needed_pct = SOC_MAX - soc
            needed_kwh = max(0, needed_pct*BAT_CAP_KWH/100)
            p_batt = needed_kwh
            imp    = load + needed_kwh/ETA_CHARGE
            soc += needed_kwh*100/BAT_CAP_KWH

        soc = min(max(soc, SOC_MIN), SOC_MAX)
        total_imp += imp
    return soc, total_imp

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pred",       required=True, help="predictions (.csv/.parquet)")
    p.add_argument("--start_hour", type=int, default=0)
    p.add_argument("--end_hour",   type=int, default=5)
    p.add_argument("--step_min",   type=int, default=15)
    p.add_argument("--evening",    help="HH:MM — фіксований вечірній switch")
    args = p.parse_args()

    df = load_predictions(Path(args.pred))
    # визначимо t_evening
    if args.evening:
        te = int(args.evening.split(":")[0])
    else:
        # беремо останній індекс з timestamp як вечір (приблизно sunset)
        te = df["timestamp"].dt.hour.max()

    best = None
    # генеруємо кандидатні t_night
    times = []
    for h in range(args.start_hour, args.end_hour):
        for m in range(0,60,args.step_min):
            times.append((h, m))
    for h,m in times:
        soc, imp = simulate_soc(df, h, te)
        if best is None or imp < best[2]:
            best = ((h,m), soc, imp)

    (hn, mn), soc_best, imp_best = best
    tn = f"{hn:02d}:{mn:02d}"
    print(f"⏱ Optimal t_night = {tn}")
    print(f"🌇 Evening switch = {te:02d}:00")
    print(f"🔋 Final SOC = {soc_best:.1f}%")
    print(f"🌐 Total import = {imp_best:.2f} kWh")

if __name__=="__main__":
    main()
