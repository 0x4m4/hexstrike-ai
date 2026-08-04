#!/usr/bin/env python3
"""SIM800C SMS monitor — тест приёма 2FA SMS на СВОЁМ номере/SIM.

Только для авторизованного теста собственной SIM-карты и своих аккаунтов.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import serial
except ImportError:
    print("ERROR: pip install pyserial", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts" / "gsm"
ARTIFACT.mkdir(parents=True, exist_ok=True)

OTP_RE = re.compile(r"\b(\d{4,8})\b")
DEFAULT_PORT = "/dev/cu.usbserial-1420"
DEFAULT_BAUD = 115200


def at(ser: serial.Serial, cmd: str, wait: float = 1.0) -> str:
    ser.reset_input_buffer()
    ser.write((cmd + "\r\n").encode())
    time.sleep(wait)
    buf = b""
    deadline = time.time() + 3.0
    while time.time() < deadline:
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting)
            if b"OK" in buf or b"ERROR" in buf:
                break
        else:
            time.sleep(0.05)
    return buf.decode(errors="replace").strip()


def setup_sms(ser: serial.Serial) -> None:
    for cmd in (
        "AT",
        "ATE0",
        "AT+CMGF=1",           # text mode
        "AT+CNMI=2,1,0,0,0",   # push new SMS to serial immediately
        "AT+CPMS=\"SM\",\"SM\",\"SM\"",  # SIM storage
    ):
        resp = at(ser, cmd)
        if "ERROR" in resp and cmd != "AT+CPMS=\"SM\",\"SM\",\"SM\"":
            raise RuntimeError(f"{cmd} failed: {resp}")


def parse_sms_urc(chunk: str) -> dict | None:
    """Parse +CMT: header and body from URC."""
    lines = chunk.replace("\r", "").split("\n")
    for i, line in enumerate(lines):
        if line.startswith("+CMT:"):
            header = line
            body = lines[i + 1] if i + 1 < len(lines) else ""
            otp = OTP_RE.search(body)
            return {
                "header": header,
                "body": body.strip(),
                "otp_candidate": otp.group(1) if otp else None,
            }
    return None


def list_existing(ser: serial.Serial) -> list[dict]:
    resp = at(ser, 'AT+CMGL="ALL"', wait=2.0)
    messages = []
    blocks = resp.split("+CMGL:")
    for block in blocks[1:]:
        lines = block.strip().split("\n")
        if len(lines) >= 2:
            meta = lines[0].strip()
            body = "\n".join(lines[1:]).split("OK")[0].strip()
            otp = OTP_RE.search(body)
            messages.append({
                "meta": meta,
                "body": body,
                "otp_candidate": otp.group(1) if otp else None,
            })
    return messages


def append_log(path: Path, entry: dict) -> None:
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="SIM800C SMS / 2FA receive test")
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--duration", type=int, default=120, help="Monitor seconds (0=infinite)")
    parser.add_argument("--list-only", action="store_true", help="List stored SMS and exit")
    parser.add_argument("--log", type=Path, default=ARTIFACT / "sms-log.jsonl")
    args = parser.parse_args()

    print(f"[sms-monitor] port={args.port} baud={args.baud}")
    print("[sms-monitor] Только СВОЙ номер / СВОИ аккаунты для теста 2FA")
    print("[sms-monitor] Запросите код на сервисе → смотрите вывод здесь")
    print("")

    with serial.Serial(args.port, baudrate=args.baud, timeout=0.5) as ser:
        time.sleep(0.5)
        setup_sms(ser)
        print("[sms-monitor] SMS mode OK (text + CNMI push)")

        existing = list_existing(ser)
        if existing:
            print(f"[sms-monitor] Stored SMS: {len(existing)}")
            for m in existing[-5:]:
                print(f"  ---\n  {m['body'][:200]}")
                if m.get("otp_candidate"):
                    print(f"  OTP?: {m['otp_candidate']}")

        if args.list_only:
            return 0

        print(f"[sms-monitor] Listening {args.duration}s ... (Ctrl+C stop)")
        buffer = ""
        pending_cmt: str | None = None
        start = time.time()
        try:
            while args.duration == 0 or time.time() - start < args.duration:
                if ser.in_waiting:
                    buffer += ser.read(ser.in_waiting).decode(errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.replace("\r", "").strip()
                        if not line:
                            continue
                        if line.startswith("+CMT:"):
                            # Header arrives first; body is typically the next line.
                            pending_cmt = line
                            continue
                        if pending_cmt is not None:
                            parsed = parse_sms_urc(pending_cmt + "\n" + line)
                            pending_cmt = None
                            if parsed:
                                print(f"\n>>> NEW SMS <<<\n{parsed['body']}\n")
                                if parsed.get("otp_candidate"):
                                    print(f">>> OTP CODE: {parsed['otp_candidate']} <<<")
                                append_log(args.log, parsed)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[sms-monitor] stopped")

    print(f"[sms-monitor] log: {args.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
