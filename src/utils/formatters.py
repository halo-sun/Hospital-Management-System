"""Shared date formatting utilities.

All date display in the application should go through these helpers
so the format is consistent and changeable in one place.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Union


# Canonical display format for dates (DOB and general date display)
DISPLAY_DATE_FORMAT = "%d-%m-%Y"

# Format for date+time display
DISPLAY_DATETIME_FORMAT = "%d-%m-%Y %H:%M"


def format_date(value: Optional[Union[date, datetime, str]], fmt: str = DISPLAY_DATE_FORMAT) -> str:
    """Format a date value for display.

    Handles date objects, datetime objects, and date strings in common
    formats (YYYY-MM-DD, DD-MM-YYYY, YYYY/MM/DD, DD/MM/YYYY).

    Args:
        value: The date to format.  Accepts date, datetime, or a string
            in any common date format.  None or empty string returns "".
        fmt: Output format string (default: DD-MM-YYYY).

    Returns:
        Formatted date string, or "" if value is None/empty.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return ""
        value = _parse_date_string(value)
        if value is None:
            return ""  # unparseable — return empty rather than crash
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, date):
        return value.strftime(fmt)
    return ""


def format_datetime(value: Optional[Union[datetime, str]]) -> str:
    """Format a datetime value for display (DD-MM-YYYY HH:MM).

    Args:
        value: The datetime to format.

    Returns:
        Formatted datetime string, or "" if value is None/empty.
    """
    return format_date(value, fmt=DISPLAY_DATETIME_FORMAT)


def _parse_date_string(s: str) -> Optional[date]:
    """Parse a date string from common formats.

    Tries DD-MM-YYYY first (our canonical format), then falls back to
    other common formats for backwards compatibility.

    Args:
        s: Date string to parse.

    Returns:
        Parsed date, or None if unparseable.
    """
    for fmt in (DISPLAY_DATE_FORMAT, "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None
