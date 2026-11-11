import logging
import os
import time
import sys
import pyautogui
import traceback
import random

from pathlib import Path
from datetime import datetime


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException


from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMimeData, QUrl

from DatabaseReporter import DatabaseReporter
from ReportFolder import ReportFolder


# ===================== НАСТРОЙКИ =====================

# Переменные БД (через ENV безопаснее)
DB_HOST = os.getenv("DB_HOST", "10.10.11.111")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "1234")
DB_NAME = os.getenv("DB_NAME", "db01")

profile_path = r"C:\ChromeSeleniumProfile"

#file = "C:\files\Telegramweba.pdf"
#FILE_TO_SEND2 = r"C:\files\file2.pdf"
#FILE_TO_SEND3 = r"C:\files\file3.pdf"
name_mess = 'Googledisk_web'


# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================

def create_test_file(
    folder: str,
    prefix: str = "TestFile",
    extension: str = ".txt",
    size_bytes: int = 1024
):
    Path(folder).mkdir(parents=True, exist_ok=True)

    filename = (
        f"{prefix}_"
        f"{datetime.now():%Y%m%d_%H%M%S}_"
        f"{random.randint(1000, 9999)}"
        f"{extension}"
    )

    file_path = Path(folder) / filename

    with file_path.open("wb") as f:
        f.write(os.urandom(size_bytes))

    return filename



def open_telegram(profile_path: str, profile_name: str = "Default", url: str = "https://drive.google.com/drive", timeout: int = 15):
    
    try:
        logging.info("Запуск браузера")

        options = Options()
        options.add_argument(f"user-data-dir={profile_path}")
        options.add_argument(f"--profile-directory={profile_name}")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, timeout)

        logging.info(f"Открываем {name_mess}")
        driver.get(url)

        driver.implicitly_wait(5)

        files1 = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@aria-label='Создать']")
            )
        )
        files1.click()
        files2 = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//li[@role='menuitem'][.//span[normalize-space()='Загрузить файл']]")
            )
        )
        files2.click() 
        time.sleep(1)
        file_name = create_test_file(
            folder=r"C:\files",
            prefix="Googledisk_web",
            extension=".pdf",
            size_bytes= 1 * 16 * 16
        )

        pyautogui.write(f"C:\\files\\{file_name}")
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(2)        
        logging.info("Файл загружен")

        return driver, wait, file_name

    except Exception as e:
        logging.error(f"Ошибка при запуске {name_mess}")
        logging.error(traceback.format_exc())
        raise

def check_database(file_name):
    try:
        db = DatabaseReporter(DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME)
        db.connect() 

        # Проверка файлов
        files = db.fetch_messages(
            "SELECT cloud_file_fname FROM cloud_files LIMIT 100;"
        )

        if db.message_exists(files, file_name):
            logging.info(f'Файл {file_name} найден в БД')
        else:
            logging.warning(f'Файл {file_name} не найден в БД')

        db.close()

    except Exception:
        logging.exception("Ошибка при работе с БД")

def main():
    logging.info("=== Запуск автоматизации ===")

    try:
        #1. Логирование
        report = ReportFolder("C:/Reports/Web_cloude/Googledisk_web")
        folder_path = report.create_folder()

        driver, wait, file_name = open_telegram(profile_path)

        time.sleep(3)   

        #1.Проверка БД
        check_database(file_name)

    except Exception:
        logging.exception("Критическая ошибка в процессе выполнения")


if __name__ == "__main__":
    main()
