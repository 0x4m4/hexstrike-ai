"""AES-256 encrypted local keystore — keys never exposed in logs or bus payloads."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hexstrike.bus.context_bus import ContextBus
from hexstrike.paths import ARTIFACTS_DIR
import os
import platform


class VaultError(RuntimeError):
    pass


def resolve_vault_storage(prefer_ramdisk: bool = True) -> Path:
    """Prefer RAM-backed storage for high-value vault material when available."""
    if prefer_ramdisk:
        if platform.system() == "Linux" and Path("/dev/shm").is_dir():
            path = Path("/dev/shm/hexstrike-vault")
            path.mkdir(parents=True, exist_ok=True)
            return path
        if platform.system() == "Darwin":
            ram = Path("/Volumes/RAMDisk/hexstrike-vault")
            if ram.parent.exists():
                ram.mkdir(parents=True, exist_ok=True)
                return ram
    return ARTIFACTS_DIR / "vault"


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, 200_000, dklen=32)


def _aes_encrypt(plaintext: bytes, key: bytes) -> bytes:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise VaultError("cryptography package required for vault (pip install cryptography)") from exc

    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def _aes_decrypt(blob: bytes, key: bytes) -> bytes:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise VaultError("cryptography package required for vault") from exc

    nonce, ciphertext = blob[:12], blob[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


@dataclass
class KeyVault:
    """Local encrypted key storage with optional RAM-disk backing."""

    bus: ContextBus
    vault_dir: Path | None = None
    vault_path: Path | None = None
    prefer_ramdisk: bool = True
    _unlocked: bool = False
    _keys: dict[str, str] = field(default_factory=dict, repr=False)
    _artifacts: dict[str, bytes] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        base = self.vault_dir or resolve_vault_storage(self.prefer_ramdisk)
        if self.vault_path is None:
            self.vault_path = base / "keystore.enc"
        self._artifact_dir = base / "artifacts"

    def _require_passphrase(self, passphrase: str) -> None:
        if not passphrase:
            raise VaultError("Passphrase required")

    def unlock(self, passphrase: str) -> None:
        self._require_passphrase(passphrase)
        if not self.vault_path.is_file():
            self._keys = {}
            self._unlocked = True
            self.bus.publish("vault.unlocked", {"keys": 0, "new": True}, source="core.vault")
            return

        raw = self.vault_path.read_bytes()
        salt, payload = raw[:16], raw[16:]
        key = _derive_key(passphrase, salt)
        try:
            data = json.loads(_aes_decrypt(payload, key).decode("utf-8"))
        except Exception as exc:
            raise VaultError("Invalid passphrase or corrupted vault") from exc

        if "keys" in data:
            self._keys = {k: v for k, v in data.get("keys", {}).items() if isinstance(v, str)}
            self._artifacts = {k: base64.b64decode(v) for k, v in data.get("artifacts", {}).items()}
        else:
            self._keys = {k: v for k, v in data.items() if isinstance(v, str)}
            self._artifacts = {}
        self._unlocked = True
        self.bus.publish("vault.unlocked", {"keys": len(self._keys)}, source="core.vault")

    def lock(self) -> None:
        self._keys.clear()
        self._artifacts.clear()
        self._unlocked = False
        self.bus.publish("vault.locked", {}, source="core.vault")

    def store_key(self, name: str, private_key_hex: str, passphrase: str) -> None:
        if not self._unlocked:
            self.unlock(passphrase)
        if not private_key_hex.startswith("0x"):
            private_key_hex = "0x" + private_key_hex
        self._keys[name] = private_key_hex
        self._save(passphrase)
        self.bus.publish("vault.key_stored", {"name": name}, source="core.vault")

    def get_key(self, name: str) -> str:
        if not self._unlocked:
            raise VaultError("Vault is locked")
        if name not in self._keys:
            raise VaultError(f"Key not found: {name}")
        return self._keys[name]

    def list_key_names(self) -> list[str]:
        return list(self._keys.keys()) if self._unlocked else []

    def store_artifact(self, name: str, data: bytes, passphrase: str) -> None:
        """Store high-value binary artifact encrypted alongside keys."""
        if not self._unlocked:
            self.unlock(passphrase)
        self._artifacts[name] = data
        self._save(passphrase)
        self.bus.publish("vault.artifact_stored", {"name": name, "bytes": len(data)}, source="core.vault")

    def get_artifact(self, name: str) -> bytes:
        if not self._unlocked:
            raise VaultError("Vault is locked")
        if name not in self._artifacts:
            raise VaultError(f"Artifact not found: {name}")
        return self._artifacts[name]

    def _save(self, passphrase: str) -> None:
        salt = secrets.token_bytes(16)
        key = _derive_key(passphrase, salt)
        payload = json.dumps({"keys": self._keys, "artifacts": {k: base64.b64encode(v).decode() for k, v in self._artifacts.items()}}).encode("utf-8")
        encrypted = _aes_encrypt(payload, key)
        assert self.vault_path is not None
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        self.vault_path.write_bytes(salt + encrypted)

    def status(self) -> dict[str, Any]:
        storage = str(self.vault_path.parent) if self.vault_path else None
        ramdisk = storage.startswith("/dev/shm") if storage else False
        return {
            "unlocked": self._unlocked,
            "key_count": len(self._keys) if self._unlocked else None,
            "artifact_count": len(self._artifacts) if self._unlocked else None,
            "path": str(self.vault_path),
            "storage_backend": "ramdisk" if ramdisk else "disk",
            "exists": self.vault_path.is_file() if self.vault_path else False,
        }
