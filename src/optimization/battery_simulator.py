# src/optimization/battery_simulator.py

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
battery_simulator.py
--------------------
Імітує поведінку АКБ протягом доби за годинним прогнозом pv/load.
Підтримує CSV та Parquet.
"""

from pathlib import Path
import argparse
import sys
import pandas as pd

# ── Параметри АКБ ─────────────────────────────────────────────────────────────
BAT_CAP_KWH   = 5.0     # ємність АКБ у кВт·год
ETA_CHARGE    = 0.95    # ККД заряджання
ETA_DISCHARGE = 0.90    # ККД розряджання
SOC_MIN       = 10      # мінімальний SoC [%]
SOC_MAX       = 95      # максимальний SoC [%]
# ──────────────────────────────────────────────────────────────────────────────


def load_predictions(path: Path) -> pd.DataFrame:
    """
    Підтримує .parquet або .csv
    Якщо .csv, але містить Parquet-контент, автоматично підхоплює через read_parquet.
    """
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

    # стандартизуємо назви
    df = df.rename(columns=lambda c: c.strip())
    if "pv_kw_pred" in df.columns and "load_kw_pred" in df.columns:
        df = df.rename(columns={"pv_kw_pred": "pv_kw", "load_kw_pred": "load_kw"})
    if not {"timestamp", "pv_kw", "load_kw"}.issubset(df.columns):
        sys.exit("❌ Required columns missing in predictions: timestamp, pv_kw, load_kw")
    return df[["timestamp", "pv_kw", "load_kw"]].sort_values("timestamp")


def simulate_soc(pred: pd.DataFrame, soc0: float, t_switch_hour: int) -> pd.DataFrame:
    """
    Імітує SOC по годинах:
    - до t_switch_hour: тільки розряд (використовує load)
    - після t_switch_hour: pv покриває load, надлишок → заряд, дефіцит → мережа
    """
    # приводимо soc0 до відсотків
    soc_pct = soc0 * 100 if soc0 <= 1 else soc0
    soc_pct = max(min(soc_pct, SOC_MAX), SOC_MIN)

    records = []
    for _, row in pred.iterrows():
        hour = row["timestamp"].hour
        pv   = row["pv_kw"]
        load = row["load_kw"]

        if hour < t_switch_hour:
            # ніч: розряд АКБ на споживання
            p_batt     = -load
            grid_imp   = 0.0
            soc_pct   += p_batt * ETA_DISCHARGE * 100 / BAT_CAP_KWH
        else:
            # день: surplus → заряд АКБ, дефіцит → з мережі
            diff = pv - load
            if diff >= 0:
                p_batt   = diff
                grid_imp = 0.0
                soc_pct += diff * ETA_CHARGE * 100 / BAT_CAP_KWH
            else:
                p_batt   = 0.0
                grid_imp = -diff

        # обмежуємо SoC
        soc_pct = min(max(soc_pct, SOC_MIN), SOC_MAX)

        records.append({
            "timestamp":      row["timestamp"],
            "pv_kw":          pv,
            "load_kw":        load,
            "batt_kw":        p_batt,
            "soc_pct":        soc_pct,
            "grid_import_kw": grid_imp,
        })

    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred",      required=True,
                        help="path to predictions (.csv or .parquet)")
    parser.add_argument("--t_switch",  required=True,
                        help="час перемикання, формат HH:MM")
    parser.add_argument("--soc_start", type=float, default=0.8,
                        help="початковий SoC (0–1 або %)")

    args = parser.parse_args()
    pred_file = Path(args.pred)
    df_pred   = load_predictions(pred_file)

    # конвертуємо soc_start:
    soc0 = args.soc_start if args.soc_start > 1 else args.soc_start * 100
    # витягаємо годину:
    h_switch = int(args.t_switch.split(":")[0])

    sim_df = simulate_soc(df_pred, soc0=soc0, t_switch_hour=h_switch)

    out_csv = pred_file.parent / f"{pred_file.stem}_soc_sim.csv"
    sim_df.to_csv(out_csv, index=False)

    final_soc   = sim_df["soc_pct"].iloc[-1]
    total_import = sim_df["grid_import_kw"].sum()

    print(f"✅ Simulation saved → {out_csv}")
    print(f"   Final SOC: {final_soc:.1f}%")
    print(f"   Total import: {total_import:.2f} kWh")


if __name__ == "__main__":
    main()
