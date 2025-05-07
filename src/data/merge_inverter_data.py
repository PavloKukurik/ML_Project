#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Обʼєднує експортовані .xlsx-файли інвертора у два єдині CSV:
  • daily_merged.csv     — детальні денні файли
  • monthly_merged.csv   — агреговані місячні файли
Запуск:
    python src/data/merge_inverter_data.py
"""

import os, glob, sys
import pandas as pd
from pathlib import Path

RAW_DAILY_DIR   = Path("data/raw")          # сюди Selenium кладе добові .xlsx
RAW_MONTH_DIR   = Path("data/raw_month")    # сюди — місячні .xlsx
OUT_DAILY_DIR   = Path("data/processed/daily")
OUT_MONTH_DIR   = Path("data/processed/monthly")
DAILY_CSV       = OUT_DAILY_DIR / "daily_merged.csv"    # або .csv.gz
MONTH_CSV       = OUT_MONTH_DIR / "monthly_merged.csv"  # або .csv.gz


def merge_folder(folder: Path) -> pd.DataFrame:
    """Читає всі .xlsx у папці й зшиває в один DataFrame"""
    files = sorted(folder.glob("*.xlsx"))
    if not files:
        print(f"[WARN] no .xlsx in {folder}")
        return pd.DataFrame()

    frames = []
    for f in files:
        try:
            frames.append(pd.read_excel(f))
        except Exception as e:
            print(f"[ERR] {f.name}: {e}")

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    # вирівнюємо типи → числові лишаються числовими, решта → string
    df = df.convert_dtypes()
    obj_cols = df.select_dtypes(include="object").columns
    df[obj_cols] = df[obj_cols].astype("string")

    return df


def main() -> None:
    OUT_DAILY_DIR.mkdir(parents=True, exist_ok=True)
    OUT_MONTH_DIR.mkdir(parents=True, exist_ok=True)

    # --- денні ---
    print("📚  merging DAILY exports …")
    df_daily = merge_folder(RAW_DAILY_DIR)
    if not df_daily.empty:
        df_daily.to_csv(DAILY_CSV, index=False)           #  + compression="gzip"
        print(f"✅  saved {DAILY_CSV}  ({len(df_daily):,} rows)")
    else:
        print("⚠️  daily folder empty — skipped")

    # --- місячні ---
    print("\n📚  merging MONTHLY exports …")
    df_month = merge_folder(RAW_MONTH_DIR)
    if not df_month.empty:
        df_month.to_csv(MONTH_CSV, index=False)           #  + compression="gzip"
        print(f"✅  saved {MONTH_CSV}  ({len(df_month):,} rows)")
    else:
        print("⚠️  monthly folder empty — skipped")


if __name__ == "__main__":
    sys.exit(main())
