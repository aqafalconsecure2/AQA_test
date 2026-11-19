import logging
import os
import time
import sys
import pyautogui
import glob
import subprocess
import psutil
import random
import win32gui
import win32con

from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMimeData, QUrl

from DownloaderInstl import DownloaderInstl
from AppInstaller import AppInstaller
from FileVersionManager import FileVersionManager
from StartApp import StartApp
from Messages import Messages
from DatabaseReporter import DatabaseReporter
from ReportFolder import ReportFolder


# ===================== НАСТРОЙКИ =====================

# Переменные БД (через ENV безопаснее)
DB_HOST = os.getenv("DB_HOST", "192.168.6.152")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "test")
DB_PASS = os.getenv("DB_PASS", "123")
DB_NAME = os.getenv("DB_NAME", "test_qa")

DB_CHECK_TIMEOUT = 30 
DB_CHECK_INTERVAL = 2  

url = 'https://telegram.org/dl/desktop/win'
TELEGRAM_INSTALLER_PATH = r"C:\Telegram.exe"
TELEGRAM_EXE_PATH = r'C:\Users\user01\AppData\Roaming\Telegram Desktop\Telegram.exe'
TELEGRAM_VERSION_FILE = r'C:\telegram_version.txt'
#FILE_TO_SEND1 = r"C:\files\Telegram.pdf"
#FILE_TO_SEND2 = r"C:\files\file2.pdf"
#FILE_TO_SEND3 = r"C:\files\file3.pdf"
destination = TELEGRAM_INSTALLER_PATH
name_mess = 'Telegram_desk'
install_args = ["/VERYSILENT"]
message = (f"This is test {name_mess}")

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

def check_installer_exists(installer_path):
    if not os.path.exists(installer_path):
        logging.error(f"Файл установщика не найден: {installer_path}")
        return False
    return True

def messeges_telegram():
    logging.info(f"Начало автоматизации {name_mess}")

    time.sleep(2)
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(0.5)
    pyautogui.write("@oleg_ob")
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(0.5)
    message_sender = Messages(message)
    message_sender.run(3)

    logging.info("Сообщения отправлены")

def copy_file_to_clipboard(file_path):
    if not os.path.isfile(file_path):
        raise ValueError(f"Файл не найден: {file_path}")

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    mime_data = QMimeData()
    file_url = QUrl.fromLocalFile(file_path)
    mime_data.setUrls([file_url])

    clipboard = app.clipboard()
    clipboard.setMimeData(mime_data)

    logging.info(f"Файл '{file_path}' скопирован в буфер обмена.")


def send_file(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"Файл для отправки не найден: {file_path}"
        )

    copy_file_to_clipboard(file_path)

    time.sleep(1)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(2)
    pyautogui.press("enter")

    logging.info("Файл отправлен: %s", file_path)


def wait_for_db_record(check, what, timeout=DB_CHECK_TIMEOUT, interval=DB_CHECK_INTERVAL):
    """
    Повторяет check() до первого True или до истечения timeout.
    По таймауту бросает AssertionError.
    """
    deadline = time.monotonic() + timeout
    attempt = 0
 
    while True:
        attempt += 1
 
        if check():
            logging.info("%s найдено в БД (попытка %d)", what, attempt)
            return
 
        if time.monotonic() >= deadline:
            raise AssertionError(
                f"{what} не найдено в БД за {timeout} с ({attempt} попыток)"
            )
 
        logging.info(
            "%s ещё не в БД, повтор через %d с (попытка %d)",
            what, interval, attempt
        )
        time.sleep(interval)


