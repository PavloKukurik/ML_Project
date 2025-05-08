#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
models.inference
────────────────
predict_day(date)  – 24‑годинний прогноз PV / Load із урахуванням
                     погодного forecast (`w_temp`, `w_cloud`, `w_swr`).

update_features()  – переганяє сирі .xlsx → features_daily.csv (без погоди).
"""

from pathlib import Path
from datetime import datetime, timedelta
import math, pickle, pandas as pd, numpy as np

DATA_DIR = Path("data/processed")
MOD_DIR  = Path("artifacts/models")

FEATURE_CSV = DATA_DIR / "features_daily.csv"
CONSUMP_PKL = MOD_DIR  / "consumption_xgb.pkl"
GENER_PKL   = MOD_DIR  / "generation_xgb.pkl"

# ── weather forecast loader ───────────────────────────────────────────
def _ensure_forecast(date_str: str) -> pd.DataFrame:
    fp = Path(f"data/weather/forecast_hourly_{date_str}.csv")
    if not fp.exists():
        from data.get_openmeteo_forecast import fetch_forecast
        fetch_forecast(date_str)
    df = pd.read_csv(fp)
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], utc=True)
          .dt.tz_convert("Europe/Kyiv")
    )
    return df.rename(columns={
        "temperature_2m":      "w_temp",
        "cloud_cover":         "w_cloud",
        "shortwave_radiation": "w_swr"
    })

# ── helper: додаємо time‑фічі ──────────────────────────────────────────
def _add_time_features(vec: pd.Series, ts: pd.Timestamp) -> pd.Series:
    v = vec.copy()
    if "hour" in v:  v["hour"]  = ts.hour
    if "dow"  in v:  v["dow"]   = ts.dayofweek
    if "month" in v: v["month"] = ts.month

    if "hour_sin" in v:
        v["hour_sin"] = math.sin(2*math.pi*ts.hour/24)
    if "hour_cos" in v:
        v["hour_cos"] = math.cos(2*math.pi*ts.hour/24)
    if "dow_sin" in v:
        v["dow_sin"]  = math.sin(2*math.pi*ts.dayofweek/7)
    if "dow_cos" in v:
        v["dow_cos"]  = math.cos(2*math.pi*ts.dayofweek/7)
    return v

# ───────────────────────────────────────────────────────────────────────
def predict_day(date_str: str) -> pd.DataFrame:
    """Прогноз 00:00→23:00 (Europe/Kyiv) з weather‑forecast на date_str."""
    # 1) вхідні дані
    df   = pd.read_csv(FEATURE_CSV)
    df["timestamp"] = (
        pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
          .dt.tz_convert("Europe/Kyiv")
    )
    hr = (df.set_index("timestamp")
            .resample("1h").mean()
            .dropna(subset=["load_kw","pv_kw"])
            .reset_index())

    start_dt   = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=None)
    start_dt   = pd.Timestamp(start_dt, tz="Europe/Kyiv")
    last_row   = hr[hr["timestamp"] < start_dt].iloc[-1]

    # 2) weather‑forecast на дату
    wf = _ensure_forecast(date_str).sort_values("timestamp").reset_index(drop=True)

    # 3) формуємо 24 рядки фіч з оновленими time + weather
    base = last_row.drop(labels=["timestamp","pv_kw","load_kw"])
    rows = []
    for i in range(24):
        ts  = start_dt + timedelta(hours=i)
        vec = _add_time_features(base, ts)

        # підставляємо прогноз‑погоду
        for col in ["w_temp","w_cloud","w_swr"]:
            if col in vec:
                vec[col] = wf.at[i, col]
        rows.append(vec.values)

    X = np.vstack(rows)

    # 4) моделі
    with open(CONSUMP_PKL, "rb") as f:
        cons_models = pickle.load(f)
    with open(GENER_PKL, "rb") as f:
        pv_models   = pickle.load(f)

    load_pred = np.mean([m.predict(X) for m in cons_models], axis=0)
    pv_pred   = np.mean([m.predict(X) for m in pv_models ], axis=0)

    stamps = [start_dt + timedelta(hours=i) for i in range(24)]
    return pd.DataFrame({"timestamp": stamps,
                         "pv_kw":     pv_pred,
                         "load_kw":   load_pred})
