import logging
import os
import time
import subprocess
import psutil

from pathlib import Path
from datetime import datetime

from DatabaseReporter import DatabaseReporter
from ReportFolder import ReportFolder


# ===================== НАСТРОЙКИ =====================

# Переменные БД (через ENV безопаснее)
DB_HOST = os.getenv("DB_HOST", "10.10.11.111")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "test0502")


#name_mess = 'Gmail_mail'

BROWSERS = {
    "chrome": {
        "path": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "process": "chrome.exe",
        "url": "https://onliner.by",
    },

    "mozilla": {
        "path": r"C:\Program Files\Mozilla Firefox\firefox.exe",
        "process": "firefox.exe",
        "url": "https://21vek.by",
    },

    "opera": {
        "path": r"C:\Users\user01\AppData\Local\Programs\Opera\opera.exe",
        "process": "opera.exe",
        "url": "https://github.com",
    },

    "yandex": {
        "path": r"C:\Program Files\Yandex\YandexBrowser\Application\browser.exe",
        "process": "browser.exe",
        "url": "https://ya.ru",
    },

    "chromium": {
        "path": r"C:\Users\user01\Downloads\chrome-win\chrome.exe",
        "process": "chrome.exe",
        "url": "https://google.com",
    },

    "edge": {
        "path": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "process": "msedge.exe",
        "url": "https://mail.ru",
    }
}

# Сколько секунд браузер будет открыт
BROWSER_OPEN_TIME = 10

# Пауза между браузерами
DELAY_BETWEEN = 2


# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================

def kill_processes(process_name):
    logging.info(f"Закрываю процессы: {process_name}")

    killed = 0

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info["name"]

            if name and name.lower() == process_name.lower():
                logging.info(
                    f"Завершаю {name}, PID={proc.info['pid']}"
                )

                proc.kill()
                killed += 1

        except psutil.NoSuchProcess:
            pass

        except psutil.AccessDenied:
            logging.warning(
                f"Нет доступа к PID={proc.info['pid']}"
            )

    logging.info(
        f"Завершено процессов {process_name}: {killed}"
    )

def launch_browser(name, path, process_name, url):
    path = os.path.expandvars(path)

    if not os.path.isfile(path):
        logging.warning(
            f"{name}: браузер не найден: {path}"
        )
        return

    logging.info(
        f"[+] Открываю: {name}, URL: {url}"
    )

    process = subprocess.Popen([
        path,
        "--new-window",
        url
    ])

    logging.info(
        f"{name}: браузер запущен. PID={process.pid}"
    )

    logging.info(
        f"{name}: ждём {BROWSER_OPEN_TIME} секунд..."
    )

    time.sleep(BROWSER_OPEN_TIME)

    # Закрываем ВСЕ процессы этого браузера
    kill_processes(process_name)

    # Небольшая пауза после закрытия
    time.sleep(2)

    # Проверяем, что процессы действительно ушли
    remaining = [
        proc.info["pid"]
        for proc in psutil.process_iter(["pid", "name"])
        if proc.info["name"]
        and proc.info["name"].lower() == process_name.lower()
    ]

    if remaining:
        logging.warning(
            f"{name}: процессы всё ещё работают: {remaining}"
        )
    else:
        logging.info(
            f"{name}: полностью закрыт"
        )

def check_database(url):
    try:
        db = DatabaseReporter(DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME)
        db.connect()

        # Проверка сообщений
        messages = db.fetch_messages(
            'SELECT browser_url_url FROM browsers_urls LIMIT 500;'
        )

        if db.message_exists(messages, f'{url}'):
            logging.info(f'Url {url} найден в БД')
        else:
            logging.warning(f'Url {url} не найден в БД')         

    except Exception:
        logging.exception("Ошибка при работе с БД")
    
def main():
    logging.info("=== Запуск автоматизации ===")

    try:
         #0. Логирование
        report = ReportFolder("C:/Reports/Browsers")
        folder_path = report.create_folder()

        #1.Запуск браузеров
        for name, config in BROWSERS.items():

            launch_browser(
                name,
                config["path"],
                config["process"],
                config["url"]
            )

            logging.info(
                f"Пауза {DELAY_BETWEEN} сек."
            )

            time.sleep(DELAY_BETWEEN)

        #2. Проверка в БД
        chrome_url = "https://onliner.by"
        check_database(chrome_url) 
        mozilla_url = "https://21vek.by"
        check_database(mozilla_url) 
        opera_url = "https://github.com"
        check_database(opera_url) 
        yandex_url = "https://ya.ru"
        check_database(yandex_url) 
        chromium_url = "https://google.com"
        check_database(chromium_url) 
        edge_url = "https://mail.ru"
        check_database(edge_url)        

    except Exception:
        logging.exception("Критическая ошибка в процессе выполнения")

if __name__ == "__main__":
    main()
