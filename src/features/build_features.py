#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
build_features.py
-----------------
• Зчитує clean_daily.csv
• Додає:   – часові фічі  (hour_sin/cos, dow, weekend)
           – лагові       (60 і 180 хв для ключових колонок)
           – ролінгові    (mean / std на 60 і 180 хв)
           – погодні      (temperature, irradiance …) якщо доступні JSON у data/external
• Зберігає features_daily.csv у ../../data/processed
"""

from pathlib import Path
import glob
import pandas as pd
import numpy as np

# --------- шляхи -------------------------------------------------------------
DATA_DIR      = Path("../../data/processed")
CLEAN_CSV     = DATA_DIR / "clean_daily.csv"
WEATHER_DIR   = Path("../../data/external")
OUT_FILE      = DATA_DIR / "features_daily.csv"

# --------- параметри фіч -----------------------------------------------------
LAG_MINUTES   = [60, 180]     # 1 год, 3 год
ROLL_WINDOWS  = [60, 180]     # хвилини
KEY_COLS      = ["pv_kw", "load_kw", "soc_pct"]

# -----------------------------------------------------------------------------


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = df["timestamp"]
    df["hour"]       = ts.dt.hour
    df["hour_sin"]   = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"]   = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow"]        = ts.dt.dayofweek               # Monday=0
    df["is_weekend"] = (df["dow"] >= 5).astype("int")
    return df


def add_lag_features(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    steps = minutes // 5                               # 5-хв інтервал
    for col in KEY_COLS:
        df[f"{col}_lag_{minutes}m"] = df[col].shift(steps)
    return df


def add_roll_features(df: pd.DataFrame, window_min: int) -> pd.DataFrame:
    win = window_min // 5
    for col in KEY_COLS:
        df[f"{col}_roll{window_min}m_mean"] = df[col].rolling(win).mean()
        df[f"{col}_roll{window_min}m_std"]  = df[col].rolling(win).std()
    return df


def merge_weather(df: pd.DataFrame) -> pd.DataFrame:
    files = sorted(glob.glob(str(WEATHER_DIR / "weather_*.json")))
    if not files:
        print("⚠️  Weather JSON not found — фічі погоди пропущені.")
        return df

    w = (
        pd.concat([pd.read_json(f) for f in files], ignore_index=True)
          .rename(columns={"temp": "temperature"})
    )
    w["timestamp"] = pd.to_datetime(w["timestamp"], utc=True).dt.tz_convert("Europe/Kyiv")
    w = w.sort_values("timestamp")

    # найближчий запис погоди до кожної 5-хв мітки (tolerance 30 хв)
    df = pd.merge_asof(
        df.sort_values("timestamp"),
        w.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("30m"),
    )
    return df


def main() -> None:
    if not CLEAN_CSV.exists():
        raise FileNotFoundError(
            f"{CLEAN_CSV} not found — спочатку запустіть preprocessing."
        )

    # ----- завантаження з явним парсингом дати --------------------------------
    df = pd.read_csv(CLEAN_CSV)
    df.rename(columns=lambda c: c.strip(), inplace=True)          # прибрати зайві пробіли
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
          .dt.tz_convert("Europe/Kyiv")
    )

    # ----- генерація фіч ------------------------------------------------------
    df = add_time_features(df)

    for m in LAG_MINUTES:
        df = add_lag_features(df, m)

    for w in ROLL_WINDOWS:
        df = add_roll_features(df, w)

    df = merge_weather(df)

    # Відкидаємо перші max(ROLL) рядків із NaN після ролінга
    drop_n = max(ROLL_WINDOWS) // 5
    df = df.iloc[drop_n:].reset_index(drop=True)

    # ----- збереження ---------------------------------------------------------
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False)
    print(f"✅  Features saved → {OUT_FILE}   ({df.shape[0]:,} rows, {df.shape[1]} cols)")


if __name__ == "__main__":
    main()
