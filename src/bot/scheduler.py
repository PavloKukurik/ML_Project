import asyncio
import os
import datetime as dt
import pathlib
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from telegram.ext import Application

# імпорт функцій бота
from .bot import build_app, send_recommendation

# ────────────────────────────────────────
# 1. Константи та змінні середовища
# ────────────────────────────────────────
load_dotenv()
DEFAULT_CHAT_ID = int(os.getenv("DEFAULT_CHAT_ID", "0"))

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]   # <repo root>

DAILY_SCRIPT   = PROJECT_ROOT / "scripts" / "daily_job.bat"        # твій shell-пайплайн
RESULTS_DIR    = PROJECT_ROOT / "results"

# ────────────────────────────────────────
# 2. Запуск основного пайплайну (ingestion → optimizer)
# ────────────────────────────────────────
async def run_pipeline() -> None:
    """
    Асинхронно запускає scripts/daily_job.sh.
    При помилці виводить код завершення в консоль.
    """
    if not DAILY_SCRIPT.exists():
        print(f"[WARN] {DAILY_SCRIPT} не знайдено – пропускаю pipeline")
        return

    proc = await asyncio.create_subprocess_exec(
        DAILY_SCRIPT,
        cwd=PROJECT_ROOT,                 # ← запускаємо .bat із кореня
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    stdout, _ = await proc.communicate()
    import locale
    encoding = locale.getpreferredencoding(False)
    print(stdout.decode(encoding, errors="replace").strip())
    if proc.returncode == 0:
        print("[✓] pipeline finished OK")
    else:
        print(f"[ERROR] pipeline exited with code {proc.returncode}")

# ────────────────────────────────────────
# 3. Джоба «pipeline + повідомлення»
# ────────────────────────────────────────
async def daily_job(app: Application) -> None:
    # ➊ запускаємо pipeline
    await run_pipeline()

    # ➋ після цього відправляємо рекомендацію
    async with app:
        fake_ctx = type("Ctx", (), {"bot": app.bot})
        await send_recommendation(fake_ctx, DEFAULT_CHAT_ID)

# ────────────────────────────────────────
# 4. Scheduler + нескінченний цикл
# ────────────────────────────────────────
async def main():
    app = build_app()

    scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(
        daily_job,
        "cron",
        hour=6, minute=5,          # щодня о 06:05
        args=[app],
        name="daily_pipeline_and_notify"
    )
    scheduler.start()

    print("Scheduler started — Ctrl+C to stop")
    await asyncio.Event().wait()   # тримаємо цикл живим

if __name__ == "__main__":
    asyncio.run(main())
