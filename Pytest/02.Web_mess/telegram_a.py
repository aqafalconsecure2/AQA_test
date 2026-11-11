import logging
import os
import time
import sys
import pyautogui
import traceback

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
name_mess = 'Telegram_a'


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

def open_telegram(profile_path: str, profile_name: str = "Default", url: str = "https://web.telegram.org/a/", timeout: int = 15):
    
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
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '[alt="Олег"]'))
                )
                chat.click()
                logging.info("Чат открыт")
                break

            except StaleElementReferenceException:
                logging.warning(
                    f"Чат обновился в DOM, попытка {attempt + 1}/5"
                )
        else:
            raise Exception("Не удалось кликнуть по чату")        

        
        for attempt in range(5):
            try:
                chat.click()
                logging.info("Чат открыт")

                place = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable(
                        (By.ID, "editable-message-text")
                    )
                )

                place.send_keys(f"Test message {name_mess}")
                logging.info("Сообщение введено")

                place.send_keys(Keys.ENTER)
                logging.info("Сообщение отправлено")

                break

            except StaleElementReferenceException:
                logging.warning(
                    f"Чат обновился в DOM, попытка {attempt + 1}/5"
                )


        files1 = driver.find_element(By.CSS_SELECTOR, ".icon.icon-attach")
        files1.click()
        files2 = driver.find_element(By.CSS_SELECTOR, "#attach-menu-controls > div > div:nth-child(2)")
        files2.click()
        time.sleep(1)
        file_name = create_test_file(
                    folder=r"C:\files\Web_mess",
                    prefix="Telegram_a",
                    extension=".pdf",
                    size_bytes= 1 * 162 * 190
                )
        pyautogui.write(f'C:\\files\\Web_mess\\{file_name}')
        time.sleep(1)
        pyautogui.press('enter')
        time.sleep(2)        
        logging.info("Файл загружен")             
        press_file = driver.find_element(By.CSS_SELECTOR, '[class="icon icon-new-send Xm7vhWAh"]')
        press_file.click()
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
            'SELECT conv_message_body FROM conv_messages LIMIT 500;'
        )

        if db.message_exists(messages, f'Test message {name_mess}'):
            logging.info('Сообщение найдено в БД')
        else:
            logging.warning('Сообщение не найдено в БД')

        # Проверка файлов
        files = db.fetch_messages(
            "SELECT conv_file_fname FROM conv_files LIMIT 100;"
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
        report = ReportFolder("C:/Reports/Web_mess/Telegram_a")
        folder_path = report.create_folder()

        driver, wait, file_name = open_telegram(profile_path)

        time.sleep(3)        
        #1.
        check_database(file_name)
    except Exception:
        logging.exception("Критическая ошибка в процессе выполнения")


if __name__ == "__main__":
    main()
