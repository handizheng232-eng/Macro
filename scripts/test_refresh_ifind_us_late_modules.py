import json
import math
import unittest
from pathlib import Path

from scripts.refresh_ifind_us_late_modules import (
    combine_series,
    difference,
    month_end_series,
    parse_fred_csv,
    pct_change,
    rolling_sum,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "src" / "data" / "usLateModulesData.json"


class LateModuleTransformTest(unittest.TestCase):
    def test_parse_fred_csv_compacts_dates_and_drops_missing_values(self):
        dates, values = parse_fred_csv(
            "observation_date,DFF\n1954-07-01,1.13\n1954-07-02,.\n1954-07-03,1.25\n",
            "DFF",
        )
        self.assertEqual(dates, ["19540701", "19540703"])
        self.assertEqual(values, [1.13, 1.25])

    def test_combine_series_preserves_the_disclosed_regime_boundary(self):
        dates, values = combine_series(
            (["20210727", "20210728"], [0.15, 0.15]),
            (["20210729", "20210730"], [0.15, 0.15]),
        )
        self.assertEqual(dates, ["20210727", "20210728", "20210729", "20210730"])
        self.assertEqual(values, [0.15, 0.15, 0.15, 0.15])


    def test_month_end_series_retains_last_valid_observation_per_month(self):
        dates, values = month_end_series(
            (["20240102", "20240131", "20240201", "20240229"], [100.0, 101.0, 102.0, 103.0])
        )
        self.assertEqual(dates, ["20240102", "20240131", "20240229"])
        self.assertEqual(values, [100.0, 101.0, 103.0])

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
        self.assertEqual(self.data["sourceProviders"], ["iFinD EDB", "Federal Reserve Economic Data (FRED)"])
        self.assertEqual(self.data["dataQuality"]["verifiedSeries"], 64)
        self.assertEqual(set(self.data["modules"]), {"housing", "investment", "pmi", "fiscal", "fed"})
        counts = {key: sum(len(section["charts"]) for section in value["sections"]) for key, value in self.data["modules"].items()}
        self.assertEqual(counts, {"housing": 9, "investment": 5, "pmi": 7, "fiscal": 6, "fed": 8})

    def test_all_series_are_verified_and_finite(self):
        for module in self.data["modules"].values():
            self.assertTrue(module["routeMap"])
            self.assertTrue(module["passports"])
            self.assertTrue(module["availability"])
            for section in module["sections"]:
                for chart in section["charts"]:
                    for series in chart["series"]:
                        self.assertIn(series["source"]["provider"], {"iFinD EDB", "Federal Reserve Economic Data (FRED)", "Federal Reserve / FRED + iFinD EDB"})
                        self.assertTrue(series["source"]["code"])
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

    def test_fed_history_uses_official_starts_and_keeps_new_regimes_honest(self):
        fed = self.data["modules"]["fed"]
        charts = {chart["id"]: chart for section in fed["sections"] for chart in section["charts"]}

        policy = {item["id"]: item for item in charts["fed-policy-target"]["series"]}
        self.assertEqual(policy["effr_history"]["dates"][0], "19540701")
        self.assertEqual(policy["fed_target"]["dates"][0], "19820927")
        self.assertEqual(policy["fed_target_lower"]["dates"][0], "20081216")
        self.assertEqual(policy["fed_target_upper"]["dates"][0], "20081216")

        corridor = {item["id"]: item for item in charts["fed-corridor"]["series"]}
        self.assertEqual(corridor["reserve_rate"]["dates"][0], "20081009")
        self.assertEqual(corridor["sofr"]["dates"][0], "20180402")
        self.assertEqual(corridor["onrrp_rate"]["dates"][0], "20130923")

        liquidity = {item["id"]: item for item in charts["fed-liquidity"]["series"]}
        self.assertGreaterEqual(liquidity["onrrp_amount"]["dates"][0], "20130923")

        dollar = {item["id"]: item for item in charts["fed-dollar"]["series"]}
        self.assertEqual(dollar["broad_dollar_legacy"]["dates"][0], "19950104")
        self.assertEqual(dollar["broad_dollar_current"]["dates"][0], "20060102")
        self.assertNotIn("broad_dollar", dollar)

        boundary_labels = {item["label"] for item in fed["availability"]}
        self.assertIn("历史覆盖审计：政策利率", boundary_labels)
        self.assertIn("历史覆盖审计：新制度工具", boundary_labels)
        self.assertIn("历史覆盖审计：资产负债表与美元", boundary_labels)


if __name__ == "__main__":
    unittest.main()
