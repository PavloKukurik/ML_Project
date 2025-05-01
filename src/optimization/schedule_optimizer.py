# src/optimization/schedule_optimizer.py

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
schedule_optimizer.py
---------------------
Перебирає можливі t_switch і обирає:
 - мінімум total_import (objective=min_import)
 - або максимум final soc (objective=max_soc)
"""

from pathlib import Path
import argparse
import sys
import pandas as pd

def load_predictions(path: Path) -> pd.DataFrame:
    if not path.exists():
        sys.exit(f"❌ File not found: {path}")
    ext = path.suffix.lower()
    try:
        if ext in (".parquet", ".pq"):
            df = pd.read_parquet(path)
        else:
            df = pd.read_csv(path, parse_dates=["timestamp"])
    except (UnicodeDecodeError, pd.errors.ParserError):
        df = pd.read_parquet(path)

    df = df.rename(columns=lambda c: c.strip())
    if "pv_kw_pred" in df.columns and "load_kw_pred" in df.columns:
        df = df.rename(columns={"pv_kw_pred":"pv_kw", "load_kw_pred":"load_kw"})
    if not {"timestamp","pv_kw","load_kw"}.issubset(df.columns):
        sys.exit("❌ Required columns missing in predictions")
    return df[["timestamp","pv_kw","load_kw"]].sort_values("timestamp")


def simulate_soc(df, soc0, t_switch_hour):
    # копія логіки з battery_simulator
    BAT_CAP_KWH = 5.0; ETA_CHARGE=0.95; ETA_DISCHARGE=0.90; SOC_MIN=10; SOC_MAX=95
    soc_pct = soc0 if soc0>1 else soc0*100
    soc_pct = min(max(soc_pct, SOC_MIN), SOC_MAX)
    total_import = 0.0

    for _, r in df.iterrows():
        h = r.timestamp.hour
        pv, load = r.pv_kw, r.load_kw
        if h < t_switch_hour:
            diff = -load
            soc_pct += diff * ETA_DISCHARGE * 100 / BAT_CAP_KWH
            imp = 0.0
        else:
            diff = pv - load
            if diff >= 0:
                soc_pct += diff * ETA_CHARGE * 100 / BAT_CAP_KWH
                imp = 0.0
            else:
                imp = -diff
        soc_pct = min(max(soc_pct, SOC_MIN), SOC_MAX)
        total_import += imp

    return soc_pct, total_import


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred",       required=True,
                        help="path to predictions (.csv or .parquet)")
    parser.add_argument("--soc_start",  type=float, default=0.8,
                        help="початковий SoC (0–1 або %)")
    parser.add_argument("--start_hour", type=int, default=0,
                        help="початкова година для перебору")
    parser.add_argument("--end_hour",   type=int, default=5,
                        help="кінець години (не включно)")
    parser.add_argument("--step_min",   type=int, default=15,
                        help="інтервал кроку (хвилини)")
    parser.add_argument("--objective",  choices=["min_import","max_soc"],
                        default="min_import")

    args = parser.parse_args()
    df_pred = load_predictions(Path(args.pred))
    soc0    = args.soc_start if args.soc_start > 1 else args.soc_start * 100

    best = None
    # генеруємо всі варіанти часу
    candidates = []
    for h in range(args.start_hour, args.end_hour):
        for m in range(0, 60, args.step_min):
            candidates.append((h, m))

    for h, m in candidates:
        final_soc, imp = simulate_soc(df_pred, soc0, h)
        if best is None or (
           args.objective=="min_import" and imp < best[2]
        ) or (
           args.objective=="max_soc"    and final_soc > best[1]
        ):
            best = ((h, m), final_soc, imp)

    (h_best, m_best), soc_best, imp_best = best
    t_best = f"{h_best:02d}:{m_best:02d}"

    print(f"⏱ Optimal t_switch = {t_best}")
    print(f"🔋 Final SOC       = {soc_best:.1f}%")
    print(f"🌐 Total import    = {imp_best:.2f} kWh")


if __name__ == "__main__":
    main()
