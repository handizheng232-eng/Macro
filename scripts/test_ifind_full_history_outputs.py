import json
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def earliest_rendered_date(filename: str, source_code: str) -> str:
    payload = json.loads((REPO_ROOT / "src" / "data" / filename).read_text(encoding="utf-8"))
    dates: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            source = value.get("source")
            series_dates = value.get("dates")
            if (
                isinstance(source, dict)
                and source.get("code") == source_code
                and isinstance(series_dates, list)
                and series_dates
            ):
                dates.append(str(series_dates[0]))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    if not dates:
        raise AssertionError(f"rendered source {source_code} not found in {filename}")
    return min(dates)


class IfindFullHistoryOutputTest(unittest.TestCase):
    def test_representative_series_are_not_cut_off_at_1990_or_2000(self) -> None:
        expected = {
            ("usGdpData.json", "G002599633"): "19470331",
            ("usEmploymentData.json", "G002600500"): "19390131",
            ("usInflationData.json", "G002600362"): "19140131",
            ("usConsumptionData.json", "DERIVED:G002599638+G002599635"): "194703",
            ("usLateModulesData.json", "G006598549"): "19200131",
        }
        for (filename, source_code), first_date in expected.items():
            with self.subTest(filename=filename, source_code=source_code):
                self.assertEqual(first_date, earliest_rendered_date(filename, source_code))


if __name__ == "__main__":
    unittest.main()
