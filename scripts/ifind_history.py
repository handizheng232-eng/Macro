from datetime import datetime
from typing import Any


def metadata_start_date(metadata: dict[str, Any], code: str) -> str:
    raw = str(metadata.get("sdate") or "")
    if not raw:
        raise ValueError(f"missing disclosure start for {code}")
    try:
        parsed = datetime.strptime(raw, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"invalid disclosure start for {code}: {raw}") from exc
    return parsed.date().isoformat()


def assert_full_history(dates: list[str], metadata: dict[str, Any], code: str) -> None:
    expected = metadata_start_date(metadata, code).replace("-", "")
    if not dates:
        raise ValueError(f"empty history for {code}")
    actual = dates[0].replace("-", "")
    if actual != expected:
        raise ValueError(f"history is truncated for {code}: expected {expected}, got {actual}")
