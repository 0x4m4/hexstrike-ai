#!/usr/bin/env python3
"""SIM800C auto-detect + AT diagnostic (run on machine with USB-UART attached)."""

from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts" / "gsm"
ARTIFACT.mkdir(parents=True, exist_ok=True)

BAUD_RATES = (115200, 9600, 57600, 38400, 19200)
PROBE_COMMANDS = (
    ("AT", "basic"),
    ("ATE0", "echo_off"),
    ("AT+CPIN?", "sim_pin"),
    ("AT+CSQ", "signal"),
    ("AT+CREG?", "network_reg"),
    ("AT+COPS?", "operator"),
    ("AT+CGSN", "imei"),
    ("AT+CCID", "iccid"),
)


def find_candidate_ports() -> list[str]:
    import platform
    patterns = (
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
        "/dev/cu.usbserial*",
        "/dev/cu.SLAB_USBtoUART*",
        "/dev/cu.wchusbserial*",
        "/dev/cu.usbmodem*",
        "/dev/cu.usb*",
    )
    skip = ("bluetooth", "debug-console", "jbl", "bose", "airpods", "beats")
    found: list[str] = []
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if any(s in path.lower() for s in skip):
                continue
            if path not in found:
                found.append(path)

    # macOS: scan all cu.* if nothing matched yet
    if platform.system() == "Darwin" and not found:
        for path in sorted(glob.glob("/dev/cu.*")):
            base = path.lower()
            if any(s in base for s in skip):
                continue
            if path not in found:
                found.append(path)

    for port in list_ports.comports():
        dev = port.device
        if dev.startswith("/dev/tty.") and platform.system() == "Darwin":
            dev = dev.replace("/dev/tty.", "/dev/cu.", 1)
        desc = (port.description or "").lower()
        hwid = (port.hwid or "").lower()
        if any(k in desc or k in hwid for k in (
            "ch340", "cp210", "ftdi", "usb serial", "uart", "wch", "serial", "usbmodem"
        )):
            if dev not in found:
                found.append(dev)
        elif platform.system() == "Darwin" and port.vid is not None:
            # Any USB serial adapter with VID/PID
            if dev not in found and not any(s in dev.lower() for s in skip):
                found.append(dev)
    return found


def send_at(ser: serial.Serial, cmd: str, timeout: float = 2.0) -> str:
    ser.reset_input_buffer()
    ser.write((cmd + "\r\n").encode())
    deadline = time.time() + timeout
    chunks: list[str] = []
    while time.time() < deadline:
        waiting = ser.in_waiting
        if waiting:
            chunks.append(ser.read(waiting).decode(errors="replace"))
            if "OK" in chunks[-1] or "ERROR" in chunks[-1]:
                break
        else:
            time.sleep(0.05)
    return "".join(chunks).strip()


def probe_port(port: str, baud: int) -> dict | None:
    try:
        with serial.Serial(port, baudrate=baud, timeout=1) as ser:
            time.sleep(0.3)
            resp = send_at(ser, "AT", timeout=1.5)
            if "OK" not in resp.upper():
                return None
            results = {"port": port, "baud": baud, "at_ok": True, "commands": {}}
            for cmd, key in PROBE_COMMANDS[1:]:
                results["commands"][key] = send_at(ser, cmd)
            return results
    except (serial.SerialException, OSError):
        return None


def diagnose(explicit_port: str | None, explicit_baud: int | None) -> dict:
    ports = [explicit_port] if explicit_port else find_candidate_ports()
    report: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ports_scanned": ports,
        "modem": None,
        "errors": [],
    }

    if not ports:
        report["errors"].append("No serial ports found. Check USB cable, driver, permissions.")
        return report

    # --baud alone: honor that rate on every candidate port.
    # --port + --baud: try the requested rate first, then fall back on that port
    # so a wrong env baud does not abort detection.
    # --port alone / neither: full BAUD_RATES scan.
    if explicit_port and explicit_baud is not None:
        baud_rates: tuple[int, ...] = (explicit_baud,) + tuple(
            b for b in BAUD_RATES if b != explicit_baud
        )
    elif explicit_baud is not None:
        baud_rates = (explicit_baud,)
    else:
        baud_rates = BAUD_RATES

    for port in ports:
        for baud in baud_rates:
            hit = probe_port(port, baud)
            if hit:
                report["modem"] = hit
                return report
        report["errors"].append(f"No AT response on {port} (tried {list(baud_rates)})")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="SIM800C UART diagnostic")
    parser.add_argument("--port", help="Serial port, e.g. /dev/ttyUSB0 or /dev/cu.usbserial-*")
    parser.add_argument("--baud", type=int, default=None, help="Baud rate (default: auto)")
    parser.add_argument("--json-out", type=Path, default=ARTIFACT / "sim800c-diagnose.json")
    args = parser.parse_args()

    report = diagnose(args.port, args.baud)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report.get("modem"):
        m = report["modem"]
        print(f"\n[OK] SIM800C found: {m['port']} @ {m['baud']} baud")
        return 0
    print("\n[FAIL] SIM800C not detected. See errors above.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
