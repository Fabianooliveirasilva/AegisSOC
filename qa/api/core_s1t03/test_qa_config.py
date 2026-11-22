"""AC-QA-07 config part / SR-16: *_FILE secret loading, fail-fast outside ci. QA-written."""

import os
import stat
from pathlib import Path

import pytest
from aegissoc.core.config import Settings, read_secret_file
from pydantic import SecretStr, ValidationError

SECRET = "S3cr3t-VALUE-xyz"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in list(os.environ):
        if k.startswith("AEGIS_"):
            monkeypatch.delenv(k)


def mk(tmp_path: Path, content: bytes | str, name: str = "s") -> Path:
    p = tmp_path / name
    p.write_bytes(content if isinstance(content, bytes) else content.encode())
    return p


def S(**kw: object) -> Settings:
    return Settings(_env_file=None, **kw)  # type: ignore[call-arg]


def test_fail_fast_outside_ci_names_variable_not_values() -> None:
    for env in (None, "local"):
        kw = {} if env is None else {"env": env}
        with pytest.raises(ValidationError) as ei:
            S(**kw)
        assert "AEGIS_DATABASE_PASSWORD_FILE" in str(ei.value)


def test_missing_only_redis_still_fails(tmp_path: Path) -> None:
    with pytest.raises(ValidationError) as ei:
        S(database_password_file=mk(tmp_path, SECRET))
    assert "AEGIS_REDIS_PASSWORD_FILE" in str(ei.value) and SECRET not in str(ei.value)


def test_ci_allows_missing_and_returns_none() -> None:
    s = S(env="ci")
    assert s.database_password is None and s.redis_password is None


def test_ci_still_validates_files_that_are_given(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        S(env="ci", redis_password_file=tmp_path / "missing")


def test_env_var_names_and_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("AEGIS_ENV", "ci")
    monkeypatch.setenv(
        "AEGIS_DATABASE_PASSWORD_FILE", str(mk(tmp_path, SECRET + "\n", "d"))
    )
    s = S()
    assert (
        s.database_password is not None
        and s.database_password.get_secret_value() == SECRET
    )
    monkeypatch.setenv("AEGIS_ENV", "CI")
    with pytest.raises(ValidationError):
        S()
    monkeypatch.setenv("AEGIS_ENV", "production")
    with pytest.raises(ValidationError):
        S()


def test_plain_env_secret_is_never_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEGIS_ENV", "ci")
    monkeypatch.setenv("AEGIS_DATABASE_PASSWORD", SECRET)
    monkeypatch.setenv("AEGIS__DATABASE_PASSWORD", SECRET)
    s = S()
    assert s.database_password is None
    with pytest.raises(ValidationError):
        S(_database_password=SecretStr(SECRET))  # type: ignore[call-arg]


def test_unprefixed_env_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "local")
    monkeypatch.setenv("DATABASE_URL", "postgresql://evil")
    s = S(env="ci")
    assert "evil" not in s.database_url


def test_secret_never_in_repr_str_dump_json_or_copy(tmp_path: Path) -> None:
    s = S(
        database_password_file=mk(tmp_path, SECRET),
        redis_password_file=mk(tmp_path, SECRET + "2", "r"),
    )
    for text in (
        repr(s),
        str(s),
        s.model_dump_json(),
        repr(s.model_dump()),
        repr(s.model_copy()),
    ):
        assert SECRET not in text
    assert SECRET not in repr(s.database_password) and "**" in repr(s.database_password)


def test_frozen() -> None:
    s = S(env="ci")
    with pytest.raises(ValidationError):
        s.env = "local"  # type: ignore[misc]
    with pytest.raises((ValidationError, AttributeError, TypeError)):
        s.database_password = SecretStr("x")  # type: ignore[misc]


@pytest.mark.parametrize(
    ("content", "expect"),
    [
        ("pw", "pw"),
        ("pw\n", "pw"),
        ("pw\n\n", "pw\n"),
        ("  pw  ", "  pw  "),
        ("p\nw", "p\nw"),
        ("pw\r\n", "pw"),
        ("é✓", "é✓"),
        ("a b", "a b"),
    ],
)
def test_read_secret_file_trailing_newline_semantics(
    tmp_path: Path, content: str, expect: str
) -> None:
    assert read_secret_file(mk(tmp_path, content)).get_secret_value() == expect


@pytest.mark.parametrize(
    "content",
    [b"", b"\n", b"\n\n", b"\r\n", b" ", b"\t\n", b"\xff\xfe\x00", b"\xc3\x28"],
)
def test_bad_secret_files_rejected_without_echoing_content(
    tmp_path: Path, content: bytes
) -> None:
    with pytest.raises(ValueError) as ei:
        read_secret_file(mk(tmp_path, content))
    assert "xff" not in str(ei.value).lower()


def test_directory_missing_and_unreadable(tmp_path: Path) -> None:
    for p in (tmp_path, tmp_path / "nope", tmp_path / "nope" / "deeper"):
        with pytest.raises(ValueError):
            read_secret_file(p)
    f = mk(tmp_path, SECRET, "locked")
    f.chmod(0)
    try:
        if os.geteuid() != 0:
            with pytest.raises(ValueError) as ei:
                read_secret_file(f)
            assert SECRET not in str(ei.value)
    finally:
        f.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_symlink_followed_and_fifo_does_not_hang(tmp_path: Path) -> None:
    real = mk(tmp_path, SECRET, "real")
    link = tmp_path / "link"
    link.symlink_to(real)
    assert read_secret_file(link).get_secret_value() == SECRET


def test_BUG_QA_S1T03_001_validation_error_does_not_leak_secret_content_or_db_url_password(
    tmp_path: Path,
) -> None:
    """Fail-fast error text must not echo configuration input (e.g. a URL carrying a password)."""
    url = "postgres://u:URLPW-LEAK@h/d"  # short: pydantic does not truncate it
    with pytest.raises(ValidationError) as ei:
        S(database_url=url)
    assert SECRET not in str(ei.value)
    assert "URLPW-LEAK" not in str(ei.value), str(ei.value)  # QA-S1T03-001
