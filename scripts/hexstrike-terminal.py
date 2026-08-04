#!/usr/bin/env python3
"""HexStrike local terminal — chat + real agent dispatch (no Cursor)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "agents/registry.json"
WORKFLOWS = ROOT / "agents/workflows.json"
ORCHESTRATOR = ROOT / "scripts/hexstrike-orchestrator.py"
MODELFILE = ROOT / "config/hexstrike-orchestrator.modelfile"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
# Средняя DeepSeek БЕЗ R1-CoT (быстрый чат). R1 зависает на thinking 5+ мин.
CHAT_MODEL = os.environ.get("HEXSTRIKE_CHAT_MODEL", "deepseek-v2.5")
CHAT_TIMEOUT = int(os.environ.get("HEXSTRIKE_CHAT_TIMEOUT", "90"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_system_prompt() -> str:
    reg = load_json(REGISTRY)
    wf = load_json(WORKFLOWS)
    lines = [
        "Ты HexStrike Orchestrator. Отвечай сразу, кратко, по-русски. Без длинных рассуждений.",
        "Агенты:",
    ]
    for name, cfg in reg.get("agents", {}).items():
        tasks = cfg.get("tasks", {})
        if isinstance(tasks, dict) and tasks:
            lines.append(f"- {name}: {', '.join(tasks.keys())}")
    lines.append("Workflows: " + ", ".join(wf.get("workflows", {}).keys()))
    lines.append("Команды: /run <workflow> /dispatch <Agent> <task> /agents /workflows /help")
    return "\n".join(lines)


def ollama_chat(messages: list[dict], model: str) -> str:
    """Native Ollama /api/chat — handles thinking+content, hard timeout."""
    url = f"{OLLAMA_HOST}/api/chat"
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_thread": int(os.environ.get("OLLAMA_NUM_THREAD", "8")),
                "num_predict": int(os.environ.get("OLLAMA_NUM_PREDICT", "128")),
                "temperature": 0.3,
            },
        }
    ).encode()

    result: dict = {"text": "", "error": None, "done": False}
    started = time.time()
    thinking_shown = False

    def _stream() -> None:
        nonlocal thinking_shown
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=CHAT_TIMEOUT + 10) as resp:
                for raw in resp:
                    if time.time() - started > CHAT_TIMEOUT:
                        result["error"] = f"Таймаут {CHAT_TIMEOUT}с — модель слишком медленная"
                        break
                    line = raw.decode(errors="replace").strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = data.get("message") or {}
                    thinking = msg.get("thinking") or ""
                    content = msg.get("content") or ""
                    if thinking and not thinking_shown:
                        elapsed = int(time.time() - started)
                        print(f"[{elapsed}s] рассуждаю…", flush=True)
                        thinking_shown = True
                    if content:
                        print(content, end="", flush=True)
                        result["text"] += content
                    if data.get("done"):
                        break
        except Exception as exc:
            result["error"] = str(exc)

        result["done"] = True

    print(f"…ожидаю ответ ({model}, макс {CHAT_TIMEOUT}с)", flush=True)
    t = threading.Thread(target=_stream, daemon=True)
    t.start()

    while t.is_alive():
        elapsed = int(time.time() - started)
        if elapsed > 0 and elapsed % 10 == 0:
            print(f" [{elapsed}s]", end="", flush=True)
        if elapsed >= CHAT_TIMEOUT:
            result["error"] = (
                f"Таймаут {CHAT_TIMEOUT}с. Используй /run для агентов (без LLM). "
                f"Или: HEXSTRIKE_CHAT_MODEL=deepseek-v2.5:7b ./hexstrike-go.sh"
            )
            break
        time.sleep(1)

    t.join(timeout=2)
    print()

    if result["error"]:
        raise RuntimeError(result["error"])
    if not result["text"].strip():
        raise RuntimeError(
            "Пустой ответ. R1-модели зависают на thinking. "
            "Запусти: export HEXSTRIKE_CHAT_MODEL=deepseek-v2.5:7b && ./hexstrike-go.sh"
        )
    return result["text"].strip()


def run_orchestrator(args: list[str]) -> tuple[int, str]:
    cmd = [sys.executable, str(ORCHESTRATOR), *args]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = (proc.stdout or proc.stderr or "").strip()
    return proc.returncode, out[-4000:]


def cmd_help() -> str:
    return """
