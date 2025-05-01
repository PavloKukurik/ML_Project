import json, os, datetime as dt, pathlib
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)

load_dotenv()
BOT_TOKEN       = os.getenv("BOT_TOKEN")
DEFAULT_CHAT_ID = int(os.getenv("DEFAULT_CHAT_ID", "0"))

RESULTS_DIR = pathlib.Path("results")

def latest_result() -> dict | None:
    """Повертає найсвіжіший JSON-результат оптимізатора."""
    files = sorted(RESULTS_DIR.glob("schedule_*.json"))
    if not files:
        return None
    with files[-1].open(encoding="utf-8") as fp:
        return json.load(fp)

async def send_recommendation(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Надсилає повідомлення з t_switch."""
    data = latest_result()
    if not data:
        await ctx.bot.send_message(chat_id, "🤔 Результат оптимізації ще не готовий")
        return

    t_switch = dt.datetime.fromisoformat(data["t_switch"]).strftime("%H:%M")
    soc      = data.get("soc_end", "–")
    msg = (
        f"🔋 Рекомендую перемикнутися **о {t_switch}**\n"
        f"Очікуваний SOC наприкінці дня: *{soc} %*"
    )
    await ctx.bot.send_message(chat_id, msg, parse_mode="Markdown")

# ---------- handlers ----------
async def today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # повідомляємо користувача
    await ctx.bot.send_message(
        update.effective_chat.id,
        "⏳ Запускаю оптимізацію, зачекай…"
    )

    # запускаємо pipeline
    from .scheduler import run_pipeline
    try:
        await run_pipeline()          # ~30-60 с, формує schedule_*.json
    except Exception as e:
        await ctx.bot.send_message(
            update.effective_chat.id,
            f"❌ Помилка pipeline: {e}"
        )
        return                        # не слати старий результат

    # надсилаємо свіжу рекомендацію
    await send_recommendation(ctx, update.effective_chat.id)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ctx.bot.send_message(
        update.effective_chat.id,
        "Привіт! Команда /today покаже оптимальний час перемикання."
    )

def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    return app

if __name__ == "__main__":
    app = build_app()
    app.run_polling(allowed_updates=Update.ALL_TYPES)
