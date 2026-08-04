#!/usr/bin/env python3
"""Автоматический поиск причины: почему Mac не видит SIM800C/USB-UART."""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "gsm" / "root-cause.json"


def run(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=30)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        out = getattr(e, "output", "") or ""
        return out


def glob_ports() -> list[str]:
    import glob
    skip = ("bluetooth", "debug-console", "jbl", "bose", "airpods", "beats")
    ports = []
    for p in sorted(glob.glob("/dev/cu.*")):
        if not any(s in p.lower() for s in skip):
            ports.append(p)
    return ports


def pyserial_ports() -> list[dict]:
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    out = []
    for p in list_ports.comports():
        out.append({
            "device": p.device,
            "description": p.description,
            "vid": p.vid,
            "pid": p.pid,
            "manufacturer": p.manufacturer,
        })
    return out


def usb_profiler_text() -> str:
    return run(["system_profiler", "SPUSBDataType"])


def ioreg_usb_text() -> str:
    return run(["ioreg", "-p", "IOUSB", "-l"])


def detect_usb_serial_chips(text: str) -> list[str]:
    chips = []
    patterns = {
        "CH340": r"CH340|wch\.cn|1a86",
        "CP2102": r"CP210|Silicon Labs|10c4",
        "FTDI": r"FTDI|0403|FT232",
        "PL2303": r"Prolific|067b",
    }
    for name, pat in patterns.items():
        if re.search(pat, text, re.I):
            chips.append(name)
    return chips


def main() -> int:
    if platform.system() != "Darwin":
        print("Запускайте на Mac: python3 scripts/gsm/find-root-cause.py")
        return 2

    cu_ports = glob_ports()
    ps_ports = pyserial_ports()
    usb_text = usb_profiler_text()
    ioreg_text = ioreg_usb_text()
    chips_usb = detect_usb_serial_chips(usb_text)
    chips_ioreg = detect_usb_serial_chips(ioreg_text)

    # Decision tree
    verdict = ""
    cause = ""
    fix = []
    confidence = "high"

    has_usb_chip = bool(chips_usb or chips_ioreg)
    has_cu_port = bool(cu_ports)

    if not has_usb_chip and not has_cu_port:
        verdict = "USB_UART_NOT_ENUMERATED"
        cause = (
            "macOS не видит USB-UART адаптер на шине USB. "
            "Это уровень кабеля/порта/адаптера — до SIM800C и AT-команд дело не доходит."
        )
        fix = [
            "Подключите ТОЛЬКО USB-TTL в iMac (без SIM800C) и снова запустите скрипт",
            "Замените USB-кабель — 80% 'раньше работало' ломается charge-only кабелем",
            "Попробуйте другой USB-порт iMac (напрямую, без хаба)",
            "Установите драйвер CH340/CP2102 и разрешите в System Settings → Privacy & Security",
            "Проверьте: USB-TTL воткнут в Mac, а не только питание 4V на плату",
        ]
    elif has_usb_chip and not has_cu_port:
        verdict = "DRIVER_BLOCKED"
        cause = (
            "USB-чип виден в system_profiler/ioreg, но /dev/cu.* не создан — "
            "драйвер не загружен или заблокирован macOS (типично после обновления macOS)."
        )
        fix = [
            "Переустановите драйвер (CH340: github.com/WCHSoftGroup/ch34xser_mac)",
            "System Settings → Privacy & Security → Allow system extension",
            "Перезагрузите Mac",
            "systemextensionsctl list — проверьте статус драйвера",
        ]
    elif has_cu_port:
        verdict = "PORT_EXISTS_AT_FAIL"
        cause = (
            f"Serial-порт есть ({', '.join(cu_ports)}), но модуль не отвечает на AT — "
            "проблема в проводке TX/RX, питании 4V, baud или SIM800C."
        )
        fix = [
            "Проверьте TXD↔RXD (перекрёстно), GND общий",
            "Питание 4.0V / 2A на VCC модуля",
            "Попробуйте baud 115200 и 9600",
            f"minicom -D {cu_ports[0]} -b 115200 → AT",
        ]
        confidence = "medium"
    else:
        verdict = "UNKNOWN"
        cause = "Недостаточно данных"
        confidence = "low"

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": run(["scutil", "--get", "ComputerName"]).strip(),
        "macos": run(["sw_vers", "-productVersion"]).strip(),
        "verdict": verdict,
        "confidence": confidence,
        "root_cause": cause,
        "fix_steps": fix,
        "evidence": {
            "cu_ports": cu_ports,
            "pyserial_ports": ps_ports,
            "usb_chips_detected": list(set(chips_usb + chips_ioreg)),
            "usb_profiler_has_serial": has_usb_chip,
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print("=" * 60)
    print(f"ВЕРДИКТ: {verdict} ({confidence})")
    print("=" * 60)
    print(f"\nПричина:\n  {cause}\n")
    print("Исправление:")
    for i, step in enumerate(fix, 1):
        print(f"  {i}. {step}")
    print(f"\nОтчёт: {OUT}")
    return 0 if verdict == "PORT_EXISTS_AT_FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
