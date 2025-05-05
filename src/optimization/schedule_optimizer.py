#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
schedule_optimizer.py
---------------------
Перебирає t_switch, автоматично дістає pocх_start із попередньої симуляції або з аргументу.
"""

from pathlib import Path
import argparse, sys
import pandas as pd

def load_predictions(path: Path) -> pd.DataFrame:
    if not path.exists(): sys.exit(f"❌ File not found: {path}")
    ext = path.suffix.lower()
    try:
        df = pd.read_parquet(path) if ext in (".parquet"," .pq") else pd.read_csv(path, parse_dates=["timestamp"])
    except:
        df = pd.read_parquet(path)
    df = df.rename(columns=lambda c: c.strip())
    if "pv_kw_pred" in df and "load_kw_pred" in df:
        df = df.rename(columns={"pv_kw_pred":"pv_kw","load_kw_pred":"load_kw"})
    if not {"timestamp","pv_kw","load_kw"}.issubset(df.columns):
        sys.exit("❌ predictions must include timestamp, pv_kw, load_kw")
    return df.sort_values("timestamp")

def get_initial_soc(args) -> float:
    if args.prev_sim:
        df = pd.read_csv(args.prev_sim)
        soc = df["soc_pct"].iloc[-1]
        print(f"ℹ️  Initial SOC loaded from {Path(args.prev_sim).name}: {soc:.1f}%")
        return soc
    soc0 = args.soc_start
    return soc0*100 if soc0 <= 1 else soc0

def simulate_soc(df, soc0, t_switch_hour):
    BAT, ηc, ηd = 5.0, 0.95, 0.90
    SOC_MIN, SOC_MAX = 10, 95
    soc = soc0
    total_import = 0.0
    for _, r in df.iterrows():
        h, pv, load = r.timestamp.hour, r.pv_kw, r.load_kw
        if h < t_switch_hour:
            diff = -load
            soc += diff * ηd * 100 / BAT
            imp = 0.0
        else:
            diff = pv - load
            if diff >= 0:
                soc += diff * ηc * 100 / BAT
                imp = 0.0
            else:
                soc += 0
                imp = -diff
        soc = min(max(soc, SOC_MIN), SOC_MAX)
        total_import += imp
    return soc, total_import

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pred",       required=True)
    p.add_argument("--soc_start",  type=float, default=0.8)
    p.add_argument("--prev_sim",   help="path to previous _soc_sim.csv")
    p.add_argument("--start_hour", type=int, default=0)
    p.add_argument("--end_hour",   type=int, default=5)
    p.add_argument("--step_min",   type=int, default=15)
    p.add_argument("--objective",  choices=["min_import","max_soc"], default="min_import")
    args = p.parse_args()

    df = load_predictions(Path(args.pred))
    soc0 = get_initial_soc(args)

    best = None
    times = [(h, m) for h in range(args.start_hour, args.end_hour)
                    for m in range(0, 60, args.step_min)]
    for h, m in times:
        final_soc, imp = simulate_soc(df, soc0, h)
        if best is None or (
            args.objective=="min_import" and imp < best[2]
        ) or (
            args.objective=="max_soc" and final_soc > best[1]
        ):
            best = ((h, m), final_soc, imp)

    (h_opt,m_opt), soc_opt, imp_opt = best
    print(f"⏱ Optimal t_switch = {h_opt:02d}:{m_opt:02d}")
    print(f"🔋 Final SOC       = {soc_opt:.1f}%")
    print(f"🌐 Total import    = {imp_opt:.2f} kWh")

if __name__=="__main__":
    main()
