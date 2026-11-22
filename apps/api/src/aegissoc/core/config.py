"""Application settings (DEPLOYMENT §2).

All settings come from environment variables prefixed ``AEGIS_``. Secrets are never
read from plain environment variables: a ``*_FILE`` variable points at a file (a Docker
secret mounted under ``/run/secrets``) and the value is loaded from it (SR-16).

Only the settings Sprint 1 uses are declared here; later tasks add theirs.
"""

from pathlib import Path
from typing import Literal, Self

from pydantic import PrivateAttr, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def read_secret_file(path: Path) -> SecretStr:
    """Read a secret from ``path``.

    One trailing newline is removed (a file edited by hand often has one); nothing else
    is stripped. Errors name the file but never include its content.
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        reason = exc.strerror or "I/O error"
        raise ValueError(f"secret file {path} cannot be read: {reason}") from None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(f"secret file {path} is not valid UTF-8") from None
    text = text.removesuffix("\n")
    if not text:
        raise ValueError(f"secret file {path} is empty")
    return SecretStr(text)


class Settings(BaseSettings):
    """Process configuration. Immutable once created."""

    model_config = SettingsConfigDict(env_prefix="AEGIS_", extra="forbid", frozen=True)

    env: Literal["local", "ci"] = "local"
    database_url: str = "postgresql+asyncpg://aegis_app@postgres:5432/aegissoc"
    database_password_file: Path | None = None
    redis_url: str = "redis://redis:6379/0"
    redis_password_file: Path | None = None

    # Loaded from the *_FILE settings; private so no environment variable can set them.
    _database_password: SecretStr | None = PrivateAttr(default=None)
    _redis_password: SecretStr | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _load_secrets(self) -> Self:
        self._database_password = self._load(
            "AEGIS_DATABASE_PASSWORD_FILE", self.database_password_file
        )
        self._redis_password = self._load("AEGIS_REDIS_PASSWORD_FILE", self.redis_password_file)
        return self

    def _load(self, variable: str, path: Path | None) -> SecretStr | None:
        if path is None:
            if self.env == "ci":
                return None
            raise ValueError(f"{variable} must be set unless AEGIS_ENV=ci")
        try:
            return read_secret_file(path)
        except ValueError as exc:
            raise ValueError(f"{variable}: {exc}") from None

    @property
    def database_password(self) -> SecretStr | None:
        return self._database_password

    @property
    def redis_password(self) -> SecretStr | None:
        return self._redis_password
