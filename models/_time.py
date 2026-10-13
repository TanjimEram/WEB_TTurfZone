from datetime import datetime, timezone


def utcnow() -> datetime:
    """Timezone-aware 'now' for created_at/updated_at columns.

    Convention: DateTime columns always hold UTC. PostgreSQL (timestamptz) keeps the
    offset; MariaDB (DATETIME) and SQLite store no offset at all, and PyMySQL silently
    DROPS it on write without converting. So only ever write UTC values (this function),
    never services.slots.now_dhaka(), and treat naive values read back as UTC.
    """
    return datetime.now(timezone.utc)
