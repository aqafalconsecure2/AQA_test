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
from DatabaseReporter import DatabaseReporter
from ReportFolder import ReportFolder


# ===================== НАСТРОЙКИ =====================

# Переменные БД (через ENV безопаснее)
DB_HOST = os.getenv("DB_HOST", "192.168.6.169")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "1234")
DB_NAME = os.getenv("DB_NAME", "test_03_04")

url = 'https://webdav.yandex.ru/share/dist/res/YandexDisk4Setup.exe'
YANDEXDISK_INSTALLER_PATH = r"C:\YandexDiskSetup.exe"
YANDEXDISK_EXE_PATH = r'C:\Program Files\Yandex\YandexDisk4\YandexDisk4.exe'
YANDEXDISK_VERSION_FILE = r'C:\YandexDisk_version.txt'
#FILE_TO_SEND2 = r"C:\files\file2.pdf"
#FILE_TO_SEND3 = r"C:\files\file3.pdf"
destination = YANDEXDISK_INSTALLER_PATH
name_mess = 'YandexDisk'
install_args = ["/qn", "/quiet"]


# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================

def check_installer_exists(installer_path):
    if not os.path.exists(installer_path):
        logging.error(f"Файл установщика не найден: {installer_path}")
        return False
    return True

def install_with_force_close(installer_path, wait_seconds=10):
    """
    Запускает установщик, ждёт указанное время и завершает его процесс.
    """

    logging.info(f"Запуск установщика: {installer_path}")

    process = subprocess.Popen(
        installer_path,
        shell=True
    )

    logging.info(
        f"Установщик запущен PID={process.pid}. "
        f"Ожидание {wait_seconds} секунд..."
    )

    time.sleep(wait_seconds)

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

def open_folder_focus(folder_path):
    """
    Открывает папку Windows Explorer и переводит окно в фокус.
    """
    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"Папка не найдена: {folder}")

    os.startfile(folder)

    time.sleep(1)  # ждём запуска проводника

    folder_name = folder.name

    def enum_windows(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if folder_name in title:
                result.append(hwnd)

    windows = []
    win32gui.EnumWindows(enum_windows, windows)

    if windows:
        hwnd = windows[0]

        # восстановить окно, если свернуто
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # установить фокус
        win32gui.SetForegroundWindow(hwnd)

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
        #pyautogui.press('enter')
        logging.info(f"Файл '{file_path}' отправлен")
    except Exception:
        logging.exception(f"Ошибка при отправке файла '{file_path}'")


def check_database(file_name):
    try:
        db = DatabaseReporter(DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME)
        db.connect()

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
        report = ReportFolder("C:/Reports/Desk_cloude/YandexDisk")
        folder_path = report.create_folder()

        # 1. Скачивание
        downloader = DownloaderInstl(url, destination)

        if not downloader.attempt_download():
            logging.critical("Загрузка не удалась. Остановка процесса.")
            return

        time.sleep(3)
        
        # 2. Установка 
        install_with_force_close(
            YANDEXDISK_INSTALLER_PATH,
            wait_seconds=10
        )
        #time.sleep(5)
        close_app_by_name("YandexDiskSetup.exe")

        # 3. Версия
        if os.path.exists(YANDEXDISK_EXE_PATH):
            version_manager = FileVersionManager(
                YANDEXDISK_EXE_PATH,
                YANDEXDISK_VERSION_FILE
            )
            version_manager.process_version()
        else:
            logging.error(f"{name_mess}.exe не найден после установки")
            return

        # 4. Запуск
        YandexDisk = StartApp(YANDEXDISK_EXE_PATH)
        YandexDisk.run()
        time.sleep(2)

        # 4. Открытие папки облака
        open_folder_focus(r"C:\Users\user01\Yandex.Disk-akapobesy")
        time.sleep(2)

        # 5. Копирование пути к файлу
        file_name = create_test_file(
                    folder=r"C:\files\Desk_cloude",
                    prefix="Yadisk",
                    extension=".pdf",
                    size_bytes= 1 * 16 * 16
                )
        
        FILE_TO_SEND = fr"C:\files\Desk_cloude\{file_name}"

        # 6. Отправка файла
        for file in [FILE_TO_SEND]:
            send_file(file)
        time.sleep(1)
        
        # 7. Проверка БД
        check_database(file_name)

        #8. Закрытие приложения
        close_app_by_name("YandexDisk4.exe")

        logging.info("=== Автоматизация завершена успешно ===")

    except Exception:
        logging.exception("Критическая ошибка в процессе выполнения")


if __name__ == "__main__":
    main()
