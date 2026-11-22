"""Entity identifiers: UUIDv7 (time-ordered), see SYSTEM_DESIGN §1."""

import uuid

import uuid6


def new_id() -> uuid.UUID:
    """Return a new UUIDv7 as a standard-library `uuid.UUID`."""
    return uuid.UUID(int=uuid6.uuid7().int)