def check_database(message=None, file_name=None):
    if message is None and file_name is None:
        raise ValueError(
            "Необходимо передать message или file_name"
        )

    db = DatabaseReporter(
        DB_HOST,
        DB_PORT,
        DB_USER,
        DB_PASS,
        DB_NAME
    )

    try:
        db.connect()

        # Проверка сообщения
        if message is not None:
            messages = db.fetch_messages(
                """
                SELECT conv_message_body
                FROM conv_messages
                WHERE conv_message_body LIKE %s
                LIMIT 300;
                """,
                (f"%{message}%",)
            )

            if not db.message_exists(messages, message):
                raise AssertionError(
                    f"Сообщение не найдено в БД: {message}"
                )

            logging.info(
                "Сообщение найдено в БД: %s", message
            )

        # Проверка файла
        if file_name is not None:
            files = db.fetch_messages(
                """
                SELECT conv_file_fname
                FROM conv_files
                WHERE conv_file_fname = %s
                LIMIT 300;
                """,
                (file_name,)
            )

            if not db.message_exists(files, file_name):
                raise AssertionError(
                    f"Файл не найден в БД: {file_name}"
                )

            logging.info(
                "Файл найден в БД: %s", file_name
            )

        logging.info("Проверка БД успешно завершена")

    except Exception:
        logging.exception("Ошибка при проверке БД")
        raise

    finally:
        db.close()


def close_app_by_name(process_name):
    
    found = False

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                logging.info(f"Завершаем процесс {process_name} (PID {proc.pid})")
                proc.terminate()
                proc.wait(timeout=10)
                found = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not found:
        logging.info(f"Процесс {process_name} не найден.")


def main():
    logging.info("=== Запуск автоматизации ===")

    try:
         #0. Логирование
        report = ReportFolder("C:/Reports/Desktop_mess/Telegram")
        folder_path = report.create_folder()

        # 1. Скачивание
        downloader = DownloaderInstl(url, destination)

        if not downloader.attempt_download():
            logging.critical("Загрузка не удалась. Остановка процесса.")
            return

        time.sleep(3)
        
        # 2. Установка      
        if check_installer_exists(TELEGRAM_INSTALLER_PATH):

            installer = AppInstaller(
                installer_path=TELEGRAM_INSTALLER_PATH,
                install_args=install_args
            )

            success = installer.install(timeout=300)

            if not success:
                logging.critical(f"Установка {name_mess} завершилась с ошибкой. Остановка процесса.")
                return

            # -------- Проверка появления exe --------
            timeout = 60
            interval = 5
            elapsed = 0

            logging.info(f"Ожидание появления {name_mess}.exe после установки...")

            start_time = time.time()

            while not os.path.exists(TELEGRAM_EXE_PATH):
                elapsed = time.time() - start_time

                if elapsed >= timeout:
                    break

                time.sleep(interval)

            if os.path.exists(TELEGRAM_EXE_PATH):
                logging.info(f"{name_mess} успешно установлен: {TELEGRAM_EXE_PATH}")
            else:
                logging.error(f"После установки {name_mess}.exe не найден! Проверьте установщик или права доступа.")
                
                return

        else:
            logging.error(f"Установочный файл не найден: {TELEGRAM_INSTALLER_PATH}")
            return

        # 3. Версия
        if os.path.exists(TELEGRAM_EXE_PATH):
            version_manager = FileVersionManager(
                TELEGRAM_EXE_PATH,
                TELEGRAM_VERSION_FILE
            )
            version_manager.process_version()
        else:
            logging.error(f"{name_mess}.exe не найден после установки")
            return

        # 4. Запуск
        telegram = StartApp(TELEGRAM_EXE_PATH)
        telegram.run()
        time.sleep(2)

        # 5. Отправка сообщений
        messeges_telegram()

        # 6. Отправка файла
        file_name = create_test_file(
                            folder=r"C:\files\Desktop_mess",
                            prefix="Telegram_desk",
                            extension=".pdf",
                            size_bytes= 1 * 160 * 126
                        )
                
        FILE_TO_SEND = fr"C:\files\Desktop_mess\{file_name}"

        for file in [FILE_TO_SEND]:
            send_file(file)
        time.sleep(3)
        
        # 7. Проверка БД
        check_database(message, file_name)
        
        ok = True

        #8. Закрытие приложения
        #close_app_by_name("Telegram.exe")

        #logging.info("=== Автоматизация завершена успешно ===")

    except Exception:
        logging.exception("Критическая ошибка в процессе выполнения")
        raise

    finally:
        try:
            close_app_by_name("Telegram.exe")
        except Exception:
            logging.exception("Не удалось корректно закрыть Telegram.exe")
 
        if ok:
            logging.info("=== Автоматизация завершена успешно ===")
        else:
            logging.error("=== Автоматизация завершена с ошибкой ===")
 


if __name__ == "__main__":
    main()
