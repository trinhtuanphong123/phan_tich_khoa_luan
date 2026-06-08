from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal


VN_TIMEZONE = timezone(timedelta(hours=7))
VN_MORNING_START = time(9, 0)
VN_MORNING_END = time(11, 30)
VN_AFTERNOON_START = time(13, 0)
VN_AFTERNOON_END = time(14, 45)

CurrentSession = Literal["morning", "afternoon"]


def _to_vn_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(VN_TIMEZONE)


def is_trading_day(value: date | datetime) -> bool:
    if isinstance(value, datetime):
        value = _to_vn_datetime(value).date()
    return value.weekday() < 5


def get_current_session(value: datetime) -> CurrentSession | None:
    value = _to_vn_datetime(value)

    if not is_trading_day(value):
        return None

    current_time = value.time()
    if VN_MORNING_START <= current_time < VN_MORNING_END:
        return "morning"
    if VN_AFTERNOON_START <= current_time < VN_AFTERNOON_END:
        return "afternoon"
    return None


def is_trading_time(value: datetime) -> bool:
    return get_current_session(value) is not None


def _parse_interval(interval: str) -> tuple[int, str]:
    match = re.fullmatch(r"(\d+)([mh])", interval)
    if match is None:
        raise ValueError(f"unsupported interval: {interval}")

    return int(match.group(1)), match.group(2)


def get_closed_bar_time(now: datetime, interval: str = "5m") -> datetime:
    now = _to_vn_datetime(now)
    amount, unit = _parse_interval(interval)

    now = now.replace(second=0, microsecond=0)

    if unit == "h":
        closed_hour = (now.hour // amount) * amount
        return now.replace(hour=closed_hour, minute=0)

    closed_minute = (now.minute // amount) * amount
    return now.replace(minute=closed_minute)


def get_fetch_window(
    now: datetime,
    lookback_minutes: int,
    delay_minutes: int,
) -> tuple[datetime, datetime]:
    now = _to_vn_datetime(now)
    end = get_closed_bar_time(now - timedelta(minutes=delay_minutes))
    start = end - timedelta(minutes=lookback_minutes)
    return start, end


def clip_window_to_trading_sessions(
    start: datetime,
    end: datetime,
) -> tuple[datetime, datetime] | None:
    start = _to_vn_datetime(start)
    end = _to_vn_datetime(end)

    if start >= end:
        return None

    clipped_segments: list[tuple[datetime, datetime]] = []
    current_day = start.date()
    last_day = end.date()

    while current_day <= last_day:
        if is_trading_day(current_day):
            morning_start = datetime.combine(current_day, VN_MORNING_START, tzinfo=start.tzinfo)
            morning_end = datetime.combine(current_day, VN_MORNING_END, tzinfo=start.tzinfo)
            afternoon_start = datetime.combine(current_day, VN_AFTERNOON_START, tzinfo=start.tzinfo)
            afternoon_end = datetime.combine(current_day, VN_AFTERNOON_END, tzinfo=start.tzinfo)

            for session_start, session_end in (
                (morning_start, morning_end),
                (afternoon_start, afternoon_end),
            ):
                clipped_start = max(start, session_start)
                clipped_end = min(end, session_end)
                if clipped_start < clipped_end:
                    clipped_segments.append((clipped_start, clipped_end))

        current_day += timedelta(days=1)

    if not clipped_segments:
        return None

    for clipped_start, clipped_end in reversed(clipped_segments):
        if clipped_start <= end <= clipped_end:
            return clipped_start, clipped_end

    return clipped_segments[-1]
