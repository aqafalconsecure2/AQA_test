import os
import subprocess
import time
import logging

from ReportFolder import ReportFolder

VPN_NAME = "vm02n"
ADAPTER = "Ethernet0"
HOST_LOG = r"C:\ProgramData\Falcongaze SecureTower\EPA\host.log"
LOG_ENCODING = "utf-8"
APP_PATH = r"C:\Program Files\Mozilla Firefox\firefox.exe"
APP_NAME = "firefox.exe"
DEFAULT_PROFILE = "Профиль по умолчанию"

results = {}


def run(cmd):
    logging.info("Команда: %s", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="cp866")
    logging.info("Код возврата: %s", r.returncode)
    if r.stdout.strip():
        logging.info("Вывод: %s", r.stdout.strip())
    if r.stderr.strip():
        logging.warning("Ошибки: %s", r.stderr.strip())
    return r


def set_adapter(enable):
    state = "enable" if enable else "disable"
    logging.info("%s адаптер %s", "Включаю" if enable else "Отключаю", ADAPTER)
    r = run(["netsh", "interface", "set", "interface", ADAPTER, f"admin={state}"])
    if r.returncode != 0:
        raise RuntimeError(r.stdout or r.stderr)


def log_size():
    return os.path.getsize(HOST_LOG) if os.path.exists(HOST_LOG) else 0


def check(profile, pos, delay, name):    
    logging.info("[%s] Ожидание %s с, поиск 'profile = %s'", name, delay, profile)
    time.sleep(delay)
    try:
        with open(HOST_LOG, "rb") as f:
            f.seek(pos)
            text = f.read().decode(LOG_ENCODING, errors="replace")
    except OSError as e:
        logging.error("[%s] Не удалось найти запись в логе host.log: %s", name, e)
        results[name] = False
        return False

    needle = f"profile = {profile}"
    lines = [l.strip() for l in text.splitlines() if needle in l]
    ok = bool(lines)
    if ok:
        logging.info("[%s] Найдены записи в логе: %s. Пример: %s", name, len(lines), lines[0])
    else:
        others = [l.strip() for l in text.splitlines() if "profile = " in l]
        logging.error("[%s] FAIL: '%s' не найдено. Новых записей о профилях: %s",
                      name, needle, len(others))
        for l in others[-3:]:
            logging.error("[%s]   встретилось: %s", name, l)
    results[name] = ok
    return ok


def test_adapter():
    logging.info("Активация профиля при недоступности EPAPS")
    pos = log_size()
    set_adapter(False)
    check("EPAPS", pos, 90, "Профиль EPAPS")

    pos = log_size()
    set_adapter(True)
    check(DEFAULT_PROFILE, pos, 20, "Профиль по умолчанию")
    time.sleep(5)

def test_vpn():
    logging.info("Активация профиля при актвином VPN")
    pos = log_size()
    logging.info("Включение VPN на %s", VPN_NAME)
    run(["rasdial", VPN_NAME])
    check("VPN", pos, 20, "Профиль VPN")

    pos = log_size()
    logging.info("Выключение VPN %s", VPN_NAME)
    run(["rasdial", VPN_NAME, "/disconnect"])
    check(DEFAULT_PROFILE, pos, 15, "Профль по умолчанию")
    time.sleep(5)

def test_lua():
    logging.info("Активация профиля c использованием LUA скрипта")
    pos = log_size()
    logging.info("Запуск приложения: %s", APP_PATH)
    proc = subprocess.Popen([APP_PATH])
    try:
        check("LUA", pos, 10, "Профиль LUA")
    finally:
        run(["taskkill", "/IM", APP_NAME, "/T", "/F"])
        logging.info("Приложение закрыто")


report = ReportFolder("C:/Reports")
folder = report.create_folder()
if not folder:
    raise SystemExit("Не удалось создать папку отчёта")

logging.info("Запуск проверки активации профилей, отчёт: %s ===", folder)

try:
    test_adapter()
    test_vpn()
    test_lua()
except Exception:
    logging.exception("Ошибка в ходе проверок")
finally:
    #logging.info("Страховка: отключаю VPN")
    #run(["rasdial", VPN_NAME, "/disconnect"])
    #logging.info("=== Итоги ===")
    #for name, ok in results.items():
    #    logging.info("%-35s %s", name, "OK" if ok else "FAIL")
    logging.info("Проверка завершена")
