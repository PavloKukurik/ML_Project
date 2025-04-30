#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
train_generation.py  –  XGBoost baseline for pv_kw
"""

from pathlib import Path
import sys, pickle
import pandas as pd
import numpy as np
import xgboost as xgb

FEATURES_CSV = Path("../../data/processed/features_daily.csv")
MODEL_DIR    = Path("../../artifacts/models"); MODEL_DIR.mkdir(parents=True, exist_ok=True)
TARGET       = "pv_kw"

# -----------------------------------------------------------------------------
def parse_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("Europe/Kyiv", nonexistent="shift_forward")
    return df

def make_hourly(df: pd.DataFrame) -> pd.DataFrame:
    df = df.set_index("timestamp")
    agg = {c: "mean" for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    hr  = df.resample("1h").agg(agg).dropna(subset=[TARGET])
    return hr.reset_index()

def make_supervised(hr: pd.DataFrame):
    X, y = [], []
    for start in range(len(hr) - 24):
        X.append(hr.iloc[start].drop("timestamp").values)
        y.append(hr[TARGET].iloc[start + 1:start + 25].values)
    if not X:
        sys.exit("❌ ERROR: після агрегації <25 годинних точок – нема чого тренувати.")
    return np.vstack(X), np.vstack(y)

def train():
    if not FEATURES_CSV.exists():
        sys.exit(f"❌ {FEATURES_CSV} not found")

    df = pd.read_csv(FEATURES_CSV)
    if "timestamp" not in df.columns or TARGET not in df.columns:
        sys.exit("❌ потрібних колонок немає у features CSV")

    df = parse_timestamp(df)
    hourly = make_hourly(df)
    print("ℹ️  hourly rows:", len(hourly))

    X, Y = make_supervised(hourly)

    models = []
    for h in range(24):
        mdl = xgb.XGBRegressor(
            n_estimators=400, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, objective="reg:squarederror",
            random_state=42,
        )
        mdl.fit(X, Y[:, h])
        models.append(mdl)

    with open(MODEL_DIR / "generation_xgb.pkl", "wb") as f:
        pickle.dump(models, f)

    print("✅  generation_xgb.pkl saved")

if __name__ == "__main__":
    train()
