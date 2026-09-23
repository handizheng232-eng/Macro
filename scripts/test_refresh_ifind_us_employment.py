import json
import math
import unittest
from pathlib import Path

from scripts.refresh_ifind_us_employment import (
    compact_date,
    detect_missing_months,
    fetch_response_series,
    rolling_mean,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "src" / "data" / "usEmploymentData.json"


class IfindEmploymentTransformTests(unittest.TestCase):
    def test_compact_date_normalizes_monthly_and_weekly_dates(self):
        self.assertEqual(compact_date("2026-08-31"), "20260831")
        self.assertEqual(compact_date("20260911"), "20260911")

    def test_fetch_response_series_sorts_reverse_payload_and_skips_blanks(self):
        payload = {
            "code": 1,
            "data": {
                "tables": [{
                    "displayid": "G004786716",
                    "time": ["2026-08-31", "2026-07-31", "2026-06-30"],
                    "value": ["162", "91", ""],
                }],
            },
        }
        dates, values = fetch_response_series(payload, "G004786716")
        self.assertEqual(dates, ["20260731", "20260831"])
        self.assertEqual(values, [91.0, 162.0])

    def test_rolling_mean_keeps_dates_aligned(self):
        dates, values = rolling_mean(
            ["20260101", "20260201", "20260301", "20260401"],
            [1.0, 2.0, 3.0, 7.0],
            3,
        )
        self.assertEqual(dates, ["20260301", "20260401"])
        self.assertEqual(values, [2.0, 4.0])

    def test_detect_missing_months_reports_gap(self):
        self.assertEqual(detect_missing_months(["20260131", "20260331"]), ["202602"])


class IfindEmploymentDatasetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_dataset_is_ifind_only(self):
        self.assertEqual(self.dataset["schemaVersion"], 1)
        self.assertEqual(self.dataset["source"], "iFinD EDB")
        self.assertEqual(self.dataset["sourceProviders"], ["iFinD EDB"])
        serialized = json.dumps(self.dataset, ensure_ascii=False)
        self.assertNotIn("OpenBB", serialized)
        self.assertNotIn("Wind EDB", serialized)
        self.assertNotIn("FRED", serialized)

    def test_headline_has_four_independently_dated_signals(self):
        self.assertEqual(
            [item["id"] for item in self.dataset["headline"]],
            ["payroll", "unemployment", "claims", "wage"],
        )
        for item in self.dataset["headline"]:
            self.assertEqual(item["source"], "iFinD EDB")
            self.assertTrue(item["observation"])
            self.assertTrue(math.isfinite(item["value"]))

    def test_framework_has_supply_slack_demand_and_wages(self):
        self.assertEqual(set(self.dataset["sections"]), {"supply", "slack", "demand", "wages"})
        self.assertEqual(len(self.dataset["sections"]["supply"]["charts"]), 1)
        self.assertEqual(len(self.dataset["sections"]["slack"]["charts"]), 5)
        self.assertEqual(len(self.dataset["sections"]["demand"]["charts"]), 2)
        self.assertEqual(len(self.dataset["sections"]["wages"]["charts"]), 2)

    def test_sector_heatmap_has_twelve_months_and_nine_industries(self):
        table = self.dataset["sections"]["demand"]["sectorHeatmap"]
        self.assertEqual(len(table["periods"]), 12)
        self.assertEqual(len(table["rows"]), 9)
        self.assertEqual(table["periods"], sorted(table["periods"], reverse=True))
        for row in table["rows"]:
            self.assertEqual(len(row["values"]), 12)
            self.assertTrue(row["source"]["code"].startswith("G"))

    def test_beveridge_points_align_unemployment_and_vacancies_by_month(self):
        chart = self.dataset["sections"]["slack"]["charts"][-1]
        self.assertEqual(chart["kind"], "scatter")
        self.assertGreater(len(chart["points"]), 24)
        for point in chart["points"]:
            self.assertRegex(point["period"], r"^\d{6}$")
            self.assertTrue(math.isfinite(point["x"]))
            self.assertTrue(math.isfinite(point["y"]))

    def test_all_rendered_series_are_aligned_and_identified(self):
        charts = [
            chart
            for section in self.dataset["sections"].values()
            for chart in section["charts"]
            if chart["kind"] != "scatter"
        ]
        for chart in charts:
            self.assertIn(chart["kind"], ("line", "bar"))
            for series in chart["series"]:
                self.assertGreater(len(series["dates"]), 0)
                self.assertEqual(len(series["dates"]), len(series["values"]))
                self.assertTrue(all(math.isfinite(value) for value in series["values"]))
                self.assertEqual(series["latestObservation"], series["dates"][-1])
                self.assertEqual(series["latestValue"], series["values"][-1])
                self.assertTrue(series["source"]["code"].startswith("G"))
                self.assertEqual(series["source"]["provider"], "iFinD EDB")

    def test_monthly_gaps_are_disclosed(self):
        quality = self.dataset["dataQuality"]
        self.assertIsInstance(quality["monthlyMissingPeriods"], dict)
        self.assertIn("payroll_total", quality["monthlyMissingPeriods"])


if __name__ == "__main__":
    unittest.main()
