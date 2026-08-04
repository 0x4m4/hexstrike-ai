"""Local LLM provider — llama-server (:8080) primary, Ollama (:11434) fallback.

Also supports Ollama local-cloud offload and ollama.com direct API.

Priority (default): llama-server > ollama-local
Overrides: LLM_PROVIDER, LLM_BASE_URL, LLM_PROVIDER_PRIORITY, LLAMA_SERVER_HOST, OLLAMA_HOST
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_LLAMA_HOST = "http://127.0.0.1:8080"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_CLOUD_HOST = "https://ollama.com"
DEFAULT_MODEL = "deepseek-r1:1.5b"
DEFAULT_CLOUD_MODEL = "qwen3-coder:480b-cloud"
DEFAULT_CLOUD_DIRECT_MODEL = "qwen3.5:397b"
DEFAULT_NUM_THREAD = 16
DEFAULT_NUM_PREDICT = 256
DEFAULT_NUM_CTX = 32768
DEFAULT_PRIORITY = ("llama-server", "ollama-local")

PROVIDER_LLAMA = "llama-server"
PROVIDER_LOCAL = "ollama-local"
PROVIDER_LOCAL_CLOUD = "ollama-local-cloud"
PROVIDER_CLOUD = "ollama-cloud"

# repo root: src/hexstrike/llm/provider.py -> parents[3] == repo
_REPO_ROOT = Path(__file__).resolve().parents[3]
SYSTEM_PROMPT_PATH = _REPO_ROOT / "config" / "llm-system-prompt.md"


def _load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE from repo .env into os.environ (do not override existing)."""
    env_path = path or (_REPO_ROOT / ".env")
    if not env_path.is_file():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        return


def ollama_request_options() -> dict[str, int]:
    """Runtime Ollama options — tune via OLLAMA_NUM_THREAD / OLLAMA_NUM_PREDICT / OLLAMA_NUM_CTX."""
    opts: dict[str, int] = {
        "num_thread": int(os.environ.get("OLLAMA_NUM_THREAD", DEFAULT_NUM_THREAD)),
        "num_predict": int(os.environ.get("OLLAMA_NUM_PREDICT", DEFAULT_NUM_PREDICT)),
    }
    num_ctx = os.environ.get("OLLAMA_NUM_CTX")
    if num_ctx:
        opts["num_ctx"] = int(num_ctx)
    elif "qwen2.5-coder" in os.environ.get("OLLAMA_MODEL", os.environ.get("LLM_MODEL", DEFAULT_MODEL)):
        opts["num_ctx"] = DEFAULT_NUM_CTX
    return opts


def rescue_path_blocks_llm() -> bool:
    """When true, LLM must not run synchronously on PrepareRescue / signing hot path."""
    return os.environ.get("LLM_ASYNC_ONLY", "1").lower() in ("1", "true", "yes")


def enqueue_llm_task(fn) -> None:
    """Fire-and-forget LLM work (bytecode deobfuscation, extended OSINT)."""
    import threading

    threading.Thread(target=fn, daemon=True, name="hexstrike-llm-async").start()


def is_cloud_model(model: str) -> bool:
    """True when the model tag is an Ollama cloud-offload variant (e.g. gpt-oss:120b-cloud)."""
    return model.endswith("-cloud") or ":cloud" in model


def is_cloud_direct_host(host: str) -> bool:
    """True when routing directly to ollama.com instead of a local daemon."""
    normalized = host.rstrip("/").lower()
    return normalized in (DEFAULT_CLOUD_HOST, "https://ollama.com", "http://ollama.com")


@dataclass(frozen=True)
class LlmConfig:
    provider: str
    host: str
    base_url: str
    model: str
    integration_mode: str
    bypass_tunnel: bool
    priority: tuple[str, ...] = DEFAULT_PRIORITY
    llama_reachable: bool = False
    ollama_reachable: bool = False
    api_key: str | None = None
    cloud_mode: str = "local"  # local | local-cloud | cloud-direct
    # Dedicated Ollama daemon host (never the llama-server URL)
    ollama_host: str = DEFAULT_OLLAMA_HOST
    llama_host: str = DEFAULT_LLAMA_HOST


def _http_ok(url: str, timeout: float = 3.0, *, headers: dict[str, str] | None = None) -> bool:
    req = urllib.request.Request(url, method="GET", headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def _auth_headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


def _request_json(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 5.0,
) -> tuple[int, dict[str, Any]]:
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode())
        return resp.status, payload


