# src/bot/telegram_bot.py
"""
Telegram bot для оптимізації роботи батареї.
Commands:
  /start - інформація про бота
  /optimize [YYYY-MM-DD] - дізнатися оптимальні часи перемикання та статистику

Перед запуском задати змінну середовища TELEGRAM_TOKEN з токеном бота.
"""
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from battery_simulator import simulate_soc, load_predictions, SOC_MAX

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Шляхи до даних
PRED_DIR = Path("data/predictions")

# Отримати токен з ENV
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("Set TELEGRAM_TOKEN environment variable")

# Обробник /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Привіт! Я бот для оптимізації роботи батареї.\n"
        "Команди:\n"
        "/start - це повідомлення\n"
        "/optimize [YYYY-MM-DD] - отримати оптимальні часи перемикання для обраної дати\n"
        "Наприклад: /optimize 2025-05-01\n"
    )
    await update.message.reply_text(text)

# Обробник /optimize
async def optimize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Парсимо дату або беремо завтра
    if context.args:
        try:
            date_str = context.args[0]
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            await update.message.reply_text("Невірний формат дати. Використовуйте YYYY-MM-DD.")
            return
    else:
        date = datetime.now().date() + timedelta(days=1)
        date_str = date.isoformat()

    pred_file = PRED_DIR / f"{date_str}_predictions.csv"
    if not pred_file.exists():
        await update.message.reply_text(f"Файл прогнозу не знайдено для {date_str}.")
        return

    # Завантажуємо прогноз
    df_pred = load_predictions(pred_file)
    # Розрахунок загальної генерації та споживання
    total_pv = df_pred['pv_kw'].sum()
    total_load = df_pred['load_kw'].sum()

    # Визначаємо t_evening як останню годину прогнозу (прибл. кінець дня)
    t_evening = df_pred['timestamp'].dt.hour.max()
    # Пошук оптимального t_night (00-05:00, крок 1 год)
    best = None
    for h in range(0, 6):
        sim = simulate_soc(df_pred, t_night=h, t_evening=t_evening)
        imp = sim['grid_import_kw'].sum()
        if best is None or imp < best[2]:
            best = (h, sim['soc_pct'].iloc[-1], imp)

    h_best, soc_end, imp_best = best
    t_night = f"{h_best:02d}:00"
    t_even = f"{t_evening:02d}:00"

    # Формуємо відповідь
    msg = (
        f"Оптимізація для {date_str}:\n"
        f"🔌 Нічне перемикання (на АКБ): {t_night}\n"
        f"🌇 Вечірнє повернення (на мережу): {t_even}\n"
        f"☀️ Прогнозована генерація: {total_pv:.2f} kWh\n"
        f"🏠 Прогнозоване споживання: {total_load:.2f} kWh\n"
        f"🌐 Імпорт з мережі: {imp_best:.2f} kWh\n"
        f"🔋 Кінцевий SOC: {soc_end:.1f}%\n"
    )
    await update.message.reply_text(msg)

# Основний запуск бота
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("optimize", optimize))
    print("Bot started...")
    app.run_polling()
