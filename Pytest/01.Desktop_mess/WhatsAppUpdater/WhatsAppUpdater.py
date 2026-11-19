import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

import psutil

STORE_ID = "9NKSQGP7F2NH"                 # WhatsApp (не Beta 9NBDXK71NK08)
PACKAGE_NAME = "5319275A.WhatsAppDesktop"
PROCESS_NAMES = ("WhatsApp.exe", "WhatsApp.Root.exe")

# Код winget "нет применимого обновления" (APPINSTALLER_CLI_ERROR_UPDATE_NOT_APPLICABLE).
# Значение по памяти, поэтому главный критерий всё равно сравнение версий до/после.
WINGET_NO_UPDATE_CODES = {0x8A15002B, -1978335189}


@dataclass
class UpdateResult:
    version_before: Optional[str]
    version_after: Optional[str]
    updated: bool
    winget_code: Optional[int]
    winget_output: str


def _powershell(command: str, timeout: int = 60) -> str:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"PowerShell завершился с кодом {result.returncode}: {result.stderr.strip()}"
        )
    return result.stdout.strip()


class WhatsAppUpdater:
    """Обновление десктопного WhatsApp (MSIX из Microsoft Store) через winget."""

    def __init__(self, store_id: str = STORE_ID, package_name: str = PACKAGE_NAME):
        self.store_id = store_id
        self.package_name = package_name

    # ---------- информация о пакете ----------
    def get_version(self) -> Optional[str]:
        out = _powershell(
            f"(Get-AppxPackage -Name {self.package_name}).Version"
        )
        return out or None

    def get_package_family_name(self) -> Optional[str]:
        out = _powershell(
            f"(Get-AppxPackage -Name {self.package_name}).PackageFamilyName"
        )
        return out or None

    def _get_app_id(self) -> str:
        # Id приложения берём из манифеста (обычно "App"), а не хардкодим.
        out = _powershell(
            f"(Get-AppxPackage -Name {self.package_name} | Get-AppxPackageManifest)"
            ".Package.Applications.Application.Id"
        )
        return out.splitlines()[0].strip() if out else "App"

    # ---------- управление приложением ----------
    def close(self, timeout: int = 10) -> None:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = proc.info["name"]
                if name and name.lower() in {n.lower() for n in PROCESS_NAMES}:
                    logging.info("Завершаем %s (PID %s)", name, proc.pid)
                    proc.terminate()
                    try:
                        proc.wait(timeout=timeout)
                    except psutil.TimeoutExpired:
                        logging.warning("%s не завершился за %s с, убиваем", name, timeout)
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def launch(self) -> None:
        pfn = self.get_package_family_name()
        if not pfn:
            raise RuntimeError("WhatsApp не установлен: PackageFamilyName не найден")
        target = f"shell:AppsFolder\\{pfn}!{self._get_app_id()}"
        logging.info("Запуск WhatsApp: %s", target)
        subprocess.Popen(["explorer.exe", target])

    # ---------- установка / обновление ----------
    def _run_winget(self, action: str, timeout: int) -> subprocess.CompletedProcess:
        cmd = [
            "winget", action,
            "--id", self.store_id,
            "--source", "msstore",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--disable-interactivity",
        ]
        logging.info("Запуск: %s", " ".join(cmd))
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def update(self, timeout: int = 600, settle_seconds: int = 10) -> UpdateResult:
        before = self.get_version()
        logging.info("Версия WhatsApp до обновления: %s", before)

        self.close()

        action = "upgrade" if before else "install"
        result = self._run_winget(action, timeout)
        output = (result.stdout or "") + (result.stderr or "")
        logging.info("winget вывод:\n%s", output.strip())

        time.sleep(settle_seconds)  # дать Store дорегистрировать пакет
        after = self.get_version()
        logging.info("Версия WhatsApp после обновления: %s", after)

        updated = after is not None and after != before

        if not updated and result.returncode != 0:
            if result.returncode not in WINGET_NO_UPDATE_CODES:
                raise RuntimeError(
                    f"winget {action} завершился с кодом {result.returncode}, "
                    f"версия не изменилась ({before})"
                )
            logging.info("Обновлений нет, установлена актуальная версия %s", after)

        if after is None:
            raise RuntimeError("После winget WhatsApp не найден в системе")

        return UpdateResult(before, after, updated, result.returncode, output)