"""core.vault — encrypted local key management (AES-256)."""

from hexstrike.core.vault.keystore import KeyVault, VaultError

__all__ = ["KeyVault", "VaultError"]
