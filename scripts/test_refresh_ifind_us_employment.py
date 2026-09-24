import json
import math
import unittest
from pathlib import Path

from scripts.refresh_ifind_us_employment import (
    align_by_period,
    compact_date,
    detect_missing_months,
    effective_end_date,
    fetch_response_series,
    rebase_series,
    rolling_mean,
    sahm_rule,
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

    def test_align_by_period_uses_common_months_not_array_positions(self):
        periods, aligned = align_by_period({
            "left": (["20260131", "20260228", "20260331"], [1.0, 2.0, 3.0]),
            "right": (["20260228", "20260331", "20260430"], [20.0, 30.0, 40.0]),
        })
        self.assertEqual(periods, ["202602", "202603"])
        self.assertEqual(aligned["left"], [2.0, 3.0])
        self.assertEqual(aligned["right"], [20.0, 30.0])

    def test_rebase_series_uses_named_base_period(self):
        dates, values = rebase_series(
            ["20211231", "20220131", "20220228"],
            [200.0, 220.0, 180.0],
            "202112",
        )
        self.assertEqual(dates, ["20211231", "20220131", "20220228"])
        self.assertEqual(values, [100.0, 110.0, 90.0])

    def test_annual_forecast_fetch_includes_current_year_end(self):
        self.assertEqual(effective_end_date("年", "2026-09-24"), "2026-12-31")
        self.assertEqual(effective_end_date("月", "2026-09-24"), "2026-09-24")

    def test_sahm_rule_is_three_month_average_minus_trailing_twelve_month_low(self):
        dates = [f"2025{month:02d}01" for month in range(1, 13)] + ["20260101", "20260201", "20260301"]
        values = [4.0] * 12 + [4.3, 4.6, 4.9]
        result_dates, result_values = sahm_rule(dates, values)
        self.assertEqual(result_dates[-1], "20260301")
        self.assertAlmostEqual(result_values[-1], 0.6)


class IfindEmploymentDatasetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    def charts(self):
        return [
            chart
            for section in self.dataset["sections"].values()
            for chart in section.get("charts", [])
        ]

    def test_dataset_is_ifind_first_and_uses_ppt_contract(self):
        self.assertEqual(self.dataset["schemaVersion"], 2)
        self.assertEqual(self.dataset["source"], "iFinD EDB")
        self.assertEqual(self.dataset["sourceProviders"], ["iFinD EDB"])
        self.assertEqual(self.dataset["frameworkSource"]["file"], "研究框架/美国宏观数据培训【0829定稿】.pptx")
        self.assertEqual(self.dataset["frameworkSource"]["slides"], "26—59")
        serialized = json.dumps(self.dataset, ensure_ascii=False)
        self.assertNotIn("Wind EDB", serialized)
        self.assertNotIn("OpenBB", serialized)

    def test_route_map_matches_the_five_ppt_branches(self):
        branches = self.dataset["routeMap"]
        self.assertEqual([item["id"] for item in branches], [
            "official-surveys", "flows-weekly", "wage-measures", "empirical-frameworks", "cross-checks",
        ])
        self.assertEqual([len(item["nodes"]) for item in branches], [2, 2, 3, 4, 3])
        self.assertIn("CES 企业调查", branches[0]["nodes"][0]["title"])
        self.assertIn("Sahm 规则", branches[3]["nodes"][3]["title"])
        self.assertIn("WARN", branches[4]["nodes"][2]["title"])

    def test_headline_has_five_independently_dated_signals(self):
        self.assertEqual(
            [item["id"] for item in self.dataset["headline"]],
            ["payroll-momentum", "unemployment", "vu", "claims", "wage"],
        )
        for item in self.dataset["headline"]:
            self.assertEqual(item["source"], "iFinD EDB")
            self.assertTrue(item["observation"])
            self.assertTrue(math.isfinite(item["value"]))

    def test_sections_follow_the_ppt_route_instead_of_old_supply_demand_buckets(self):
        self.assertEqual(list(self.dataset["sections"]), [
            "officialSurveys", "flows", "wages", "frameworks", "crossChecks",
        ])
        expected_chart_ids = {
            "officialSurveys": {
                "payroll-momentum", "cyclical-industries", "temporary-help", "weekly-hours",
                "u-spectrum", "long-term-unemployment", "participation", "race-unemployment",
                "age-sex-unemployment", "survey-divergence",
            },
            "flows": {"claims", "vu-wage", "jolts-rates"},
            "wages": {"wage-three-measures"},
            "frameworks": {"okun", "unemployment-gap", "beveridge", "sahm"},
            "crossChecks": {"adp-trend", "adp-scatter"},
        }
        for section_id, ids in expected_chart_ids.items():
            actual = {chart["id"] for chart in self.dataset["sections"][section_id]["charts"]}
            self.assertTrue(ids.issubset(actual), (section_id, ids - actual))

    def test_every_chart_carries_ppt_grounded_explanation(self):
        for chart in self.charts():
            explanation = chart["explanation"]
            self.assertTrue(explanation["what"])
            self.assertTrue(explanation["howToRead"])
            self.assertTrue(explanation["caveat"])
            self.assertRegex(explanation["pptSlide"], r"^PPT p\.\d+")

    def test_data_passports_explain_producer_processing_and_use(self):
        passports = self.dataset["dataPassports"]
        self.assertEqual({item["id"] for item in passports}, {"ces", "cps", "claims", "jolts", "wages"})
        for item in passports:
            self.assertTrue(item["producer"])
            self.assertTrue(item["sample"])
            self.assertTrue(item["frequency"])
            self.assertTrue(item["revision"])
            self.assertTrue(item["use"])
            self.assertTrue(item["pitfall"])

    def test_sector_monitor_has_recent_heatmap_and_pre_pandemic_benchmark(self):
        table = self.dataset["sections"]["officialSurveys"]["sectorMonitor"]
        self.assertEqual(len(table["periods"]), 12)
        self.assertEqual(len(table["rows"]), 9)
        self.assertEqual(table["periods"], sorted(table["periods"], reverse=True))
        for row in table["rows"]:
            self.assertEqual(len(row["values"]), 12)
            self.assertTrue(math.isfinite(row["recent12mAverage"]))
            self.assertTrue(math.isfinite(row["baseline2018To2019"]))
            self.assertRegex(row["source"]["code"], r"^[A-Z]\d+$")

    def test_framework_charts_expose_required_derived_contracts(self):
        charts = {chart["id"]: chart for chart in self.dataset["sections"]["frameworks"]["charts"]}
        self.assertEqual(charts["sahm"]["reference"], 0.5)
        self.assertEqual(charts["beveridge"]["balanceLine"], "V/U=1")
        self.assertGreater(len(charts["okun"]["points"]), 40)
        self.assertTrue(all("period" in point for point in charts["okun"]["points"]))
        self.assertTrue(charts["unemployment-gap"]["series"])

    def test_core_comparison_series_use_current_precise_ifind_contracts(self):
        charts = {chart["id"]: chart for chart in self.charts()}
        survey_sources = {series["id"]: series["source"]["code"] for series in charts["survey-divergence"]["series"]}
        wage_sources = {series["id"]: series["source"]["code"] for series in charts["wage-three-measures"]["series"]}
        gap_sources = {series["id"]: series["source"]["code"] for series in charts["unemployment-gap"]["series"]}
        adp_sources = {series["id"]: series["source"]["code"] for series in charts["adp-trend"]["series"]}
        self.assertEqual(survey_sources["ces_employment"], "G002600500")
        self.assertEqual(wage_sources["eci_wage_yoy"], "G005349364")
        self.assertEqual(charts["okun"]["xSource"]["code"], "G005120901")
        self.assertEqual(gap_sources["u_star"], "G011775525")
        self.assertEqual(adp_sources["adp_3m"], "G015405071")
        self.assertIn("非周期性失业率代理", charts["unemployment-gap"]["series"][1]["label"])
        vu_units = {series["id"]: series["unit"] for series in charts["vu-wage"]["series"]}
        self.assertEqual(vu_units, {"vacancy_unemployment_ratio": "倍", "eci_wage_yoy": "%"})

    def test_all_rendered_series_are_aligned_finite_and_identified(self):
        for chart in self.charts():
            for series in chart.get("series", []):
                self.assertGreater(len(series["dates"]), 0)
                self.assertEqual(len(series["dates"]), len(series["values"]))
                self.assertTrue(all(math.isfinite(value) for value in series["values"]))
                self.assertEqual(series["latestObservation"], series["dates"][-1])
                self.assertEqual(series["latestValue"], series["values"][-1])
                self.assertRegex(series["source"]["code"], r"^[A-Z]\d+$")
                self.assertEqual(series["source"]["provider"], "iFinD EDB")

    def test_unavailable_third_party_series_are_explicit_not_fabricated(self):
        availability = self.dataset["sections"]["crossChecks"]["availability"]
        self.assertEqual({item["id"] for item in availability}, {"challenger", "indeed", "nfib", "warn"})
        for item in availability:
            self.assertIn(item["status"], ("available", "not-integrated"))
            self.assertTrue(item["explanation"])

    def test_monthly_gaps_are_disclosed(self):
        quality = self.dataset["dataQuality"]
        self.assertIsInstance(quality["monthlyMissingPeriods"], dict)
        self.assertIn("payroll_total", quality["monthlyMissingPeriods"])


if __name__ == "__main__":
    unittest.main()
