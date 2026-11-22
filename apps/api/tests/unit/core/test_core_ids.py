"""core.ids: UUIDv7 identifiers (SYSTEM_DESIGN §1: time-ordered ids for all entities)."""

import uuid

import pytest

from aegissoc.core.ids import new_id


@pytest.mark.req("AC-PLAT-10")
def test_new_id_is_a_uuid_version_7() -> None:
    value = new_id()
    assert isinstance(value, uuid.UUID)
    assert value.version == 7


@pytest.mark.req("AC-PLAT-10")
def test_new_ids_are_unique() -> None:
    assert len({new_id() for _ in range(1000)}) == 1000


@pytest.mark.req("AC-PLAT-10")
def test_new_ids_are_time_ordered() -> None:
    ids = [new_id() for _ in range(200)]
    assert ids == sorted(ids)
