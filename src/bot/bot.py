import os, sys, logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN missing")

ROOT = Path(__file__).parents[1].resolve()
sys.path.append(str(ROOT))

from models.inference                import predict_day
from optimization.schedule_optimizer import optimize_schedule
from data.get_openmeteo_forecast     import fetch_forecast

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привіт! Я бот‑оптимізатор батареї.\n"
        "/optimize – сьогодні\n"
        "/optimize YYYY‑MM‑DD – вибір дати"
    )

async def cmd_optimize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = context.args[0] if context.args else datetime.now().strftime("%Y-%m-%d")

    fp = Path(f"data/weather/forecast_hourly_{date_str}.csv")
    if not fp.exists():
        try:
            fetch_forecast(date_str)
        except Exception as e:
            log.exception(e)
            return await update.message.reply_text(f"❌ Не вдалося отримати прогноз погоди\n{e}")

    df_weather = pd.read_csv(fp)
    df_weather["timestamp"] = pd.to_datetime(df_weather["timestamp"], utc=True)

    try:
        df_pred = predict_day(date_str)
    except Exception as e:
        log.exception(e)
        return await update.message.reply_text(f"❌ Не вдалося побудувати прогноз\n{e}")

    weather = pd.read_csv(f"data/weather/forecast_hourly_{date_str}.csv")
    t_night, t_even, soc_end, imp = optimize_schedule(df_pred, weather)

    total_gen  = df_pred["pv_kw"].sum()
    total_load = df_pred["load_kw"].sum()

    await update.message.reply_text(
        f"⚙️ Оптимізація для {date_str}:\n\n"
        f"🌙 Нічне перемикання: {t_night}\n"
        f"🌇 Вечірнє перемикання: {t_even}\n\n"
        f"🔋 Генерація: {total_gen:.2f}kWh\n"
        f"⚡️ Споживання: {total_load:.2f}kWh\n"

    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("optimize", cmd_optimize))
    log.info("🚀 Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
