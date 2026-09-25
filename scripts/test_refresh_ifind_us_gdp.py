import json
import math
import unittest
from pathlib import Path

from scripts.refresh_ifind_us_gdp import (
    align_common_periods,
    annualized_growth,
    rebase,
    rolling_mean,
    year_over_year,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "src" / "data" / "usGdpData.json"


class GdpTransformTest(unittest.TestCase):
    def test_annualized_growth(self):
        dates, values = annualized_growth(["20240331", "20240630"], [100.0, 101.0])
        self.assertEqual(dates, ["20240630"])
        self.assertAlmostEqual(values[0], (1.01**4 - 1) * 100)

    def test_year_over_year(self):
        dates = ["20230331", "20230630", "20230930", "20231231", "20240331"]
        out_dates, values = year_over_year(dates, [100, 101, 102, 103, 105])
        self.assertEqual(out_dates, ["20240331"])
        self.assertAlmostEqual(values[0], 5.0)

    def test_rolling_mean(self):
        dates, values = rolling_mean(["1", "2", "3"], [1.0, 2.0, 3.0], 2)
        self.assertEqual(dates, ["2", "3"])
        self.assertEqual(values, [1.5, 2.5])

    def test_rebase(self):
        dates, values = rebase(["20211231", "20220131"], [200.0, 210.0], "202112")
        self.assertEqual(dates, ["20211231", "20220131"])
        self.assertEqual(values, [100.0, 105.0])

    def test_align_common_periods(self):
        periods, aligned = align_common_periods({
            "a": (["20240331", "20240630"], [1.0, 2.0]),
            "b": (["2024-06-30", "20240930"], [3.0, 4.0]),
        }, digits=6)
        self.assertEqual(periods, ["202406"])
        self.assertEqual(aligned, {"a": [2.0], "b": [3.0]})


class GdpDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_contract_and_sections(self):
        self.assertEqual(self.data["schemaVersion"], 1)
        self.assertEqual(self.data["sourceProviders"], ["iFinD EDB"])
        self.assertEqual(self.data["frameworkSource"]["slides"], "94—111")
        self.assertEqual(len(self.data["routeMap"]), 5)
        self.assertEqual(len(self.data["headline"]), 5)
        self.assertEqual(set(self.data["sections"]), {"benchmark", "coreDemand", "incomePrices", "cycleTracking"})

    def test_expected_charts(self):
        charts = {chart["id"]: chart for section in self.data["sections"].values() for chart in section["charts"]}
        self.assertEqual(set(charts), {
            "actual-potential", "supply-legs", "gdp-core-onion", "growth-contributions",
            "gdp-gdi", "nominal-real-deflator", "wei-gdp", "nber-dashboard",
        })
        self.assertEqual(charts["growth-contributions"]["unit"], "百分点")
        self.assertEqual(charts["nber-dashboard"]["rebasedAt"], "2021-12=100")

    def test_ifind_only_and_finite(self):
        for section in self.data["sections"].values():
            for chart in section["charts"]:
                for series in chart["series"]:
                    self.assertEqual(series["source"]["provider"], "iFinD EDB")
                    self.assertEqual(len(series["dates"]), len(series["values"]))
                    self.assertTrue(series["dates"])
                    self.assertTrue(all(math.isfinite(value) for value in series["values"]))

    def test_verified_series_contracts(self):
        all_series = [series for section in self.data["sections"].values() for chart in section["charts"] for series in chart["series"]]
        by_id = {series["id"]: series for series in all_series}
        expected = {
            "real_gdp_saar": "G005120877",
            "potential_gdp": "G011775386",
            "pdfp_saar": "G010701368",
            "gdi_yoy": "G010701498",
            "wei": "G005350606",
        }
        for series_id, code in expected.items():
            self.assertEqual(by_id[series_id]["source"]["code"], code)

    def test_accounting_closures(self):
        checks = self.data["dataQuality"]["accountingChecks"]
        self.assertLessEqual(abs(checks["latestContributionResidualPp"]), 0.02)
        self.assertLessEqual(abs(checks["latestDeflatorIdentityResidual"]), 0.001)
        self.assertLessEqual(abs(checks["latestGdpGdiMeanResidualBillion"]), 0.001)

    def test_availability_is_explicit(self):
        items = {item["id"]: item for item in self.data["availability"]}
        self.assertEqual(items["wei"]["status"], "available")
        self.assertEqual(items["gdpnow"]["status"], "not-integrated")
        self.assertEqual(items["ny-fed-nowcast"]["status"], "not-integrated")
        self.assertIn("未发现", items["gdpnow"]["explanation"])


if __name__ == "__main__":
    unittest.main()
