"""
Завантажує історичні погодинні + денні дані Open-Meteo
(Львів, останні 100 днів) і зберігає у data/weather/.
"""

import openmeteo_requests, requests_cache, pandas as pd
from retry_requests import retry
from datetime import date, timedelta
import os, pathlib

# → Локація
LAT, LON = 49.8397, 24.0297
# → Діапазон: ще на день раніше, щоб не було «висячих» годин
END_DATE   = date(2025, 5, 7)
START_DATE = END_DATE - timedelta(days=100)

OUT_DIR = pathlib.Path("data/weather")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ↘️ клієнт із кешем + retry
cache = requests_cache.CachedSession(".cache", expire_after=3600)
session = retry(cache, retries=5, backoff_factor=0.2)
om     = openmeteo_requests.Client(session=session)

url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
params = {
    "latitude": LAT,
    "longitude": LON,
    "start_date": "2025-01-30",
    "end_date":  "2025-04-30",
    "timezone":   "auto",
    # --- погодинні фічі (додали shortwave_radiation) ---
    "hourly": [
        "temperature_2m", "relative_humidity_2m", "apparent_temperature",
        "precipitation_probability", "cloud_cover", "wind_speed_10m",
        "shortwave_radiation"
    ],
    # --- денні (додали sunrise / sunset / weather_code) ---
    "daily": [
        "sunrise", "sunset", "daylight_duration",
        "uv_index_max", "shortwave_radiation_sum",
        "weather_code"
    ],
}

response = om.weather_api(url, params=params)[0]

# ----------  Hourly ----------
h = response.Hourly()
hourly_df = pd.DataFrame({
    "time": pd.date_range(
        pd.to_datetime(h.Time(),    unit="s", utc=True),
        pd.to_datetime(h.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=h.Interval()),
        inclusive="left"
    ),
    "temperature_2m":           h.Variables(0).ValuesAsNumpy(),
    "relative_humidity_2m":     h.Variables(1).ValuesAsNumpy(),
    "apparent_temperature":     h.Variables(2).ValuesAsNumpy(),
    "precipitation_probability":h.Variables(3).ValuesAsNumpy(),
    "cloud_cover":              h.Variables(4).ValuesAsNumpy(),
    "wind_speed_10m":           h.Variables(5).ValuesAsNumpy(),
    "shortwave_radiation":      h.Variables(6).ValuesAsNumpy()
})
hourly_fp = OUT_DIR / f"history_hourly_{START_DATE}_to_{END_DATE}.csv"
hourly_df.to_csv(hourly_fp, index=False)

# ----------  Daily ----------
d = response.Daily()
daily_df = pd.DataFrame({
    "date": pd.date_range(
        pd.to_datetime(d.Time(),    unit="s", utc=True),
        pd.to_datetime(d.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=d.Interval()),
        inclusive="left"
    ).date,
    "sunrise":                  pd.to_datetime(d.Variables(0).ValuesInt64AsNumpy(), unit="s", utc=True),
    "sunset":                   pd.to_datetime(d.Variables(1).ValuesInt64AsNumpy(), unit="s", utc=True),
    "daylight_duration":        d.Variables(2).ValuesAsNumpy(),
    "uv_index_max":             d.Variables(3).ValuesAsNumpy(),
    "shortwave_radiation_sum":  d.Variables(4).ValuesAsNumpy(),
    "weather_code":             d.Variables(5).ValuesAsNumpy()
})
daily_fp = OUT_DIR / f"history_daily_{START_DATE}_to_{END_DATE}.csv"
daily_df.to_csv(daily_fp, index=False)

print(f"[✅] Saved:\n • {hourly_fp}\n • {daily_fp}")

def main():
    """Щоб import … as main не падав, якщо ви захочете повернути погоду."""
    pass