def detect_llama_server(host: str = DEFAULT_LLAMA_HOST, timeout: float = 3.0) -> bool:
    """Return True when llama-server / OpenAI-compatible server responds."""
    base = host.rstrip("/")
    return _http_ok(f"{base}/v1/models", timeout=timeout) or _http_ok(
        f"{base}/health", timeout=timeout
    )


def detect_ollama(host: str = DEFAULT_OLLAMA_HOST, *, api_key: str | None = None, timeout: float = 3.0) -> bool:
    """Return True when Ollama responds on the given host."""
    url = f"{host.rstrip('/')}/api/tags"
    try:
        _request_json(url, headers=_auth_headers(api_key), timeout=timeout)
        return True
    except (urllib.error.URLError, TimeoutError, OSError, urllib.error.HTTPError, json.JSONDecodeError):
        return False


def detect_local_ollama(host: str = DEFAULT_OLLAMA_HOST, timeout: float = 3.0) -> bool:
    """Return True when a local Ollama daemon responds on the given host."""
    if is_cloud_direct_host(host):
        return False
    return detect_ollama(host, timeout=timeout)


def list_ollama_models(
    host: str = DEFAULT_OLLAMA_HOST,
    *,
    api_key: str | None = None,
    timeout: float = 5.0,
) -> list[str]:
    url = f"{host.rstrip('/')}/api/tags"
    _, payload = _request_json(url, headers=_auth_headers(api_key), timeout=timeout)
    return [m.get("name", "") for m in payload.get("models", [])]


# Back-compat alias used by older scripts
list_models = list_ollama_models


def list_openai_models(base_url: str, timeout: float = 5.0) -> list[str]:
    """List models from OpenAI-compatible /v1/models (llama-server)."""
    if base_url.rstrip("/").endswith("/v1"):
        url = f"{base_url.rstrip('/')}/models"
    else:
        url = f"{base_url.rstrip('/')}/v1/models"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode())
    data = payload.get("data") or payload.get("models") or []
    names: list[str] = []
    for m in data:
        if isinstance(m, dict):
            names.append(m.get("id") or m.get("name") or "")
        elif isinstance(m, str):
            names.append(m)
    return [n for n in names if n]


def has_qwen_coder(models: list[str]) -> bool:
    return any("qwen2.5-coder" in name or "qwen3-coder" in name for name in models)


def has_deepseek_r1(models: list[str]) -> bool:
    return any("deepseek-r1" in name for name in models)


def _local_base_url(host: str) -> str:
    h = host.rstrip("/")
    return h if h.endswith("/v1") else f"{h}/v1"


def _parse_priority() -> tuple[str, ...]:
    raw = os.environ.get("LLM_PROVIDER_PRIORITY", "").strip()
    if not raw:
        return DEFAULT_PRIORITY
    items = tuple(p.strip() for p in raw.split(",") if p.strip())
    return items or DEFAULT_PRIORITY


def load_defense_system_prompt(path: Path | None = None) -> str:
    """Load defense-only system prompt prepended to every skill/chat call."""
    p = path or Path(os.environ.get("LLM_SYSTEM_PROMPT_PATH", str(SYSTEM_PROMPT_PATH)))
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return (
        "HexStrike defense-only mode. Refuse drain/theft/exploit plans, "
        "unknown-target ops, and private-key extraction. Prefer remediation."
    )


def prepend_defense_prompt(messages: list[dict[str, str]], system_prompt: str | None = None) -> list[dict[str, str]]:
    """Ensure the defense system prompt is the first system message."""
    defense = (system_prompt or load_defense_system_prompt()).strip()
    out = list(messages)
    if out and out[0].get("role") == "system":
        existing = out[0].get("content") or ""
        if defense[:80] not in existing:
            out[0] = {"role": "system", "content": defense + "\n\n---\n\n" + existing}
        return out
    return [{"role": "system", "content": defense}] + out


