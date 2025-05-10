from pathlib import Path
from datetime import datetime, timedelta
import math, pickle, pandas as pd, numpy as np

DATA_CSV = Path("data/processed/features_daily.csv")
MOD_DIR  = Path("artifacts/models")
CONSUMP_PKL = MOD_DIR / "consumption_xgb.pkl"
PV_PKL      = MOD_DIR / "generation_xgb.pkl"

from data.get_openmeteo_forecast import fetch_forecast
def _forecast(date_str: str) -> pd.DataFrame:
    fp = Path(f"data/weather/forecast_hourly_{date_str}.csv")
    if not fp.exists():
        fetch_forecast(date_str)
    df = pd.read_csv(fp)
    df["timestamp"] = (pd.to_datetime(df["timestamp"], utc=True)
                         .dt.tz_convert("Europe/Kyiv"))
    return (df.rename(columns={
        "temperature_2m":      "w_temp",
        "cloud_cover":         "w_cloud",
        "shortwave_radiation": "w_swr"
    })[["timestamp","w_temp","w_cloud","w_swr"]])

def _add_time_cols(vec: pd.Series, ts) -> pd.Series:
    vec = vec.copy()
    vec["hour"]  = ts.hour
    vec["dow"]   = ts.dayofweek
    vec["month"] = ts.month
    vec["hour_sin"] = math.sin(2*math.pi*ts.hour/24)
    vec["hour_cos"] = math.cos(2*math.pi*ts.hour/24)
    vec["dow_sin"]  = math.sin(2*math.pi*ts.dayofweek/7)
    vec["dow_cos"]  = math.cos(2*math.pi*ts.dayofweek/7)
    return vec

def predict_day(date_str: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_CSV)
    df["timestamp"] = (pd.to_datetime(df["timestamp"], utc=True)
                         .dt.tz_convert("Europe/Kyiv"))

    hr = (df.set_index("timestamp")
            .resample("1h").mean()
            .dropna(subset=["load_kw", "pv_kw"])
            .reset_index())

    start = pd.Timestamp(datetime.strptime(date_str, "%Y-%m-%d"),
                         tz="Europe/Kyiv")

    hist = hr[hr["timestamp"] < start]

    if len(hist):
        base = hist.iloc[-1].drop(["timestamp","pv_kw","load_kw"])
    elif len(hr):
        base = hr.iloc[-1].drop(["timestamp","pv_kw","load_kw"])
    else:
        raise ValueError("features_daily.csv порожній – немає даних для інференсу")

    wdf = _forecast(date_str).sort_values("timestamp").reset_index(drop=True)

    rows = []
    for i in range(24):
        ts  = start + timedelta(hours=i)
        vec = _add_time_cols(base, ts)
        for c in ["w_temp","w_cloud","w_swr"]:
            vec[c] = wdf.at[i, c]
        rows.append(vec)

    X_df = pd.DataFrame(rows)

    with open(CONSUMP_PKL, "rb") as f:
        load_obj = pickle.load(f)
    with open(PV_PKL, "rb") as f:
        pv_obj = pickle.load(f)

    X_load = X_df[load_obj["feat"]].values
    X_pv   = X_df[pv_obj  ["feat"]].values

    load_pred = load_obj["model"].predict(X_load)
    pv_pred   = pv_obj  ["model"].predict(X_pv)

    return pd.DataFrame({
        "timestamp": [start + timedelta(hours=i) for i in range(24)],
        "pv_kw":   pv_pred,
        "load_kw": load_pred,
    })
