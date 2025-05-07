import os
from datetime import date, timedelta
import pandas as pd
import requests_cache
from retry_requests import retry
import openmeteo_requests

# ───────────────────────────────────────────────────────────────
# 1. Конфігурація
# ───────────────────────────────────────────────────────────────
LAT, LON = 49.8397, 24.0297  # Львів
TIMEZONE = "Europe/Kyiv"
OUT_PATH = os.path.join("data", "processed", "weather_for_model.csv")
CACHE_DB = ".weather_cache"

# Годинні й добові фічі для моделі
HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "cloud_cover",
    "precipitation_probability",
    "wind_speed_10m",
]
DAILY_VARS = [
    "sunrise",
    "sunset",
    "daylight_duration",
    "uv_index_max",
    "shortwave_radiation_sum",
]

# ───────────────────────────────────────────────────────────────
# 2. Функція завантаження й перезапису
# ───────────────────────────────────────────────────────────────
def fetch_and_save():
    # Налаштування клієнта з кешем і ретраями
    cache_sess = requests_cache.CachedSession(CACHE_DB, expire_after=3600)
    sess = retry(cache_sess, retries=3, backoff_factor=0.3)
    client = openmeteo_requests.Client(session=sess)

    today = date.today()
    tomorrow = today + timedelta(days=1)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": TIMEZONE,
        "start_date": today.isoformat(),
        "end_date": tomorrow.isoformat(),
        "hourly": HOURLY_VARS,
        "daily": DAILY_VARS,
    }

    # Отримуємо відповідь — беремо першу локацію
    resp = client.weather_api(url, params=params)[0]

    # Парсимо hourly з правильним індексом часу
    hr = resp.Hourly()
    start_ts = hr.Time()
    end_ts = hr.TimeEnd()
    interval = hr.Interval()

    times = pd.date_range(
        start=pd.to_datetime(start_ts, unit="s", utc=True)
                  .tz_convert(TIMEZONE).tz_localize(None),
        end=pd.to_datetime(end_ts, unit="s", utc=True)
                  .tz_convert(TIMEZONE).tz_localize(None),
        freq=pd.Timedelta(seconds=interval),
        inclusive="left"
    )
    df_hourly = pd.DataFrame({"time": times})
    for i, var in enumerate(HOURLY_VARS):
        df_hourly[var] = hr.Variables(i).ValuesAsNumpy()

    # Парсимо daily через date_range
    dd = resp.Daily()
    date_list = pd.date_range(start=today, end=tomorrow, freq='D').date
    df_daily = pd.DataFrame({"date": date_list})
    for i, var in enumerate(DAILY_VARS):
        df_daily[var] = dd.Variables(i).ValuesAsNumpy()

    # Merge hourly + daily по даті для кожної години
    df_hourly['date'] = df_hourly['time'].dt.date
    df_merge = df_hourly.merge(df_daily, on='date', how='left')

    # Видаляємо допоміжну колонку та зберігаємо
    df_merge = df_merge.drop(columns=['date'])
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df_merge.to_csv(OUT_PATH, index=False)
    print(f"[✓] Weather for model saved to {OUT_PATH}")

# ───────────────────────────────────────────────────────────────
# 3. Запуск
# ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    fetch_and_save()
