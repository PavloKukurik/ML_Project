#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_features.py  (v2 – з погодою CSV)
---------------------------------------
• Зчитує clean_daily.csv  (5-хв телеметрія)
• Додає часові, лагові, ролінгові фічі
• Підтягує погоду з processed_weather_2025.csv
• Зберігає features_daily.csv  у ../../data/processed
"""

from pathlib import Path
import sys
import pandas as pd
import numpy as np

# ───── ШЛЯХИ ────────────────────────────────────────────────────────────────
DATA_DIR    = Path("../../data/processed")
CLEAN_CSV   = DATA_DIR / "clean_daily.csv"
WEATHER_CSV = Path("../../data/external/processed_weather_2025.csv")
OUT_CSV     = DATA_DIR / "features_daily.csv"

# ───── ПАРАМЕТРИ ФІЧ ────────────────────────────────────────────────────────
LAG_MIN    = [60, 180]    # хвилини для лагів
ROLL_MIN   = [60, 180]    # хвилини для ролінгів
KEY_COLS   = ["pv_kw", "load_kw", "soc_pct"]

WEATHER_KEEP = [
    "temperature_2m",
    "relative_humidity_2m",
    "cloud_cover",
    "shortwave_radiation",
    "precipitation_probability",
    "wind_speed_10m",
    "weather_code",
]

# ───── ФУНКЦІЇ ───────────────────────────────────────────────────────────────

def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = df["timestamp"]
    df["hour"]       = ts.dt.hour
    df["hour_sin"]   = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"]   = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow"]        = ts.dt.dayofweek
    df["is_weekend"] = (df["dow"] >= 5).astype("int8")
    return df

def add_lag(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    steps = minutes // 5
    for c in KEY_COLS:
        df[f"{c}_lag_{minutes}m"] = df[c].shift(steps)
    return df

def add_roll(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    window = minutes // 5
    for c in KEY_COLS:
        df[f"{c}_roll{minutes}m_mean"] = df[c].rolling(window).mean()
        df[f"{c}_roll{minutes}m_std"]  = df[c].rolling(window).std()
    return df

def load_weather(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        print("⚠️  Weather CSV not found – без погодних фіч.")
        return None
    w = pd.read_csv(path, parse_dates=["time"])
    w = w.rename(columns={"time": "timestamp"})
    # локалізуємо час
    w["timestamp"] = pd.to_datetime(w["timestamp"], errors="coerce", utc=True)
    w["timestamp"] = w["timestamp"].dt.tz_convert("Europe/Kyiv")
    keep = [c for c in WEATHER_KEEP if c in w.columns]
    w = w[["timestamp", *keep]].sort_values("timestamp")
    return w

def merge_weather(df: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    # перед merge_asof видаляємо будь-які NaT у df.timestamp
    df = df.dropna(subset=["timestamp"])
    return pd.merge_asof(
        df.sort_values("timestamp"),
        weather.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("30m"),
    )

# ───── ГОЛОВНА ЛОГІКА ───────────────────────────────────────────────────────

def main() -> None:
    if not CLEAN_CSV.exists():
        sys.exit(f"❌ {CLEAN_CSV} not found – спочатку запустіть preprocessing.py")

    # 1) Завантажуємо clean_daily
    df = pd.read_csv(CLEAN_CSV)
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
          .dt.tz_convert("Europe/Kyiv")
    )
    # Видаляємо рядки з невірними часами
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    # 2) Додаємо часові, лагові, ролінгові фічі
    df = add_time_features(df)
    for m in LAG_MIN:
        df = add_lag(df, m)
    for m in ROLL_MIN:
        df = add_roll(df, m)

    # 3) Мержимо погоду
    weather_df = load_weather(WEATHER_CSV)
    if weather_df is not None:
        df = merge_weather(df, weather_df)

    # 4) Обрізаємо початкові NaN від ролінгів
    drop_n = max(ROLL_MIN) // 5
    df = df.iloc[drop_n:].reset_index(drop=True)

    # 5) Зберігаємо результати
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"✅  Features saved → {OUT_CSV}   ({df.shape[0]:,} rows, {df.shape[1]} cols)")

if __name__ == "__main__":
    main()
