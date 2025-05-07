#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
battery_simulator.py
--------------------
Імітує роботу АКБ з двома перемиканнями:
  1) t_night   — перемикання на батарею вночі
  2) t_evening — повернення на мережу ввечері із дозаправкою до 100%

Підтримує .csv та .parquet для прогнозу.
"""

from pathlib import Path
import argparse, sys
import pandas as pd

# Параметри АКБ
BAT_CAP_KWH   = 5.0     # kWh
ETA_CHARGE    = 0.95
ETA_DISCHARGE = 0.90
SOC_MIN, SOC_MAX = 10, 95  # відсотки

def load_predictions(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext in (".parquet", ".pq"):
        df = pd.read_parquet(path)
    else:
        try:
            df = pd.read_csv(path, parse_dates=["timestamp"])
        except (UnicodeDecodeError, pd.errors.ParserError):
            df = pd.read_parquet(path)
    df = df.rename(columns=lambda c: c.strip())
    if "pv_kw_pred" in df.columns:
        df = df.rename(columns={"pv_kw_pred":"pv_kw","load_kw_pred":"load_kw"})
    if not {"timestamp","pv_kw","load_kw"}.issubset(df.columns):
        sys.exit("❌ В прогнозі мають бути колонки timestamp, pv_kw, load_kw")
    return df.sort_values("timestamp")[["timestamp","pv_kw","load_kw"]]

def simulate_soc(df, t_night:int, t_evening:int) -> pd.DataFrame:
    soc = SOC_MAX  # стартуємо з 100 %
    batt_kw, grid_kw, soc_pct = [], [], []

    for _, row in df.iterrows():
        h, pv, load = row["timestamp"].hour, row["pv_kw"], row["load_kw"]

        # 1) ніч: до t_night — живимося з батареї
        if h < t_night:
            p_batt = -load
            imp    = 0
            soc   += p_batt * ETA_DISCHARGE * 100 / BAT_CAP_KWH

        # 2) день: між t_night та t_evening — PV→споживання, надлишок→батарея
        elif h < t_evening:
            diff = pv - load
            if diff >= 0:
                p_batt = diff
                imp    = 0
                soc   += diff * ETA_CHARGE * 100 / BAT_CAP_KWH
            else:
                p_batt = 0
                imp    = -diff

        # 3) вечір: від t_evening — живимося з мережі та заряджаємо батарею до 100 %
        else:
            needed_pct = SOC_MAX - soc
            needed_kwh = max(0, needed_pct * BAT_CAP_KWH / 100)
            p_batt     = needed_kwh
            imp        = load + needed_kwh / ETA_CHARGE
            soc       += needed_kwh * 100 / BAT_CAP_KWH

        # обмеження SOC
        soc = min(max(soc, SOC_MIN), SOC_MAX)

        batt_kw.append(p_batt)
        grid_kw.append(imp)
        soc_pct.append(soc)

    out = df.copy()
    out["batt_kw"]        = batt_kw
    out["soc_pct"]        = soc_pct
    out["grid_import_kw"] = grid_kw
    return out

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred",      required=True, help="path to predictions (.csv/.parquet)")
    parser.add_argument("--t_night",   required=True, help="HH:MM — нічне перемикання")
    parser.add_argument("--t_evening", required=True, help="HH:MM — вечірнє перемикання")
    args = parser.parse_args()

    df = load_predictions(Path(args.pred))
    hn = int(args.t_night.split(":")[0])
    he = int(args.t_evening.split(":")[0])
    sim = simulate_soc(df, hn, he)

    out_path = Path(args.pred).parent / f"{Path(args.pred).stem}_soc_sim.csv"
    sim.to_csv(out_path, index=False)
    print(f"✅ Saved → {out_path}")
    print(f"   Final SOC: {sim['soc_pct'].iloc[-1]:.1f}%")
    print(f"   Total import: {sim['grid_import_kw'].sum():.2f} kWh")

if __name__=="__main__":
    main()