Команды HexStrike Terminal:
  /help                         — справка
  /agents                       — список агентов
  /workflows                    — список workflow
  /run <workflow>               — запустить pipeline (реально, без LLM)
  /dispatch <Agent-ID> <task>   — один агент (реально)
  /status                       — статус
  /exit                         — выход

Быстрые workflow:
  /run defensive-disclosure
  /run vps-full-readonly

Чат = DeepSeek v2.5 (средняя, быстрая). Агенты = /run (мгновенно).
""".strip()


def cmd_agents() -> str:
    reg = load_json(REGISTRY)
    lines = ["Зарегистрированные агенты:"]
    for name, cfg in reg.get("agents", {}).items():
        tasks = cfg.get("tasks", {})
        if isinstance(tasks, dict):
            lines.append(f"  {name}: {', '.join(tasks.keys()) or '(orchestrator)'}")
    return "\n".join(lines)


def cmd_workflows() -> str:
    code, out = run_orchestrator(["workflows"])
    return out if code == 0 else f"Ошибка workflows: {out}"


def handle_slash(line: str) -> tuple[bool, str]:
    parts = line.strip().split()
    if not parts:
        return True, ""
    cmd = parts[0].lower()

    if cmd in ("/exit", "/quit", "/bye"):
        raise SystemExit(0)
    if cmd == "/help":
        return True, cmd_help()
    if cmd == "/agents":
        return True, cmd_agents()
    if cmd == "/workflows":
        return True, cmd_workflows()
    if cmd == "/status":
        code, out = run_orchestrator(["status"])
        if code != 0:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "hexstrike_orchestrator.py"), "status"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            out = proc.stdout or proc.stderr
        return True, out
    if cmd == "/run" and len(parts) >= 2:
        wf = parts[1]
        print(f"\n[hexstrike] запуск workflow: {wf} ...\n")
        code, out = run_orchestrator(["run", wf])
        return True, f"exit={code}\n{out}"
    if cmd == "/dispatch" and len(parts) >= 3:
        agent, task = parts[1], parts[2]
        print(f"\n[hexstrike] dispatch {agent} / {task} ...\n")
        code, out = run_orchestrator(["dispatch", agent, task])
        return True, f"exit={code}\n{out}"

    return False, ""


def resolve_chat_model() -> str:
    tags = json.loads(urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5).read().decode())
    names = [m.get("name", "") for m in tags.get("models", [])]

    def has(prefix: str) -> bool:
        return any(n == prefix or n.startswith(f"{prefix}:") for n in names)

    for candidate in (
        CHAT_MODEL,
        "deepseek-v2.5:7b",
        "deepseek-v2.5",
        "deepseek-r1:7b",
        "deepseek-r1:1.5b",
    ):
        if has(candidate.split(":")[0]) or any(candidate in n for n in names):
            for n in names:
                if n.startswith(candidate) or candidate in n:
                    return n
    return CHAT_MODEL


def main() -> int:
    try:
        urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"[FAIL] Ollama недоступен: {exc}")
        return 1

    model = resolve_chat_model()
    messages: list[dict] = [{"role": "system", "content": build_system_prompt()}]

    print("╔══════════════════════════════════════════════════╗")
    print("║  HexStrike Terminal — локальный оркестратор      ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"Ollama: {OLLAMA_HOST} | chat: {model}")
    print("Агенты без LLM: /run defensive-disclosure\n")

    while True:
        try:
            user = input("hexstrike> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0

        if not user:
            continue

        if user.startswith("/"):
            try:
                handled, reply = handle_slash(user)
            except SystemExit:
                print("bye")
                return 0
            if handled:
                if reply:
                    print(reply)
                continue

        low = user.lower()
        m_run = re.search(r"(?:запусти|run)\s+(?:workflow\s+)?([\w-]+)", low)

        messages.append({"role": "user", "content": user})
        try:
            reply = ollama_chat(messages, model=model)
        except Exception as exc:
            print(f"[FAIL] {exc}")
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": reply})
        print()

        if m_run:
            print(f"[подсказка] Реальный запуск: /run {m_run.group(1)}\n")


if __name__ == "__main__":
    raise SystemExit(main())
