from pathlib import Path
import glob, math, pandas as pd, numpy as np

PROC_DIR = Path("data/processed")
WEATH_DIR= Path("data/weather")
OUT_CSV  = PROC_DIR / "features_daily.csv"

INV_FILE = PROC_DIR / "clean_daily.csv"

inv = pd.read_csv(INV_FILE)
inv["timestamp"] = pd.to_datetime(inv["timestamp"], utc=True, errors="coerce")
inv = inv.dropna(subset=["timestamp"])
inv = inv.rename(columns={"AC_Power(kW)": "load_kw",
                          "PV_Power(kW)": "pv_kw"})
inv["timestamp"] = inv["timestamp"].dt.tz_convert("Europe/Kyiv")

inv = (inv.set_index("timestamp")
          .resample("1h")
          .mean()                 
          .dropna(subset=["load_kw","pv_kw"])
          .reset_index())

inv["load_kw"] *= 1.0
inv["pv_kw"]   *= 1.0

weather_files = glob.glob(str(WEATH_DIR / "history_hourly_*.csv"))
weather = (pd.concat((pd.read_csv(f) for f in weather_files), ignore_index=True)
             .rename(columns={"time": "timestamp"}))
weather["timestamp"] = pd.to_datetime(weather["timestamp"], utc=True)
weather["timestamp"] = weather["timestamp"].dt.tz_convert("Europe/Kyiv")
weather = weather.sort_values("timestamp")

weather = weather.rename(columns={
    "temperature_2m":      "w_temp",
    "cloud_cover":         "w_cloud",
    "shortwave_radiation": "w_swr"
})[["timestamp","w_temp","w_cloud","w_swr"]]


df = pd.merge_asof(inv.sort_values("timestamp"),
                   weather, on="timestamp",
                   tolerance=pd.Timedelta("30min"))

ts = df["timestamp"].dt
df["hour"]      = ts.hour
df["dow"]       = ts.dayofweek
df["month"]     = ts.month
df["hour_sin"]  = np.sin(2*np.pi*df["hour"]/24)
df["hour_cos"]  = np.cos(2*np.pi*df["hour"]/24)
df["dow_sin"]   = np.sin(2*np.pi*df["dow"]/7)
df["dow_cos"]   = np.cos(2*np.pi*df["dow"]/7)

df[["w_temp","w_cloud","w_swr"]] = (
    df[["w_temp","w_cloud","w_swr"]]
      .interpolate(limit_direction="both")
)

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT_CSV, index=False)
print(f"[✅] features_daily.csv saved → {OUT_CSV}   ({len(df)} rows, {df.shape[1]} cols)")
