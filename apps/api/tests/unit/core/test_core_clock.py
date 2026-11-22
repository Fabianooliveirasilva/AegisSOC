"""core.clock: injected Clock so time-dependent behaviour is testable (python-backend rules)."""

from datetime import UTC, datetime, timedelta

import pytest

from aegissoc.core.clock import Clock, FrozenClock, SystemClock


@pytest.mark.req("AC-PLAT-10")
def test_system_clock_returns_timezone_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


@pytest.mark.req("AC-PLAT-10")
def test_system_clock_is_close_to_real_time() -> None:
    before = datetime.now(UTC)
    now = SystemClock().now()
    assert before <= now <= datetime.now(UTC)


@pytest.mark.req("AC-PLAT-10")
def test_frozen_clock_does_not_move() -> None:
    start = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    clock = FrozenClock(start)
    assert clock.now() == start
    assert clock.now() == start


@pytest.mark.req("AC-PLAT-10")
def test_frozen_clock_advance_moves_forward() -> None:
    start = datetime(2026, 1, 2, tzinfo=UTC)
    clock = FrozenClock(start)
    clock.advance(timedelta(minutes=31))
    assert clock.now() == start + timedelta(minutes=31)


@pytest.mark.req("AC-PLAT-10")
def test_frozen_clock_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone"):
        FrozenClock(datetime(2026, 1, 2))


@pytest.mark.req("AC-PLAT-10")
def test_both_clocks_satisfy_the_clock_protocol() -> None:
    clocks: list[Clock] = [SystemClock(), FrozenClock(datetime(2026, 1, 2, tzinfo=UTC))]
    assert all(c.now().tzinfo is not None for c in clocks)