def resolve_llm_config() -> LlmConfig:
    """Resolve LLM endpoint — llama-server, Ollama local/cloud, or public tunnel."""
    _load_dotenv()
    llama_host = os.environ.get("LLAMA_SERVER_HOST", DEFAULT_LLAMA_HOST)
    ollama_host = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
    model = os.environ.get("LLM_MODEL", os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL))
    integration_mode = os.environ.get("CURSOR_INTEGRATION_MODE", "SYSTEM_INTEGRATION")
    priority = _parse_priority()
    api_key = os.environ.get("OLLAMA_API_KEY", "").strip() or None
    cloud_host = os.environ.get("OLLAMA_CLOUD_HOST", DEFAULT_CLOUD_HOST).strip() or DEFAULT_CLOUD_HOST

    llama_ok = detect_llama_server(llama_host)
    ollama_ok = detect_local_ollama(ollama_host)

    explicit_provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    explicit_base = os.environ.get("LLM_BASE_URL", "").strip()

    # Cloud-direct / local-cloud take precedence when explicitly selected
    if explicit_provider == PROVIDER_CLOUD or (is_cloud_direct_host(ollama_host) and api_key):
        host = cloud_host if explicit_provider == PROVIDER_CLOUD else ollama_host
        if not model or model == DEFAULT_MODEL:
            model = os.environ.get("OLLAMA_CLOUD_MODEL", DEFAULT_CLOUD_DIRECT_MODEL)
        return LlmConfig(
            provider=PROVIDER_CLOUD,
            host=host,
            base_url=_local_base_url(host),
            model=model,
            integration_mode=integration_mode,
            bypass_tunnel=False,
            priority=priority,
            llama_reachable=llama_ok,
            ollama_reachable=ollama_ok,
            api_key=api_key,
            cloud_mode="cloud-direct",
            ollama_host=ollama_host,
            llama_host=llama_host,
        )

    if explicit_provider == PROVIDER_LOCAL_CLOUD or is_cloud_model(model):
        if model == DEFAULT_MODEL:
            model = os.environ.get("OLLAMA_CLOUD_MODEL", DEFAULT_CLOUD_MODEL)
        return LlmConfig(
            provider=PROVIDER_LOCAL_CLOUD,
            host=ollama_host,
            base_url=_local_base_url(ollama_host),
            model=model,
            integration_mode=integration_mode,
            bypass_tunnel=ollama_ok,
            priority=priority,
            llama_reachable=llama_ok,
            ollama_reachable=ollama_ok,
            api_key=None,
            cloud_mode="local-cloud",
            ollama_host=ollama_host,
            llama_host=llama_host,
        )

    provider = ""
    host = ""
    base_url = ""

    # Explicit base URL always honored when set
    if explicit_base:
        base_url = explicit_base if explicit_base.rstrip("/").endswith("/v1") else _local_base_url(explicit_base)
        if explicit_provider in (PROVIDER_LLAMA, PROVIDER_LOCAL):
            provider = explicit_provider
        elif "11434" in base_url:
            provider = PROVIDER_LOCAL
        else:
            provider = PROVIDER_LLAMA
        host = base_url[:-3] if base_url.endswith("/v1") else base_url
    elif explicit_provider in (PROVIDER_LLAMA, PROVIDER_LOCAL, "ollama"):
        provider = PROVIDER_LOCAL if explicit_provider == "ollama" else explicit_provider
        if provider == PROVIDER_LLAMA:
            host = llama_host
            base_url = _local_base_url(llama_host)
        else:
            host = ollama_host
            base_url = _local_base_url(ollama_host)
    else:
        # Auto by priority + reachability (empty LLM_PROVIDER / LLM_BASE_URL)
        for cand in priority:
            if cand == PROVIDER_LLAMA and llama_ok:
                provider, host, base_url = PROVIDER_LLAMA, llama_host, _local_base_url(llama_host)
                break
            if cand in (PROVIDER_LOCAL, "ollama") and ollama_ok:
                provider, host, base_url = PROVIDER_LOCAL, ollama_host, _local_base_url(ollama_host)
                break
        if not provider:
            # Prefer first priority host even if down (so status shows intended primary)
            first = priority[0] if priority else PROVIDER_LLAMA
            if first == PROVIDER_LLAMA:
                provider, host, base_url = PROVIDER_LLAMA, llama_host, _local_base_url(llama_host)
            else:
                provider, host, base_url = PROVIDER_LOCAL, ollama_host, _local_base_url(ollama_host)

    bypass_tunnel = os.environ.get("OLLAMA_BYPASS_TUNNEL", "").lower() in ("1", "true", "yes")
    if llama_ok or ollama_ok or integration_mode == "OFFLINE_PRIMARY":
        bypass_tunnel = True

    # Optional public tunnel only when local down and not bypassing
    public = os.environ.get("OLLAMA_PUBLIC_BASE_URL", "").strip()
    if (not llama_ok and not ollama_ok) and public and not bypass_tunnel:
        base_url = public if public.endswith("/v1") else f"{public.rstrip('/')}/v1"

    return LlmConfig(
        provider=provider,
        host=host,
        base_url=base_url,
        model=model,
        integration_mode=integration_mode,
        bypass_tunnel=bypass_tunnel,
        priority=priority,
        llama_reachable=llama_ok,
        ollama_reachable=ollama_ok,
        api_key=None,
        cloud_mode="local",
        ollama_host=ollama_host,
        llama_host=llama_host,
    )


