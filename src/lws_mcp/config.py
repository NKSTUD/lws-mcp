"""Server settings, read from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.lws.net/v1"

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


class ConfigError(Exception):
    """Raised when the environment does not describe a usable configuration."""


@dataclass(frozen=True)
class Settings:
    login: str
    api_key: str
    test_mode: bool = False
    read_only: bool = False
    enable_purchases: bool = False
    base_url: str = DEFAULT_BASE_URL
    timeout: float = 30.0

    @property
    def allows_writes(self) -> bool:
        return not self.read_only

    @property
    def allows_purchases(self) -> bool:
        return self.enable_purchases and not self.read_only

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        test_mode = _flag(env, "LWS_TEST_MODE")

        login = env.get("LWS_LOGIN", "").strip()
        # In test mode a dedicated test key is preferred, so production and test keys can live side by side.
        api_key = (test_mode and env.get("LWS_TEST_API_KEY", "").strip()) or env.get("LWS_API_KEY", "").strip()

        missing = [name for name, value in (("LWS_LOGIN", login), ("LWS_API_KEY", api_key)) if not value]
        if missing:
            raise ConfigError(f"Missing environment variable(s): {', '.join(missing)}.")

        try:
            timeout = float(env.get("LWS_TIMEOUT", "30"))
        except ValueError as exc:
            raise ConfigError("LWS_TIMEOUT must be a number of seconds.") from exc

        return cls(
            login=login,
            api_key=api_key,
            test_mode=test_mode,
            read_only=_flag(env, "LWS_READ_ONLY"),
            enable_purchases=_flag(env, "LWS_ENABLE_PURCHASES"),
            base_url=env.get("LWS_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            timeout=timeout,
        )


def _flag(env: Mapping[str, str], name: str) -> bool:
    value = env.get(name, "").strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ConfigError(f"{name} must be true or false, got {value!r}.")
