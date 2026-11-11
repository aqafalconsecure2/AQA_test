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
DB_HOST = os.getenv("DB_HOST", "192.168.6.169")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "1234")
DB_NAME = os.getenv("DB_NAME", "test_03_04")

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

    # === Поиск и клик по иконке ===
    for attempt in range(3):
        search_field = pyautogui.locateCenterOnScreen(
            'screens/telegram_icon.png',
            confidence=0.7
        )

        if search_field:
            pyautogui.click(search_field)
            logging.info("Telegram открыт")
            break

        logging.warning(f"Telegram icon не найден. Попытка {attempt + 1}")
        time.sleep(2)
    else:
        logging.error("Telegram icon не найден после retry")
        return

    time.sleep(2)

    # === Поиск поля ввода ===
    message_field = pyautogui.locateCenterOnScreen(
        'screens/telegram_field.png',
        confidence=0.71
    )

    if not message_field:
        logging.error("Поле ввода сообщения не найдено")
        return

    pyautogui.click(message_field)
    time.sleep(1)

    message_sender = Messages(f"This is test {name_mess}")
    message_sender.run(5)

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
    if not os.path.exists(file_path):
        logging.error(f"Файл для отправки не найден: {file_path}")
        return
    try:
        copy_file_to_clipboard(file_path)
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1)
        pyautogui.press('enter')
        logging.info(f"Файл '{file_path}' отправлен")
    except Exception:
        logging.exception(f"Ошибка при отправке файла '{file_path}'")


def check_database(file_name):
    try:
        db = DatabaseReporter(DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME)
        db.connect()

        # Проверка сообщений
        messages = db.fetch_messages(
            'SELECT conv_message_body FROM conv_messages LIMIT 500;'
        )

        if db.message_exists(messages, f"This is test {name_mess}"):
            logging.info('Сообщение найдено в БД')
        else:
            logging.warning('Сообщение не найдено в БД')

        # Проверка файлов
        files = db.fetch_messages(
            "SELECT conv_file_fname FROM conv_files LIMIT 100;"
        )

        if db.message_exists(files, file_name):
            logging.info('Файл найден в БД')
        else:
            logging.warning('Файл не найден в БД')

        db.close()

    except Exception:
        logging.exception("Ошибка при работе с БД")

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
                            size_bytes= 1 * 16 * 16
                        )
                
        FILE_TO_SEND = fr"C:\files\Desktop_mess\{file_name}"

        for file in [FILE_TO_SEND]:
            send_file(file)
        time.sleep(1)
        
        # 7. Проверка БД
        check_database(file_name)

        #8. Закрытие приложения
        close_app_by_name("Telegram.exe")

        logging.info("=== Автоматизация завершена успешно ===")

    except Exception:
        logging.exception("Критическая ошибка в процессе выполнения")


if __name__ == "__main__":
    main()
