import json
import math
import unittest
from pathlib import Path

from scripts.refresh_ifind_us_consumption import align_common, detect_missing_periods, pct_change, standardize

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "src" / "data" / "usConsumptionData.json"


class ConsumptionTransformTest(unittest.TestCase):
    def test_pct_change(self):
        dates, values = pct_change(["20230131", "20230228", "20230331"], [100.0, 101.0, 103.0], 1)
        self.assertEqual(dates, ["20230228", "20230331"])
        self.assertAlmostEqual(values[0], 1.0)
        self.assertAlmostEqual(values[1], 103 / 101 * 100 - 100)

    def test_align_common_uses_period_not_array_position(self):
        periods, aligned = align_common({
            "a": (["20240131", "20240229"], [1.0, 2.0]),
            "b": (["2024-02-29", "20240331"], [3.0, 4.0]),
        })
        self.assertEqual(periods, ["202402"])
        self.assertEqual(aligned, {"a": [2.0], "b": [3.0]})

    def test_standardize_baseline(self):
        dates = [f"{year}{month:02d}28" for year in range(2015, 2020) for month in range(1, 13)]
        values = [float(index) for index in range(len(dates))]
        _, standardized = standardize(dates, values)
        baseline = standardized[:60]
        self.assertAlmostEqual(sum(baseline) / len(baseline), 0.0, places=12)

    def test_missing_months(self):
        self.assertEqual(detect_missing_periods(["20240131", "20240331"], "月"), ["202402"])


class ConsumptionDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.charts = {chart["id"]: chart for section in cls.data["sections"].values() for chart in section["charts"]}

    def test_contract_and_sections(self):
        self.assertEqual(self.data["schemaVersion"], 1)
        self.assertEqual(self.data["sourceProviders"], ["iFinD EDB"])
        self.assertEqual(self.data["frameworkSource"]["slides"], "112—129")
        self.assertEqual(len(self.data["routeMap"]), 5)
        self.assertEqual(len(self.data["headline"]), 6)
        self.assertEqual(set(self.data["sections"]), {"anchor", "retail", "income", "structure", "sentiment"})

    def test_expected_charts(self):
        self.assertEqual(set(self.charts), {
            "pce-gdp-share", "income-consumption", "retail-control-mom", "retail-control-yoy",
            "nominal-real-retail", "saving-rate", "credit-stress", "consumption-shares",
            "consumption-volatility", "confidence-standardized", "soft-hard-divergence",
        })

    def test_ifind_only_and_finite(self):
        for chart in self.charts.values():
            for series in chart["series"]:
                self.assertEqual(series["source"]["provider"], "iFinD EDB")
                self.assertEqual(len(series["dates"]), len(series["values"]))
                self.assertTrue(series["dates"])
                self.assertTrue(all(math.isfinite(value) for value in series["values"]))

    def test_accounting_and_derived_contracts(self):
        checks = self.data["dataQuality"]["accountingChecks"]
        self.assertTrue(checks["latestControlPositive"])
        self.assertAlmostEqual(checks["latestPceComponentShareSum"], 100.0, places=3)
        self.assertGreater(checks["latestPceGdpShare"], 60)
        self.assertLess(checks["latestPceGdpShare"], 75)
        control = self.charts["retail-control-mom"]["series"][1]
        self.assertTrue(control["source"]["code"].startswith("DERIVED:"))
        self.assertIn("汽车", control["transformLabel"])

    def test_unavailable_series_are_not_substituted(self):
        items = {item["id"]: item for item in self.data["availability"]}
        self.assertEqual(items["party"]["status"], "not-integrated")
        self.assertEqual(items["high-frequency"]["status"], "not-integrated")
        self.assertEqual(items["excess-saving"]["status"], "historical-case")


if __name__ == "__main__":
    unittest.main()
