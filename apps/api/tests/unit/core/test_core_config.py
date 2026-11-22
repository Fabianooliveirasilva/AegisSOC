"""core.config: AEGIS_-prefixed settings, *_FILE secret loading, fail fast outside ci."""

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