class LocalLlmProvider:
    """Thin client for llama-server / Ollama OpenAI-compatible APIs."""

    def __init__(self, config: LlmConfig | None = None) -> None:
        self.config = config or resolve_llm_config()
        self.defense_prompt = load_defense_system_prompt()
        os.environ.setdefault("LLM_PROVIDER", self.config.provider)
        os.environ.setdefault("LLM_BASE_URL", self.config.base_url)
        os.environ.setdefault("LLM_MODEL", self.config.model)
        os.environ.setdefault("LLAMA_SERVER_HOST", self.config.llama_host)
        # Always keep OLLAMA_HOST on the Ollama daemon — never llama-server :8080
        os.environ.setdefault("OLLAMA_HOST", self.config.ollama_host)

    def _headers(self, *, content_type: bool = False) -> dict[str, str]:
        headers = _auth_headers(self.config.api_key)
        if content_type:
            headers["Content-Type"] = "application/json"
        return headers

    def selected_provider_reachable(self) -> bool:
        """Live probe of the currently selected provider (not cached resolve flags)."""
        if self.config.provider == PROVIDER_LLAMA:
            return detect_llama_server(self.config.host)
        if self.config.cloud_mode == "cloud-direct":
            return detect_ollama(self.config.host, api_key=self.config.api_key, timeout=8.0)
        return detect_ollama(self.config.host, api_key=self.config.api_key)

    def status(self) -> dict[str, Any]:
        models: list[str] = []
        selected_ok = self.selected_provider_reachable()
        if selected_ok:
            try:
                if self.config.provider == PROVIDER_LLAMA:
                    models = list_openai_models(self.config.base_url)
                else:
                    models = list_ollama_models(self.config.host, api_key=self.config.api_key)
            except (
                urllib.error.URLError,
                TimeoutError,
                OSError,
                json.JSONDecodeError,
                ValueError,
                urllib.error.HTTPError,
            ):
                models = []

        llama_live = detect_llama_server(self.config.llama_host)
        ollama_live = detect_local_ollama(self.config.ollama_host)

        return {
            "provider": self.config.provider,
            "host": self.config.host,
            "base_url": self.config.base_url,
            "model": self.config.model,
            "integration_mode": self.config.integration_mode,
            "bypass_tunnel": self.config.bypass_tunnel,
            "priority": list(self.config.priority),
            "cloud_mode": self.config.cloud_mode,
            "cloud_authenticated": bool(self.config.api_key),
            "llama_server_reachable": llama_live,
            "ollama_reachable": ollama_live,
            "endpoint_reachable": selected_ok,
            "local_inference": selected_ok and self.config.cloud_mode == "local",
            "selected_provider_reachable": selected_ok,
            "qwen_coder_available": has_qwen_coder(models),
            "deepseek_r1_available": has_deepseek_r1(models),
            "cloud_model": is_cloud_model(self.config.model),
            "models": models,
            "defense_system_prompt": str(SYSTEM_PROMPT_PATH),
            "options": ollama_request_options() if self.config.provider != PROVIDER_LLAMA else {},
        }

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        timeout: float = 120.0,
        prepend_defense: bool = True,
    ) -> dict[str, Any]:
        """Chat completions with defense system prompt prepended by default."""
        msgs = prepend_defense_prompt(messages, self.defense_prompt) if prepend_defense else list(messages)
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        body_obj: dict[str, Any] = {
            "model": model or self.config.model,
            "messages": msgs,
            "stream": False,
            "temperature": temperature,
        }
        if self.config.provider in (PROVIDER_LOCAL, PROVIDER_LOCAL_CLOUD, PROVIDER_CLOUD):
            body_obj["options"] = ollama_request_options()
        body = json.dumps(body_obj).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers=self._headers(content_type=True),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode())
            content = ""
            choices = payload.get("choices") or []
            if choices:
                content = (choices[0].get("message") or {}).get("content") or ""
            return {
                "ok": True,
                "content": content,
                "raw": payload,
                "url": url,
                "provider": self.config.provider,
            }
        except urllib.error.HTTPError as exc:
            detail = exc.read(400).decode(errors="replace")
            return {"ok": False, "error": detail[:300], "status": exc.code, "url": url}
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            return {"ok": False, "error": str(exc), "url": url}

    def handshake(self, *, probe: str = "both") -> dict[str, Any]:
        """Status + latency probes + defense-prompted chat ping."""
        probes = ["models", "chat"] if probe == "both" else [probe]
        report: dict[str, Any] = {
            "llm": self.status(),
            "latency": {p: self.measure_hook_latency(probe=p) for p in probes},
        }
        if "chat" in probes:
            report["defense_chat"] = self.chat(
                [{"role": "user", "content": "Reply with exactly: DEFENSE_OK"}],
                temperature=0.0,
            )
        return report

    def measure_hook_latency(self, *, probe: str = "models") -> dict[str, Any]:
        """Measure round-trip latency for the Cursor ↔ model hook."""
        if probe == "chat":
            url = f"{self.config.base_url.rstrip('/')}/chat/completions"
            msgs = prepend_defense_prompt([{"role": "user", "content": "ping"}], self.defense_prompt)
            body_obj: dict[str, Any] = {
                "model": self.config.model,
                "messages": msgs,
                "stream": False,
            }
            if self.config.provider in (PROVIDER_LOCAL, PROVIDER_LOCAL_CLOUD, PROVIDER_CLOUD):
                body_obj["options"] = ollama_request_options()
            body = json.dumps(body_obj).encode()
            headers = self._headers(content_type=True)
            method = "POST"
        else:
            url = f"{self.config.base_url.rstrip('/')}/models"
            body = None
            headers = self._headers()
            method = "GET"

        start = time.perf_counter()
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                elapsed_ms = (time.perf_counter() - start) * 1000
                return {
                    "probe": probe,
                    "url": url,
                    "status": resp.status,
                    "latency_ms": round(elapsed_ms, 2),
                    "ok": True,
                }
        except urllib.error.HTTPError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            detail = exc.read(300).decode(errors="replace")
            return {
                "probe": probe,
                "url": url,
                "status": exc.code,
                "latency_ms": round(elapsed_ms, 2),
                "ok": False,
                "error": detail[:200],
            }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {
                "probe": probe,
                "url": url,
                "latency_ms": round(elapsed_ms, 2),
                "ok": False,
                "error": str(exc),
            }


