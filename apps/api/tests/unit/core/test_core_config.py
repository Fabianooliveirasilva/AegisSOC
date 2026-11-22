"""core.config: AEGIS_-prefixed settings, *_FILE secret loading, fail fast outside ci."""

import contextlib
import os
import signal
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from aegissoc.core.config import Settings, read_secret_file


def _secrets(
    tmp_path: Path, db: str = "db-secret-value", redis: str = "redis-secret-value"
) -> dict[str, str]:
    db_file = tmp_path / "db"
    redis_file = tmp_path / "redis"
    db_file.write_text(db)
    redis_file.write_text(redis)
    return {
        "AEGIS_DATABASE_PASSWORD_FILE": str(db_file),
        "AEGIS_REDIS_PASSWORD_FILE": str(redis_file),
    }


def _load(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> Settings:
    for key in [k for k in list(__import__("os").environ) if k.startswith("AEGIS_")]:
        monkeypatch.delenv(key)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings()


@pytest.mark.req("AC-QA-07")
def test_defaults_follow_the_deployment_table(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    s = _load(monkeypatch, _secrets(tmp_path))
    assert s.env == "local"
    assert s.database_url == "postgresql+asyncpg://aegis_app@postgres:5432/aegissoc"
    assert s.redis_url == "redis://redis:6379/0"


@pytest.mark.req("AC-QA-07")
def test_environment_variables_override_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env = _secrets(tmp_path) | {"AEGIS_REDIS_URL": "redis://elsewhere:6380/1"}
    assert _load(monkeypatch, env).redis_url == "redis://elsewhere:6380/1"


@pytest.mark.req("SR-16")
def test_secrets_are_read_from_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    s = _load(monkeypatch, _secrets(tmp_path))
    assert s.database_password is not None
    assert s.database_password.get_secret_value() == "db-secret-value"
    assert s.redis_password is not None
    assert s.redis_password.get_secret_value() == "redis-secret-value"


@pytest.mark.req("SR-18")
def test_secret_values_never_appear_in_repr_or_dump(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    s = _load(monkeypatch, _secrets(tmp_path))
    rendered = repr(s) + str(s) + s.model_dump_json() + str(s.model_dump())
    assert "db-secret-value" not in rendered
    assert "redis-secret-value" not in rendered


@pytest.mark.req("SR-16")
def test_secret_cannot_be_supplied_directly_through_the_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env = _secrets(tmp_path) | {"AEGIS_DATABASE_PASSWORD": "plain-text-in-env"}
    s = _load(monkeypatch, env)
    assert s.database_password is not None
    assert s.database_password.get_secret_value() == "db-secret-value"


@pytest.mark.req("SR-16")
def test_missing_secret_file_setting_fails_fast_outside_ci(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValidationError, match="AEGIS_DATABASE_PASSWORD_FILE"):
        _load(monkeypatch, {})


@pytest.mark.req("SR-16")
def test_unreadable_secret_file_fails_fast(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env = _secrets(tmp_path) | {"AEGIS_REDIS_PASSWORD_FILE": str(tmp_path / "does-not-exist")}
    with pytest.raises(ValidationError, match="AEGIS_REDIS_PASSWORD_FILE"):
        _load(monkeypatch, env)


@pytest.mark.req("SR-16")
def test_empty_secret_file_fails_fast(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env = _secrets(tmp_path, db="")
    with pytest.raises(ValidationError, match="empty"):
        _load(monkeypatch, env)


@pytest.mark.req("SR-16")
def test_ci_environment_may_omit_secret_files(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _load(monkeypatch, {"AEGIS_ENV": "ci"})
    assert s.env == "ci"
    assert s.database_password is None
    assert s.redis_password is None


@pytest.mark.req("AC-QA-07")
def test_unknown_environment_name_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(ValidationError):
        _load(monkeypatch, _secrets(tmp_path) | {"AEGIS_ENV": "production"})


@pytest.mark.req("SR-16")
def test_read_secret_file_strips_one_trailing_newline_only(tmp_path: Path) -> None:
    path = tmp_path / "s"
    path.write_text("abc \n")
    assert read_secret_file(path).get_secret_value() == "abc "


@pytest.mark.req("SR-16")
def test_read_secret_file_error_does_not_leak_content(tmp_path: Path) -> None:
    path = tmp_path / "s"
    path.write_bytes(b"\xff\xfe-not-utf8-secret")
    with pytest.raises(ValueError, match="UTF-8") as exc:
        read_secret_file(path)
    assert "not-utf8-secret" not in str(exc.value)


@contextlib.contextmanager
def _deadline(seconds: int) -> Iterator[None]:
    def on_alarm(_signum: int, _frame: object) -> None:
        raise TimeoutError("operation blocked")

    previous = signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


@pytest.mark.req("SR-18")
def test_validation_errors_never_echo_the_submitted_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env = _secrets(tmp_path) | {"AEGIS_ENV": "bogus-PWLEAK"}
    with pytest.raises(ValidationError) as exc:
        _load(monkeypatch, env)
    assert "PWLEAK" not in str(exc.value)
    # errors() still carries `input` unless asked otherwise: callers that serialise it must
    # pass include_input=False (documented on Settings).
    assert all("input" not in e for e in exc.value.errors(include_input=False))


@pytest.mark.req("SR-16")
@pytest.mark.parametrize(
    ("variable", "url"),
    [
        ("AEGIS_REDIS_URL", "redis://:PWLEAK@r:6379/0"),
        ("AEGIS_REDIS_URL", "redis://user:PWLEAK@r:6379/0"),
        ("AEGIS_DATABASE_URL", "postgresql+asyncpg://u:PWLEAK@h:5432/db"),
    ],
)
def test_urls_with_embedded_passwords_are_rejected_without_echoing_them(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, variable: str, url: str
) -> None:
    with pytest.raises(ValidationError, match=variable) as exc:
        _load(monkeypatch, _secrets(tmp_path) | {variable: url})
    assert "PWLEAK" not in str(exc.value)
    assert "_FILE" in str(exc.value)


@pytest.mark.req("SR-16")
def test_urls_with_a_username_but_no_password_are_accepted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env = _secrets(tmp_path) | {"AEGIS_DATABASE_URL": "postgresql+asyncpg://aegis_app@h:5432/db"}
    assert _load(monkeypatch, env).database_url.endswith("@h:5432/db")


@pytest.mark.req("SR-16")
def test_fifo_secret_file_is_rejected_instead_of_blocking(tmp_path: Path) -> None:
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with _deadline(5), pytest.raises(ValueError, match="not a regular file"):
        read_secret_file(fifo)


@pytest.mark.req("SR-16")
def test_directory_and_device_secret_files_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not a regular file"):
        read_secret_file(tmp_path)
    with pytest.raises(ValueError, match="not a regular file"):
        read_secret_file(Path("/dev/null"))


@pytest.mark.req("SR-16")
def test_oversized_secret_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "big"
    path.write_text("x" * 5000)
    with pytest.raises(ValueError, match="too large"):
        read_secret_file(path)
    path.write_text("x" * 4096)
    assert len(read_secret_file(path).get_secret_value()) == 4096


@pytest.mark.req("SR-16")
def test_secret_file_symlink_to_a_regular_file_is_followed(tmp_path: Path) -> None:
    target = tmp_path / "real"
    target.write_text("linked-secret")
    link = tmp_path / "link"
    link.symlink_to(target)
    assert read_secret_file(link).get_secret_value() == "linked-secret"


@pytest.mark.req("SR-16")
@pytest.mark.parametrize(
    ("content", "expected"), [("abc\r\n", "abc"), ("abc\n", "abc"), ("abc", "abc")]
)
def test_secret_file_line_endings_are_stripped_once(
    tmp_path: Path, content: str, expected: str
) -> None:
    path = tmp_path / "s"
    path.write_bytes(content.encode())
    assert read_secret_file(path).get_secret_value() == expected


@pytest.mark.req("SR-16")
@pytest.mark.parametrize("content", ["\n", "\n\n", "  ", " \n", "\r\n", "\t"])
def test_whitespace_only_secret_files_are_rejected(tmp_path: Path, content: str) -> None:
    path = tmp_path / "s"
    path.write_text(content)
    with pytest.raises(ValueError, match="empty"):
        read_secret_file(path)


@pytest.mark.req("SR-16")
def test_malformed_url_is_rejected_without_echoing_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(ValidationError, match="not a valid URL") as exc:
        _load(monkeypatch, _secrets(tmp_path) | {"AEGIS_REDIS_URL": "redis://[PWLEAK"})
    assert "PWLEAK" not in str(exc.value)


@pytest.mark.req("SR-16")
def test_io_error_while_reading_a_secret_names_the_file_not_the_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "s"
    path.write_text("never-shown")

    def failing_read(_fd: int, _size: int) -> bytes:
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(os, "read", failing_read)
    with pytest.raises(ValueError, match="cannot be read: Input/output error") as exc:
        read_secret_file(path)
    assert "never-shown" not in str(exc.value)
