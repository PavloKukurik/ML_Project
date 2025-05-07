#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
inference.py  –  формує добовий прогноз load_kw / pv_kw
"""

from pathlib import Path
from datetime import timedelta
import sys, pickle
import pandas as pd
import numpy as np
# ───────────────────────────────────────────────────────────────
# 0. Оновлюємо прогноз погоди в реальному часі
# ───────────────────────────────────────────────────────────────
from data.fetch_weather_for_model import fetch_and_save

# --- шляхи -----------------------------------------------------------
DATA_DIR = Path("../../data/processed")
MOD_DIR  = Path("../../artifacts/models")
OUT_DIR  = Path("../../data/predictions"); OUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_CSV     = DATA_DIR / "features_daily.csv"
CONSUMP_PKL     = MOD_DIR  / "consumption_xgb.pkl"
GENER_PKL       = MOD_DIR  / "generation_xgb.pkl"

# ---------------------------------------------------------------------

def load_features() -> pd.DataFrame:
    df = pd.read_csv(FEATURE_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])
    df["timestamp"] = df["timestamp"].dt.tz_convert("Europe/Kyiv").dt.tz_localize(None)
    print("ℹ️  features rows:", len(df))
    return df


def to_hourly(df: pd.DataFrame) -> pd.DataFrame:
    df = df.set_index("timestamp")

    # середнє для всіх числових
    agg = {c: "mean" for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    hourly = df.resample("1h").agg(agg)

    # залишаємо години, де є і load, і pv
    hourly = hourly.dropna(subset=["load_kw", "pv_kw"])
    print("ℹ️  hourly rows :", len(hourly))
    return hourly.reset_index()


def load_models(pkl: Path):
    with open(pkl, "rb") as f:
        return pickle.load(f)


def predict(models, x: np.ndarray) -> np.ndarray:
    return np.array([m.predict(x.reshape(1, -1))[0] for m in models])


def main():
    # ───────────────────────────────────────────────────────────────
    # 1) Спершу оновлюємо прогноз погоди для моделі
    # ───────────────────────────────────────────────────────────────
    print("🔄 Updating weather features...")
    fetch_and_save()

    # --- перевіряємо наявність файлів
    for f in (FEATURE_CSV, CONSUMP_PKL, GENER_PKL):
        if not f.exists():
            sys.exit(f"❌ {f} not found – перевірте попередні етапи.")

    # --- завантажуємо фічі та робимо агрегацію по годинах
    df = load_features()
    hourly = to_hourly(df)

    if len(hourly) < 25:
        sys.exit("⚠️  Менше 25 годинних точок – пропускаємо прогноз.")

    latest = hourly.iloc[-1]
    X_vec  = latest.drop("timestamp").values

    # --- завантажуємо моделі
    load_models_list = load_models(CONSUMP_PKL)
    gen_models_list  = load_models(GENER_PKL)

    # --- робимо прогноз
    load_pred = predict(load_models_list, X_vec).astype("float32")
    pv_pred   = predict(gen_models_list,  X_vec).astype("float32")

    # --- формуємо часові мітки для наступних 24 г
    start_ts = latest["timestamp"].replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    stamps   = [start_ts + timedelta(hours=i) for i in range(24)]

    # --- зберігаємо результат
    out = pd.DataFrame({
        "timestamp": stamps,
        "load_kw_pred": load_pred,
        "pv_kw_pred":   pv_pred,
    })

    out_path = OUT_DIR / f"{start_ts.date()}_predictions.csv"
    out.to_parquet(out_path, index=False)
    print(f"✅  Saved → {out_path}")


if __name__ == "__main__":
    main()
