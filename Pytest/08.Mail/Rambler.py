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

from Messages import Messages
from DatabaseReporter import DatabaseReporter
from ReportFolder import ReportFolder


# ===================== НАСТРОЙКИ =====================

# Переменные БД (через ENV безопаснее)
DB_HOST = os.getenv("DB_HOST", "10.10.11.111")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "test0502")

profile_path = r"C:\ChromeSeleniumProfile"

#file = "C:\files\Telegramweba.pdf"
#FILE_TO_SEND2 = r"C:\files\file2.pdf"
#FILE_TO_SEND3 = r"C:\files\file3.pdf"
name_mess = 'Rambler_mail'


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

def open_telegram(profile_path: str, profile_name: str = "Default", url: str = "https://mail.rambler.ru/", timeout: int = 15):
    
    try:
        logging.info("Запуск браузера")

        options = Options()
        options.add_argument(f"user-data-dir={profile_path}")
        options.add_argument(f"--profile-directory={profile_name}")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, timeout)

        logging.info(f"Открываем {name_mess} Web")
        driver.get(url)

        driver.implicitly_wait(5)

        logging.info(f"{name_mess} успешно открыт")       
        

        for attempt in range(5):
            try:
                chat = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='root.header.compose']"))
                )
                chat.click()
                logging.info("Письмо открыто")
                break

            except StaleElementReferenceException:
                logging.warning(
                    f"Чат обновился в DOM, попытка {attempt + 1}/5"
                )
        else:
            raise Exception("Не удалось кликнуть по чату")
        

        for attempt in range(5):
            try:
                place = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@data-testid='root.compose.fields.to.input']"))
                )
                place.click()
                logging.info("Поле ввода открыто")
                place.send_keys(f"123@mail.ru")
                logging.info("Email заполнен")
                break

            except StaleElementReferenceException:
                logging.warning(
                    f"Чат обновился в DOM, попытка {attempt + 1}/5"
                )
        else:
            raise Exception("Не удалось отправить сообщение") 
                       

        for attempt in range(5):
            try:
                place = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//iframe[@data-testid='root.compose.fields.message.iframe']"))
                )
                place.click()
                logging.info("Поле ввода открыто")
                place.send_keys(f"Test message {name_mess}")
                logging.info("Сообщение введено")                
                break

            except StaleElementReferenceException:
                logging.warning(
                    f"Чат обновился в DOM, попытка {attempt + 1}/5"
                )
        else:
            raise Exception("Не удалось отправить сообщение")
        
        for attempt in range(5):
            try:
                files1 = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='file' and @multiple]"))
                )
                files1.click()              
                break

            except StaleElementReferenceException:
                logging.warning(
                    f"Чат обновился в DOM, попытка {attempt + 1}/5"
                )
        else:
            raise Exception("Не удалось открыть скрепку")        

        time.sleep(1)

        file_name = create_test_file(
                    folder=r"C:\files\Mail",
                    prefix="Rambler",
                    extension=".pdf",
                    size_bytes= 1 * 640 * 199
                )
        time.sleep(4)
        file_path = rf"C:\files\Mail\{file_name}"
        files1.send_keys(file_path)
        time.sleep(2)        
        logging.info("Файл загружен")   
        
        for attempt in range(5):
            try:
                press_file_ = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='root.compose.footer.send']"))
                )
                press_file_.click()
                logging.info("Сообщение отравленно")
                break

            except StaleElementReferenceException:
                logging.warning(
                    f"Чат обновился в DOM, попытка {attempt + 1}/5"
                )
        else:
            raise Exception("Не удалось отправить файл")      
           
        time.sleep(2)  

        return driver, wait, file_name

    except Exception as e:
        logging.error(f"Ошибка при запуске {name_mess}")
        logging.error(traceback.format_exc())
        raise

def check_database(filename):
    try:
        db = DatabaseReporter(DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME)
        db.connect()

        # Проверка сообщений
        messages = db.fetch_messages(
            'SELECT web_mail_body FROM web_mails LIMIT 500;'
        )

        if db.message_exists(messages, f'Test message {name_mess}'):
            logging.info('Сообщение найдено в БД')
        else:
            logging.warning('Сообщение не найдено в БД')

        # Проверка файлов
        files = db.fetch_messages(
            "SELECT web_file_fname FROM web_files LIMIT 100;"
        )

        if db.message_exists(files, filename):
            logging.info('Файл найден в БД')
        else:
            logging.warning('Файл не найден в БД')

        db.close()

    except Exception:
        logging.exception("Ошибка при работе с БД")
    
def main():
    logging.info("=== Запуск автоматизации ===")

    try:
         #0. Логирование
        report = ReportFolder("C:/Reports/Mail/Rambler")
        folder_path = report.create_folder()

        driver, wait, file_name = open_telegram(profile_path)

        time.sleep(3)

        #1.
        check_database(file_name)        

    except Exception:
        logging.exception("Критическая ошибка в процессе выполнения")




if __name__ == "__main__":
    main()
