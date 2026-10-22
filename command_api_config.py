"""Configuration for the legacy command-execution API."""

from dataclasses import dataclass
import hmac
from typing import Mapping, Optional


@dataclass(frozen=True)
class CommandApiConfig:
    """Validated settings that control access to the legacy command API."""

    enabled: bool
    token: Optional[str]
    host: str

    def accepts_token(self, candidate: Optional[str]) -> bool:
        """Return whether a request token matches the configured secret."""
        return bool(
            self.enabled
            and self.token
            and candidate
            and hmac.compare_digest(
                candidate.encode("utf-8"), self.token.encode("utf-8")
            )
        )


def load_command_api_config(
    environment: Mapping[str, str],
) -> CommandApiConfig:
    """Parse and validate command API settings from an environment mapping."""
    enabled_value = environment.get("HEXSTRIKE_COMMAND_API_ENABLED", "false")
    normalized_enabled = enabled_value.strip().lower()
    if normalized_enabled in {"1", "true", "yes", "on"}:
        enabled = True
    elif normalized_enabled in {"0", "false", "no", "off", ""}:
        enabled = False
    else:
        raise ValueError("HEXSTRIKE_COMMAND_API_ENABLED must be a boolean")

    token = environment.get("HEXSTRIKE_COMMAND_API_TOKEN")
    host = environment.get("HEXSTRIKE_HOST", "127.0.0.1")
    if enabled:
        if not token or not token.strip():
            raise ValueError(
                "HEXSTRIKE_COMMAND_API_TOKEN is required when the command API is enabled"
            )
        if host not in {"127.0.0.1", "localhost"}:
            raise ValueError(
                "HEXSTRIKE_HOST must be 127.0.0.1 or localhost when the command API is enabled"
            )

    return CommandApiConfig(enabled=enabled, token=token, host=host)
