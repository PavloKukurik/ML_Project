#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_features.py
─────────────────
Читає:
  data/processed/clean_daily.csv           – інвертор (1 хв / 5 хв)
  data/weather/history_hourly_*.csv        – історична погода (hourly)

Робить:
  • агрегує інвертор → hourly (mean)
  • asof‑merge з погодою (≤30 хв допуск)
  • додає часові ознаки (hour, dow, month, синуси/косинуси)
  • зберігає  features_daily.csv  (hourly rows)
"""

from pathlib import Path
import math, glob, pandas as pd, numpy as np

# ── файли ─────────────────────────────────────────────────────────────
PROC_DIR = Path("data/processed")
WEATH_DIR= Path("data/weather")
OUT_CSV  = PROC_DIR / "features_daily.csv"

INV_FILE = PROC_DIR / "clean_daily.csv"          # агреговані ваші .xlsx

# ── зчитуємо інвертор (timestamp UTC) ──────────────────────────────────
inv = pd.read_csv(INV_FILE)
inv["timestamp"] = pd.to_datetime(inv["timestamp"], utc=True, errors="coerce")
inv = inv.dropna(subset=["timestamp"])
inv = inv.rename(columns={"AC_Power(kW)": "load_kw",
                          "PV_Power(kW)": "pv_kw"})

# ≥ перетворюємо в Europe/Kyiv
inv["timestamp"] = inv["timestamp"].dt.tz_convert("Europe/Kyiv")
inv = (inv.set_index("timestamp")
          .resample("1h")
          .mean()
          .dropna(subset=["load_kw","pv_kw"])
          .reset_index())

# ── читаємо всі history_hourly_*weather CSV ───────────────────────────
weather_files = glob.glob(str(WEATH_DIR / "history_hourly_*.csv"))
weather = (pd.concat(
    (pd.read_csv(f) for f in weather_files), ignore_index=True)
    .rename(columns={"time": "timestamp"})
)
weather["timestamp"] = pd.to_datetime(weather["timestamp"], utc=True, errors="coerce")
weather["timestamp"] = weather["timestamp"].dt.tz_convert("Europe/Kyiv")
weather = weather.sort_values("timestamp")

# залишаємо лише 24‑годинні фічі, перейменовуємо для зручності
WEATH_COLS = {
    "temperature_2m":      "w_temp",
    "cloud_cover":         "w_cloud",
    "shortwave_radiation": "w_swr",
}
weather = weather[["timestamp"] + list(WEATH_COLS)]
weather = weather.rename(columns=WEATH_COLS)

# ── asof‑merge (≤30 хв) ───────────────────────────────────────────────
inv   = inv.sort_values("timestamp")
weather = weather.sort_values("timestamp")

df = pd.merge_asof(inv, weather,
                   on="timestamp",
                   tolerance=pd.Timedelta("30min"))

# ── часові ознаки ─────────────────────────────────────────────────────
ts = df["timestamp"].dt
df["hour"]      = ts.hour
df["dow"]       = ts.dayofweek
df["month"]     = ts.month
df["hour_sin"]  = np.sin(2*np.pi*df["hour"]/24)
df["hour_cos"]  = np.cos(2*np.pi*df["hour"]/24)
df["dow_sin"]   = np.sin(2*np.pi*df["dow"]/7)
df["dow_cos"]   = np.cos(2*np.pi*df["dow"]/7)

# ── заповнюємо прогалини погоди лінійною інтерполяцією ────────────────
df[["w_temp","w_cloud","w_swr"]] = (
    df[["w_temp","w_cloud","w_swr"]]
      .interpolate(limit_direction="both")
)

# ── зберігаємо ────────────────────────────────────────────────────────
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT_CSV, index=False)
print(f"[✅] features_daily.csv saved → {OUT_CSV}   ({len(df)} rows, {df.shape[1]} cols)")
