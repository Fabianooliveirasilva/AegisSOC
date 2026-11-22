"""Application settings (DEPLOYMENT §2).

All settings come from environment variables prefixed ``AEGIS_``. Secrets are never
read from plain environment variables: a ``*_FILE`` variable points at a file (a Docker
secret mounted under ``/run/secrets``) and the value is loaded from it (SR-16).

Only the settings Sprint 1 uses are declared here; later tasks add theirs.
"""

import os
import stat
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import PrivateAttr, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MAX_SECRET_BYTES = 4096


def read_secret_file(path: Path) -> SecretStr:
    """Read a secret from ``path``.

    The file must be a regular file of at most ``MAX_SECRET_BYTES`` (a FIFO or device would
    block startup, a huge file would be loaded into memory). One trailing newline (LF or
    CRLF) is removed; nothing else is stripped. A value that is empty or only whitespace is
    rejected. Errors name the file but never include its content.
    """
    try:
        # O_NONBLOCK so that opening a FIFO cannot block; the type is checked on the fd.
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as exc:
        reason = exc.strerror or "I/O error"
        raise ValueError(f"secret file {path} cannot be read: {reason}") from None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"secret file {path} is not a regular file")
        raw = os.read(fd, MAX_SECRET_BYTES + 1)
    except OSError as exc:
        reason = exc.strerror or "I/O error"
        raise ValueError(f"secret file {path} cannot be read: {reason}") from None
    finally:
        os.close(fd)
    if len(raw) > MAX_SECRET_BYTES:
        raise ValueError(f"secret file {path} is too large (limit {MAX_SECRET_BYTES} bytes)")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(f"secret file {path} is not valid UTF-8") from None
    if text.endswith("\r\n"):
        text = text[:-2]
    elif text.endswith("\n"):
        text = text[:-1]
    if not text.strip():
        raise ValueError(f"secret file {path} is empty or only whitespace")
    return SecretStr(text)


class Settings(BaseSettings):
    """Process configuration. Immutable once created.

    A ``ValidationError`` raised here does not echo submitted values in its message. Code
    that serialises ``exc.errors()`` must pass ``include_input=False``.
    """

    # hide_input_in_errors: a ValidationError must never echo what was submitted (SR-18).
    model_config = SettingsConfigDict(
        env_prefix="AEGIS_", extra="forbid", frozen=True, hide_input_in_errors=True
    )

    env: Literal["local", "ci"] = "local"
    database_url: str = "postgresql+asyncpg://aegis_app@postgres:5432/aegissoc"
    database_password_file: Path | None = None
    redis_url: str = "redis://redis:6379/0"
    redis_password_file: Path | None = None

    # Loaded from the *_FILE settings; private so no environment variable can set them.
    _database_password: SecretStr | None = PrivateAttr(default=None)
    _redis_password: SecretStr | None = PrivateAttr(default=None)

    @field_validator("database_url", "redis_url")
    @classmethod
    def _no_password_in_url(cls, value: str, info: ValidationInfo) -> str:
        name = str(info.field_name)
        variable = f"AEGIS_{name.upper()}"
        try:
            has_password = urlsplit(value).password is not None
        except ValueError:
            raise ValueError(f"{variable} is not a valid URL") from None
        if has_password:
            file_variable = variable.removesuffix("_URL") + "_PASSWORD_FILE"
            raise ValueError(f"{variable} must not contain a password; use {file_variable}")
        return value

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
