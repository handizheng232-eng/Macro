import json
import math
import unittest
from pathlib import Path

from scripts.refresh_ifind_us_inflation import (
    compact_date,
    detect_missing_months,
    difference_series,
    fetch_response_series,
    monthly_average,
    shift_months,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPO_ROOT / "src" / "data" / "usInflationData.json"


class IfindTransformTests(unittest.TestCase):
    def test_compact_date_normalizes_year_month_day(self):
        self.assertEqual(compact_date("2026-08-31"), "20260831")
        self.assertEqual(compact_date("20260831"), "20260831")

    def test_fetch_response_series_parses_reversed_tables_and_skips_blanks(self):
        payload = {
            "code": 1,
            "data": {
                "dataVol": 3,
                "tables": [{
                    "displayid": "G002600362",
                    "time": ["2026-08-31", "2026-07-31", "2026-06-30"],
                    "value": ["3.4", "3.2", ""],
                }],
            },
        }
        dates, values = fetch_response_series(payload, "G002600362")
        self.assertEqual(dates, ["20260731", "20260831"])
        self.assertEqual(values, [3.2, 3.4])

    def test_detect_missing_months_reports_calendar_gap(self):
        self.assertEqual(detect_missing_months(["20250901", "20251101", "20251201"]), ["202510"])

    def test_monthly_average_and_leading_date_shift_are_deterministic(self):
        dates, values = monthly_average(
            ["20260102", "20260109", "20260206"],
            [3.0, 5.0, 7.0],
        )
        self.assertEqual(dates, ["20260131", "20260228"])
        self.assertEqual(values, [4.0, 7.0])
        self.assertEqual(shift_months(["20251130", "20251231"], 2), ["20260131", "20260228"])

    def test_difference_series_aligns_by_month_and_preserves_gaps(self):
        dates, values = difference_series(
            (["20250131", "20250228", "20250430"], [3.0, 3.2, 3.4]),
            (["20250131", "20250331", "20250430"], [2.5, 2.7, 2.8]),
        )
        self.assertEqual(dates, ["20250131", "20250430"])
        self.assertEqual(values, [0.5, 0.6])


class IfindDatasetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def test_dataset_is_ifind_only(self):
        self.assertEqual(self.dataset["schemaVersion"], 5)
        self.assertEqual(self.dataset["source"], "iFinD EDB")
        self.assertEqual(self.dataset["sourceProviders"], ["iFinD EDB"])
        serialized = json.dumps(self.dataset, ensure_ascii=False)
        self.assertNotIn("OpenBB", serialized)
        self.assertNotIn("Wind EDB", serialized)
        self.assertNotIn("FRED public series", serialized)

    def test_headline_covers_actual_survey_and_implied(self):
        self.assertEqual([item["id"] for item in self.dataset["headline"]], ["actual", "survey", "implied"])
        self.assertEqual(self.dataset["headline"][2]["title"], "5y5y远期通胀补偿")
        for item in self.dataset["headline"]:
            self.assertEqual(item["source"], "iFinD EDB")

    def test_ppt_research_route_and_series_passports_are_explicit(self):
        framework = self.dataset["framework"]
        self.assertEqual(
            [step["id"] for step in framework["route"]],
            ["headline", "anatomy", "underlying", "expectations", "leading", "scenario"],
        )
        self.assertEqual({item["id"] for item in framework["passports"]}, {"cpi", "pce"})
        self.assertEqual(
            [item["id"] for item in framework["attribution"]],
            ["demand-gap", "supply-shock", "expectation-anchor", "policy-reaction"],
        )
        self.assertEqual(len(framework["oilShockFramework"]["steps"]), 5)
        self.assertEqual(framework["oilShockFramework"]["evidenceType"], "PPT教学框架，不是实时预测")
        for item in framework["passports"]:
            self.assertTrue(item["publisher"])
            self.assertTrue(item["frequency"])
            self.assertTrue(item["revision"])
            self.assertTrue(item["role"])
        self.assertGreaterEqual(len(framework["indicatorDictionary"]), 12)
        for item in framework["indicatorDictionary"]:
            self.assertTrue(item["definition"])
            self.assertTrue(item["frequency"])
            self.assertTrue(item["unit"])
            self.assertTrue(item["transformation"])
            self.assertTrue(item["interpretation"])
            self.assertTrue(item["caveat"])

    def test_actual_inflation_has_cpi_and_pce_trends_and_detail(self):
        self.assertEqual(len(self.dataset["actual"]["cpiTrend"]["series"]), 4)
        self.assertEqual(len(self.dataset["actual"]["pceTrend"]["series"]), 4)
        rows = self.dataset["actual"]["cpiDetail"]["rows"]
        self.assertEqual(len(rows), 7)
        self.assertEqual([row["label"] for row in rows], [
            "所有项目", "食品", "能源", "核心", "商品(不含食品能源)", "服务(不含能源)", "住房",
        ])
        for row in rows:
            self.assertTrue(math.isfinite(row["yoy"]))
            self.assertTrue(math.isfinite(row["mom"]))
            self.assertIn(row["nature"], ("总量", "波动项", "周期分项", "结构分项"))
            self.assertTrue(row["source"]["code"].startswith("G"))
            self.assertEqual(row["observation"], row["source"]["latestObservation"])
            self.assertNotEqual(row["observation"][-2:], "01")

    def test_core_split_chart_and_cycle_structure_table(self):
        core_split = self.dataset["actual"]["coreSplit"]["series"]
        self.assertEqual(len(core_split), 3)
        self.assertEqual([item["label"] for item in core_split], ["核心商品", "住房", "超级核心服务"])
        cycle_rows = self.dataset["actual"]["cycleStructure"]["rows"]
        self.assertEqual(len(cycle_rows), 3)
        self.assertEqual([row["classification"] for row in cycle_rows], ["周期", "半结构", "结构"])
        for row in cycle_rows:
            self.assertIn(row["nature"], ("周期分项", "半结构分项", "结构分项"))
            self.assertTrue(math.isfinite(row["peak"]))
            self.assertTrue(math.isfinite(row["latest"]))
            self.assertTrue(math.isfinite(row["annualVolatility"]))
            self.assertTrue(math.isfinite(row["halfLifeYears"]))
            self.assertTrue(math.isfinite(row["wageCorrelation"]))
            self.assertTrue(0 <= row["retrace"] <= 100)

    def test_detailed_cpi_heatmap_has_twelve_months_and_hierarchy(self):
        heatmap = self.dataset["actual"]["cpiHeatmap"]
        self.assertEqual(len(heatmap["periods"]), 12)
        self.assertGreaterEqual(len(heatmap["rows"]), 18)
        self.assertEqual(heatmap["periods"], sorted(heatmap["periods"], reverse=True))
        groups = {row["group"] for row in heatmap["rows"]}
        self.assertTrue({"总量", "食品", "能源", "核心商品", "核心服务", "超级核心"}.issubset(groups))
        for row in heatmap["rows"]:
            self.assertEqual(len(row["yoy"]), 12)
            self.assertEqual(len(row["mom"]), 12)
            self.assertTrue(math.isfinite(row["weight"]))

    def test_contribution_supercore_and_wage_modules_are_present(self):
        contributions = self.dataset["actual"]["cpiContributions"]
        self.assertEqual(len(contributions["series"]), 5)
        self.assertEqual(
            {s["label"] for s in contributions["series"]},
            {"核心服务", "核心商品", "食品", "能源", "残差/未覆盖"},
        )
        self.assertTrue(all(s["source"]["rawUnit"] == "百分点" for s in contributions["series"]))
        total_map = dict(zip(contributions["totalSeries"]["dates"], contributions["totalSeries"]["values"]))
        component_maps = [dict(zip(s["dates"], s["values"])) for s in contributions["series"]]
        common = set(total_map).intersection(*(set(item) for item in component_maps))
        self.assertGreater(len(common), 0)
        for date in common:
            self.assertAlmostEqual(sum(item[date] for item in component_maps), total_map[date], places=8)
        supercore = self.dataset["actual"]["supercoreMom"]["series"]
        self.assertEqual([s["label"] for s in supercore], ["CPI口径", "PCE口径"])
        self.assertEqual(supercore[1]["source"]["rawUnit"], "2017年=100")
        self.assertIn("环比", supercore[1]["source"]["transformation"])
        wage = self.dataset["actual"]["wageAnchor"]["series"]
        self.assertEqual([s["id"] for s in wage], ["eci_wage_yoy", "unit_labor_cost_yoy", "cpi_supercore_yoy"])
        self.assertEqual([s["frequency"] for s in wage], ["季", "季", "月"])

    def test_ppt_actual_inflation_modules_cover_structure_and_measurement(self):
        actual = self.dataset["actual"]
        self.assertEqual([s["id"] for s in actual["goodsServices"]["series"]], ["cpi_goods_yoy", "cpi_services_yoy"])
        self.assertEqual([s["id"] for s in actual["shelterLag"]["series"]], ["rent_yoy", "oer_yoy"])
        self.assertEqual([s["id"] for s in actual["underlying"]["series"]], ["core_cpi_yoy", "median_cpi_yoy", "trimmed_mean_cpi_yoy"])
        self.assertEqual([s["id"] for s in actual["cpiPceGap"]["series"]], ["core_cpi_yoy", "core_pce_yoy", "core_cpi_pce_gap"])
        seasonality = actual["januaryEffect"]
        self.assertEqual(seasonality["months"], list(range(1, 13)))
        self.assertEqual([s["id"] for s in seasonality["series"]], ["pre_pandemic", "post_pandemic"])
        self.assertTrue(all(len(s["values"]) == 12 for s in seasonality["series"]))
        weights = actual["cpiPceWeights"]
        self.assertEqual(len(weights["categories"]), 5)
        self.assertEqual(len(weights["cpi"]), 5)
        self.assertEqual(len(weights["pce"]), 5)
        self.assertGreaterEqual(len(actual["specialComponents"]), 5)

    def test_survey_and_implied_have_expected_series_counts(self):
        self.assertEqual(len(self.dataset["survey"]["expectations"]["series"]), 5)
        self.assertEqual(len(self.dataset["implied"]["breakeven"]["series"]), 4)
        self.assertEqual(len(self.dataset["implied"]["latestCurve"]), 4)

    def test_ppt_expectations_and_leading_toolbox_are_refreshable(self):
        divergence = self.dataset["survey"]["divergence"]["series"]
        self.assertEqual([s["id"] for s in divergence], ["mich_1y", "nyfed_sce_1y", "mich_5y"])
        fiveyfivey = self.dataset["implied"]["fiveYearFiveYear"]["series"]
        self.assertEqual([s["id"] for s in fiveyfivey], ["five_year_five_year"])
        leading = self.dataset["leading"]
        self.assertEqual([s["id"] for s in leading["energyNowcast"]["series"]], ["gasoline_yoy", "cpi_energy_yoy"])
        gasoline = leading["energyNowcast"]["series"][0]
        self.assertEqual(gasoline["latestObservation"], gasoline["source"]["latestObservation"])
        self.assertLess(gasoline["latestObservation"], gasoline["dates"][-1])
        self.assertEqual([s["id"] for s in leading["usedCarLead"]["series"]], ["manheim_yoy_shifted", "used_cars_cpi_yoy"])
        manheim = leading["usedCarLead"]["series"][0]
        self.assertEqual(manheim["displayDateShiftMonths"], 2)
        self.assertEqual(manheim["latestObservation"], manheim["source"]["latestObservation"])
        self.assertEqual([s["id"] for s in leading["goodsPipeline"]["series"]], ["gscpi", "cpi_goods_yoy"])
        self.assertGreaterEqual(len(leading["toolkit"]), 6)
        self.assertIn("unavailable", {item["status"] for item in leading["toolkit"]})
        for chart_name in ("energyNowcast", "usedCarLead", "goodsPipeline"):
            for item in leading[chart_name]["series"]:
                self.assertEqual(len(item["dates"]), len(item["values"]))
                self.assertGreater(len(item["dates"]), 0)

    def test_all_rendered_series_have_aligned_finite_values_and_codes(self):
        charts = [
            self.dataset["actual"]["cpiTrend"],
            self.dataset["actual"]["pceTrend"],
            self.dataset["survey"]["expectations"],
            self.dataset["implied"]["breakeven"],
        ]
        for chart in charts:
            for series in chart["series"]:
                self.assertGreater(len(series["dates"]), 0)
                self.assertEqual(len(series["dates"]), len(series["values"]))
                self.assertTrue(all(math.isfinite(value) for value in series["values"]))
                self.assertEqual(series["latestObservation"], series["dates"][-1])
                self.assertEqual(series["latestValue"], series["values"][-1])
                self.assertTrue(series["source"]["code"].startswith("G"))

    def test_missing_periods_are_reported_not_silently_connected(self):
        missing = self.dataset["dataQuality"]["cpiMissingPeriods"]
        self.assertIsInstance(missing, list)


if __name__ == "__main__":
    unittest.main()
