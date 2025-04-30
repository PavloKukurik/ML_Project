#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
battery_simulator.py
--------------------
Імітує поведінку АКБ по годинному прогнозу (pv/load).
Підтримує CSV та Parquet.
"""

from pathlib import Path
import argparse, sys
import pandas as pd

# --- Параметри АКБ ----------------------------------------------------------
BAT_CAP_KWH   = 5.0     # ємність
ETA_CHARGE    = 0.95
ETA_DISCHARGE = 0.90
SOC_MIN, SOC_MAX = 10, 95  # [%]
# ----------------------------------------------------------------------------

def load_predictions(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext in (".parquet", ".pq"):
        df = pd.read_parquet(path)
    elif ext == ".csv":
        df = pd.read_csv(path, parse_dates=["timestamp"])
    else:
        sys.exit(f"❌ Unsupported prediction file type: {ext}")
    # стандартизуємо колонки
    df = df.rename(columns=lambda c: c.strip())
    if "pv_kw_pred" in df.columns:
        df = df.rename(columns={"pv_kw_pred":"pv_kw","load_kw_pred":"load_kw"})
    if not {"timestamp","pv_kw","load_kw"}.issubset(df.columns):
        sys.exit("❌ Required columns missing in predictions")
    return df[["timestamp","pv_kw","load_kw"]]

def simulate_soc(pred: pd.DataFrame, soc0: float, t_switch_hour: int) -> pd.DataFrame:
    """Повертає DF з batt_kw, soc_pct, grid_import_kw для кожної години."""
    soc = []
    batt = []
    grid = []
    soc_pct = soc0 if soc0>1 else soc0*100

    for _, row in pred.sort_values("timestamp").iterrows():
        h = row["timestamp"].hour
        pv, load = row["pv_kw"], row["load_kw"]
        if h < t_switch_hour:
            # ніч: тільки розряд
            p_batt = -load
            soc_pct += p_batt * ETA_DISCHARGE * 100 / BAT_CAP_KWH
            grid_kw = 0
        else:
            # день: surplus → заряд, дефіцит → мережа
            diff = pv - load
            if diff >= 0:
                p_batt = diff
                soc_pct += diff * ETA_CHARGE * 100 / BAT_CAP_KWH
                grid_kw = 0
            else:
                p_batt = 0
                grid_kw = -diff

        # обмеження SOC
        soc_pct = min(max(soc_pct, SOC_MIN), SOC_MAX)
        soc.append(soc_pct)
        batt.append(p_batt)
        grid.append(grid_kw)

    out = pred.copy()
    out["batt_kw"]          = batt
    out["soc_pct"]          = soc
    out["grid_import_kw"]   = grid
    return out

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pred",      required=True, help="path to predictions (.csv or .parquet)")
    p.add_argument("--t_switch",  required=True, help="HH:MM – час перемикання (локальний)")
    p.add_argument("--soc_start", type=float, default=0.8, help="початковий SOC (0–1 або %)")
    args = p.parse_args()

    pred_file = Path(args.pred)
    if not pred_file.exists():
        sys.exit(f"❌ File not found: {pred_file}")

    df = load_predictions(pred_file)
    # конвертуємо soc_start
    soc0 = args.soc_start * 100 if args.soc_start <= 1 else args.soc_start
    h_switch = int(args.t_switch.split(":")[0])

    sim = simulate_soc(df, soc0=soc0, t_switch_hour=h_switch)
    # вивід
    end_soc = sim["soc_pct"].iloc[-1]
    total_imp = sim["grid_import_kw"].sum()
    out_csv = pred_file.parent / f"{pred_file.stem}_soc_sim.csv"
    sim.to_csv(out_csv, index=False)
    print(f"✅ Simulation saved → {out_csv}")
    print(f"   Final SOC: {end_soc:.1f}%")
    print(f"   Total import: {total_imp:.2f} kWh")

if __name__=="__main__":
    main()