def write_env_llm_block(env_path: Path, config: LlmConfig) -> None:
    """Upsert LLM discovery keys without pinning a dead provider endpoint.

    Keeps LLM_PROVIDER / LLM_BASE_URL empty for auto-detect on next resolve,
    preserves an existing OLLAMA_PUBLIC_BASE_URL (tunnel), and always writes
    distinct LLAMA_SERVER_HOST / OLLAMA_HOST values.
    """
    lines: list[str] = []
    existing_public = ""
    if env_path.is_file():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if line.startswith("OLLAMA_PUBLIC_BASE_URL=") and not line.strip().startswith("#"):
                existing_public = line.split("=", 1)[1].strip()
                break

    # Prefer env / config dedicated hosts over selected config.host
    llama_host = config.llama_host or os.environ.get("LLAMA_SERVER_HOST", DEFAULT_LLAMA_HOST)
    ollama_host = config.ollama_host or os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)

    # Do not overwrite a real tunnel URL with localhost
    public_url = existing_public
    env_public = os.environ.get("OLLAMA_PUBLIC_BASE_URL", "").strip()
    if env_public and "127.0.0.1" not in env_public and "localhost" not in env_public:
        public_url = env_public
    elif existing_public and ("127.0.0.1" in existing_public or "localhost" in existing_public):
        # Clear stale local pins so tunnel fallback can be set manually
        if config.bypass_tunnel:
            public_url = ""

    updates = {
        # Empty = auto via LLM_PROVIDER_PRIORITY + reachability
        "LLM_PROVIDER": "",
        "LLM_BASE_URL": "",
        "LLM_MODEL": config.model,
        "LLM_PROVIDER_PRIORITY": ",".join(config.priority),
        "LLAMA_SERVER_HOST": llama_host,
        "OLLAMA_HOST": ollama_host,
        "OLLAMA_BYPASS_TUNNEL": "true" if config.bypass_tunnel else os.environ.get("OLLAMA_BYPASS_TUNNEL", "true"),
        "OLLAMA_PUBLIC_BASE_URL": public_url,
        "CURSOR_INTEGRATION_MODE": config.integration_mode or "OFFLINE_PRIMARY",
    }

    keys_seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in updates:
                out.append(f"{k}={updates[k]}")
                keys_seen.add(k)
                continue
        out.append(line)
    for k, v in updates.items():
        if k not in keys_seen:
            out.append(f"{k}={v}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
