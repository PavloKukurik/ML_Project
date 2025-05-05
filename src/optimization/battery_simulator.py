#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
battery_simulator.py
--------------------
Імітує поведінку АКБ за годинним прогнозом pv/load.
Підтримує CSV та Parquet.
Може брати початковий SoC із попереднього результату.
"""

from pathlib import Path
import argparse, sys
import pandas as pd

# ── Параметри АКБ ─────────────────────────────────────────────────────────────
BAT_CAP_KWH   = 5.0     # ємність АКБ у кВт·год
ETA_CHARGE    = 0.95    # ККД заряджання
ETA_DISCHARGE = 0.90    # ККД розряджання
SOC_MIN, SOC_MAX = 10, 95  # [%]
# ──────────────────────────────────────────────────────────────────────────────


def load_predictions(path: Path) -> pd.DataFrame:
    if not path.exists():
        sys.exit(f"❌ Файл не знайдено: {path}")
    ext = path.suffix.lower()
    try:
        if ext in (".parquet", ".pq"):
            df = pd.read_parquet(path)
        else:
            df = pd.read_csv(path, parse_dates=["timestamp"])
    except (UnicodeDecodeError, pd.errors.ParserError):
        df = pd.read_parquet(path)
    df = df.rename(columns=lambda c: c.strip())
    if "pv_kw_pred" in df and "load_kw_pred" in df:
        df = df.rename(columns={"pv_kw_pred":"pv_kw","load_kw_pred":"load_kw"})
    if not {"timestamp","pv_kw","load_kw"}.issubset(df.columns):
        sys.exit("❌ В прогнозі мають бути колонки timestamp, pv_kw(=_pred), load_kw(=_pred)")
    return df[["timestamp","pv_kw","load_kw"]].sort_values("timestamp")


def get_initial_soc(args) -> float:
    # якщо вказано попередню симуляцію — беремо останній soc_pct
    if args.prev_sim:
        ps = Path(args.prev_sim)
        if not ps.exists():
            sys.exit(f"❌ Файл попередньої симуляції не знайдено: {ps}")
        prev = pd.read_csv(ps)
        soc = prev["soc_pct"].iloc[-1]
        print(f"ℹ️  Взяли початковий SOC = {soc:.1f}% з {ps.name}")
        return soc
    # інакше — беремо з --soc_start
    soc0 = args.soc_start
    if soc0 <= 1:
        soc0 *= 100
    if not (SOC_MIN <= soc0 <= SOC_MAX):
        sys.exit(f"❌ soc_start має бути в межах {SOC_MIN}–{SOC_MAX}%")
    return soc0


def simulate_soc(pred: pd.DataFrame, soc0: float, t_switch_hour: int) -> pd.DataFrame:
    soc_pct = soc0
    records = []
    for _, r in pred.iterrows():
        h, pv, load = r.timestamp.hour, r.pv_kw, r.load_kw
        if h < t_switch_hour:
            p_batt   = -load
            grid_imp = 0.0
            soc_pct += p_batt * ETA_DISCHARGE * 100 / BAT_CAP_KWH
        else:
            diff     = pv - load
            if diff >= 0:
                p_batt   = diff
                grid_imp = 0.0
                soc_pct += diff * ETA_CHARGE * 100 / BAT_CAP_KWH
            else:
                p_batt   = 0.0
                grid_imp = -diff
        soc_pct = min(max(soc_pct, SOC_MIN), SOC_MAX)
        records.append({
            "timestamp": r.timestamp,
            "pv_kw":     pv,
            "load_kw":   load,
            "batt_kw":   p_batt,
            "soc_pct":   soc_pct,
            "grid_import_kw": grid_imp,
        })
    return pd.DataFrame(records)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pred",      required=True,
                   help="path to predictions (.csv or .parquet)")
    p.add_argument("--t_switch",  required=True,
                   help="time HH:MM when to switch to battery")
    p.add_argument("--soc_start", type=float, default=0.8,
                   help="initial SOC (0–1 or %), ignored if --prev_sim set")
    p.add_argument("--prev_sim",  help="path to previous _soc_sim.csv to auto-load SOC")
    args = p.parse_args()

    df_pred = load_predictions(Path(args.pred))
    soc0     = get_initial_soc(args)
    t_switch_hour = int(args.t_switch.split(":")[0])

    sim_df = simulate_soc(df_pred, soc0=soc0, t_switch_hour=t_switch_hour)

    out_csv = Path(args.pred).parent / f"{Path(args.pred).stem}_soc_sim.csv"
    sim_df.to_csv(out_csv, index=False)

    final_soc   = sim_df["soc_pct"].iloc[-1]
    total_import = sim_df["grid_import_kw"].sum()

    print(f"✅ Simulation saved → {out_csv.name}")
    print(f"   Final SOC: {final_soc:.1f}%")
    print(f"   Total import: {total_import:.2f} kWh")

if __name__ == "__main__":
    main()
