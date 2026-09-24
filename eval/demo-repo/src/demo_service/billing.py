"""Invoice dates."""

from datetime import UTC, date, datetime


def invoice_date() -> date:
    """Invoices are dated in UTC."""
    return datetime.now(UTC).date()
