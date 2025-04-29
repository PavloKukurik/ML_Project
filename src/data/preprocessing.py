import pandas as pd
from pathlib import Path

RAW_DAILY   = Path("data/processed/daily/daily_merged.csv")
RAW_MONTH   = Path("data/processed/monthly/monthly_merged.csv")
OUT_DIR     = Path("../../data/processed")
TZ          = "Europe/Kyiv"

# ---- 1. Мапінг «оригінал → snake_case» ----
COL_MAP = {
    "Time": "timestamp",
    "PV Input Power(W)": "pv_kw",            # /1000
    "Total DC Input Power(W)": "pv_kw",      # альтернатива (беремо, що є)
    "Total Consumption Power(W)": "load_kw", # /1000
    "BMS SOC(%)": "soc_pct",
    "Total Charge/Discharge Power(W)": "batt_power_kw",  # /1000 (+/-)
    "Grid Active Power(W)": "grid_kw",       # /1000, +імпорт/−експорт
    "Grid Feed-in Energy(kWh)": "grid_feed_kwh",
    "Daily Production (Active)(kWh)": "pv_day_kwh",
    "Daily Consumption(kWh)": "load_day_kwh",
    "Total Charging Energy(kWh)": "batt_charge_kwh",
    "Total Discharging Energy(kWh)": "batt_discharge_kwh",
    "Temperature- Battery(℃)": "batt_temp_c",
    "Charge current limit(A)": "charge_lim_a",
    "Discharge Current Limit(A)": "discharge_lim_a",
}

KEEP = set(COL_MAP.keys()) | {"Device Type", "SN"}  # лишаємо id-шники на всяк

def load_and_clean(path: Path, datetime_col: str):
    df = pd.read_csv(path, dtype_backend="pyarrow")
    # 1) вибираємо лише потрібні колонки
    df = df[[c for c in df.columns if c in KEEP]]
    # 2) перейменовуємо
    df = df.rename(columns=COL_MAP)
    # 3) timestamp
    df[datetime_col] = (
        pd.to_datetime(df[datetime_col], errors="coerce")
        .dt.tz_localize(TZ, nonexistent="shift_forward")
    )
    # 4) типи
    num_cols = df.columns.difference([datetime_col, "device_type", "sn"])
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    # 5) одиниці (Вт→кВт)
    w_cols = [c for c in df.columns if c.endswith("_kw")]
    df[w_cols] = df[w_cols].div(1000)
    return df

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # daily 5-хв
    daily = load_and_clean(RAW_DAILY, "timestamp")
    daily.to_parquet(OUT_DIR / "clean_daily.parquet", index=False)

    # monthly (агрегати)
    monthly = pd.read_csv(RAW_MONTH, dtype_backend="pyarrow")
    monthly = monthly.rename(columns={"Time": "date"})
    monthly["date"] = pd.to_datetime(monthly["date"]).dt.date
    monthly.to_parquet(OUT_DIR / "clean_monthly.parquet", index=False)

if __name__ == "__main__":
    main()
