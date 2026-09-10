from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware 'now' for created_at/updated_at columns."""
    return datetime.now(timezone.utc)
