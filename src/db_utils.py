from datetime import datetime, timezone
from importlib import resources
from zoneinfo import ZoneInfo


def get_sql_query_text(query_rel_path: str) -> str:
    return (resources.files("sql") / query_rel_path).read_text()


# Timezone that the hospital sits in (and thus Caboodle records data using)
HOSPITAL_TZ = ZoneInfo("Europe/London")


def utc_to_naive_local(utc_dt: datetime) -> datetime:
    return utc_dt.astimezone(HOSPITAL_TZ).replace(tzinfo=None)


def naive_local_to_utc(naive_dt: datetime) -> datetime:
    if naive_dt.tzinfo is not None:
        raise ValueError(f"datetime {naive_dt} is not a tz-naive datetime")
    return naive_dt.replace(tzinfo=HOSPITAL_TZ).astimezone(timezone.utc)


def validate_args_must_be_utc(*args):
    for a in args:
        if not isinstance(a, datetime):
            raise TypeError(f"Argument {a} must be a datetime")
        if a.tzinfo is None or a.tzinfo != timezone.utc:
            raise TypeError(f"Argument {a} must be have a UTC timezone")
