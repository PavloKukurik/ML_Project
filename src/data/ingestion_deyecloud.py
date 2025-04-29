import os
import time
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

def init_driver(download_dir: str):
    options = webdriver.ChromeOptions()
    prefs = {"download.default_directory": os.path.abspath(download_dir)}
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--start-maximized")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def go_to_previous_day(driver, wait):
    """
    Перемикаємо дату на попередню, клікаючи по стрілці поруч із датою (клас iconarrow-l fsUsePar).
    """
    try:
        prev_btn = wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "div.iconarrow-l.fsUsePar"
        )))
        # JS-клік, щоб уникнути 'not clickable'
        driver.execute_script("arguments[0].click();", prev_btn)
        print("  ✔ Clicked previous-day arrow")
        time.sleep(5)  # чекаємо, поки підвантажаться дані
    except Exception as e:
        print(f"  ✖ Failed to click previous-day arrow: {e}")

def download_data(driver, inverter_url: str, download_dir: str, days: int):
    wait = WebDriverWait(driver, 20)

    # Відкриваємо сторінку інвертора
    driver.get(inverter_url)
    time.sleep(5)

    for i in range(days):
        print(f"Day {i+1}/{days} — exporting...")

        # 1) Експорт даних
        try:
            export_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.export-btn")))
            export_btn.click()
            print("  ✔ Export clicked")
            time.sleep(8)  # чекаємо, коли файл зкачається
        except Exception as e:
            print(f"  ✖ Export failed: {e}")

        # 2) Перемикаємо попередній день
        go_to_previous_day(driver, wait)

def main():
    load_dotenv()
    download_dir = "data/raw"
    os.makedirs(download_dir, exist_ok=True)

    inverter_url = "https://www.deyecloud.com/station/device?id=61156646&hasSetPrice=false"
    days_to_download = 180  # останні 6 місяців

    driver = init_driver(download_dir)
    try:
        driver.get(inverter_url)
        input("🔑 Будь ласка, логініться вручну в браузері, потім натисніть ENTER…")
        download_data(driver, inverter_url, download_dir, days_to_download)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
