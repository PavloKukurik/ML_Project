"""
Об’єднує hourly + daily CSV, додає derived-features і
зберігає готовий датасет.
"""

import pandas as pd, numpy as np, argparse, os, pathlib

def build_weather_features(hourly_path: str, daily_path: str, output_path: str):
    # ---------- читання ----------
    hourly = pd.read_csv(hourly_path, parse_dates=["time"])
    daily  = pd.read_csv(daily_path,  parse_dates=["sunrise", "sunset"])

    # ---------- базові ----------
    hourly["hour_of_day"] = hourly["time"].dt.hour
    hourly["date"]        = hourly["time"].dt.date
    daily ["date"]        = pd.to_datetime(daily["date"]).dt.date  # вирівнюємо тип

    # ---------- merge ----------
    merged = hourly.merge(
        daily, on="date", how="left", suffixes=("", "_daily")
    )

    # ---------- derived ----------
    merged["is_daylight"] = (
        (merged["time"] >= merged["sunrise"]) &
        (merged["time"] <= merged["sunset"])
    ).astype(int)

    merged["sun_fraction_hour"] = merged["daylight_duration"] / (24 * 3600)

    merged["cloud_cover_rolling"] = (
        merged["cloud_cover"].rolling(window=3, min_periods=1).mean()
    )

    merged["irradiance_cumsum"] = (
        merged.groupby("date")["shortwave_radiation"].cumsum()
    )

    # ---------- save ----------
    pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    print(f"[✅] Processed CSV → {output_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hourly", required=True)
    ap.add_argument("--daily",  required=True)
    ap.add_argument("--output", default="data/weather/processed_weather.csv")
    cfg = ap.parse_args()
    build_weather_features(cfg.hourly, cfg.daily, cfg.output)
