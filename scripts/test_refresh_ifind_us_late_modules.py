import json
import math
import unittest
from pathlib import Path

from scripts.refresh_ifind_us_late_modules import difference, pct_change, rolling_sum

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "src" / "data" / "usLateModulesData.json"


class LateModuleTransformTest(unittest.TestCase):
    def test_pct_change(self):
        dates, values = pct_change(["202301", "202302", "202303"], [100.0, 102.0, 103.0], 1)
        self.assertEqual(dates, ["202302", "202303"])
        self.assertAlmostEqual(values[0], 2.0)

    def test_rolling_sum(self):
        dates, values = rolling_sum(["202301", "202302", "202303"], [1.0, 2.0, 3.0], 2)
        self.assertEqual(dates, ["202302", "202303"])
        self.assertEqual(values, [3.0, 5.0])

    def test_difference_aligns_by_period(self):
        dates, values = difference((["20240131", "20240229"], [50.0, 55.0]), (["2024-02-01"], [40.0]))
        self.assertEqual(dates, ["202402"])
        self.assertEqual(values, [15.0])


class LateModuleDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_contract_and_module_counts(self):
        self.assertEqual(self.data["schemaVersion"], 1)
        self.assertEqual(self.data["sourceProviders"], ["iFinD EDB"])
        self.assertEqual(self.data["dataQuality"]["verifiedSeries"], 52)
        self.assertEqual(set(self.data["modules"]), {"housing", "investment", "pmi", "fiscal", "fed"})
        counts = {key: sum(len(section["charts"]) for section in value["sections"]) for key, value in self.data["modules"].items()}
        self.assertEqual(counts, {"housing": 7, "investment": 4, "pmi": 7, "fiscal": 6, "fed": 6})

    def test_all_series_are_verified_and_finite(self):
        for module in self.data["modules"].values():
            self.assertTrue(module["routeMap"])
            self.assertTrue(module["passports"])
            self.assertTrue(module["availability"])
            for section in module["sections"]:
                for chart in section["charts"]:
                    for series in chart["series"]:
                        self.assertEqual(series["source"]["provider"], "iFinD EDB")
                        self.assertTrue(series["source"]["code"].startswith(("G", "M", "L", "S", "W")))
                        self.assertEqual(len(series["dates"]), len(series["values"]))
                        self.assertTrue(series["dates"])
                        self.assertTrue(all(math.isfinite(value) for value in series["values"]))

    def test_ppt_ranges_and_unavailable_items_are_explicit(self):
        expected = {"housing": "130—147", "investment": "148—160", "pmi": "161—174", "fiscal": "175—205", "fed": "206—231"}
        for key, slides in expected.items():
            self.assertEqual(self.data["modules"][key]["slides"], slides)
            self.assertTrue(any(item["status"] != "integrated" for item in self.data["modules"][key]["availability"]))

    def test_fiscal_rolling_deficit_closes_to_outlays_less_receipts(self):
        fiscal = self.data["modules"]["fiscal"]
        charts = {chart["id"]: chart for section in fiscal["sections"] for chart in section["charts"]}
        flows = {item["id"]: item for item in charts["fiscal-flows"]["series"]}
        deficit = charts["fiscal-deficit"]["series"][0]
        receipts = dict(zip(flows["receipts_12m"]["dates"], flows["receipts_12m"]["values"]))
        outlays = dict(zip(flows["outlays_12m"]["dates"], flows["outlays_12m"]["values"]))
        reported = dict(zip(deficit["dates"], deficit["values"]))
        common = sorted(set(receipts) & set(outlays) & set(reported))
        self.assertTrue(common)
        latest = common[-1]
        self.assertAlmostEqual(outlays[latest] - receipts[latest], reported[latest], delta=0.01)


if __name__ == "__main__":
    unittest.main()
