"""Long-table contracts; synthetic fixtures never enter production JSON."""
import json
import unittest
from pathlib import Path

from scripts import refresh_ifind_us_inflation as inflation
from scripts import refresh_ifind_us_employment as employment

ROOT = Path(__file__).resolve().parents[1]


def rebuild_snapshots():
    """Replay only archived originals: no network or credentials."""
    originals = {name: json.loads((ROOT / f"src/data/{name}.json").read_text(encoding="utf-8")) for name in ("usInflationData", "usEmploymentData")}
    for doc in originals.values():
        for ref in doc["rawSnapshots"].values():
            if not (ROOT / ref).is_file():
                raise FileNotFoundError(f"Required read-only raw archive missing: {ref}")
    a, b = originals.values()
    ia = a["rawSnapshots"]["ifind"]
    er = b["rawSnapshots"]
    load = lambda path: json.loads((ROOT / path).read_text(encoding="utf-8"))
    return originals, {
        "usInflationData": inflation.build_dataset(load(ia), a["generatedAt"], ia),
        "usEmploymentData": employment.build_dataset(load(er["ifind"]), b["generatedAt"], er["ifind"], load(er["blsSectorWages"]), er["blsSectorWages"], load(er["blsSectorEmployment"]), er["blsSectorEmployment"]),
    }



class InflationHistoryTests(unittest.TestCase):
    def test_history_uses_all_actual_months_and_preserves_calendar_gaps(self):
        parsed = {}
        for _, _, yoy, mom, weight, _ in inflation.HEATMAP_ROWS:
            parsed[yoy] = (["20250930", "20251130"], [1.2, 2.3])
            parsed[mom] = (["20250930", "20251130"], [0.1, 0.2])
            if weight:
                parsed[weight] = (["20250731"], [5.25])
        parsed["cpi_mom"] = (["20250831", "20250930", "20251130"], [0.3, 0.1, 0.2])
        table = inflation.build_heatmap(parsed)
        self.assertIn("history", table)
        history = table["history"]
        self.assertEqual(history["periods"], ["202511", "202510", "202509", "202508"])
        self.assertEqual(history["rows"][0]["yoy"], [2.3, None, 1.2, None])
        self.assertEqual(history["rows"][0]["mom"], [0.2, None, 0.1, 0.3])
        self.assertEqual(table["periods"], ["202511", "202509"])
        self.assertEqual(table["rows"][0]["yoy"], [2.3, 1.2])
        self.assertEqual(history["rows"][1]["weight"], 5.25)
        self.assertEqual(history["rows"][1]["weightDate"], "20250731")
        self.assertIsNone(history["rows"][0]["weightDate"])
        self.assertIn("最新权重快照", history["note"])
        self.assertIn("非逐月历史权重", history["note"])


class EmploymentHistoryTests(unittest.TestCase):
    def test_full_history_preserves_missing_months_and_actual_residuals(self):
        from scripts.test_employment_sector_structure import fixture
        from scripts.employment_sector_structure import build_sector_monitor, shift_month
        payload, dates, payroll = fixture()
        # Historical problems outside strict recent/baseline windows must be
        # visible, not intersected away or overwritten with the chart total.
        index = dates.index("20210101")
        payroll[index] += 7
        gap = dates.index("20210301")
        dates.pop(gap)
        payroll.pop(gap)
        observations = payload["Results"]["series"][7]["data"]
        observations[:] = [p for p in observations if (p["year"], p["period"]) != ("2021", "M05")]
        table = build_sector_monitor(payload, dates, payroll, "data/raw/test.json")
        self.assertIn("history", table)
        history = table["history"]
        self.assertEqual(history["periods"][-1], "201801")
        self.assertEqual(history["periods"][0], "202609")
        self.assertTrue(all(shift_month(a, -1) == b for a, b in zip(history["periods"], history["periods"][1:])))
        rows = {r["id"]: r for r in history["rows"]}
        checks = {c["id"]: c for c in history["reconciliation"]["checks"]}
        at = history["periods"].index
        self.assertEqual(checks["table-vs-payroll"]["values"][at("202101")], -7)
        self.assertIsNone(checks["table-vs-payroll"]["values"][at("202103")])
        for period in ("202105", "202106"):
            self.assertIsNone(rows["sector_wholesale"]["values"][at(period)])
            self.assertIsNone(checks["services-subtotal"]["values"][at(period)])
            self.assertIsNotNone(checks["nonfarm-total"]["values"][at(period)])
        self.assertEqual(len(history["reconciliation"]["checks"]), 7)
        for old, new in zip(table["rows"], history["rows"]):
            self.assertEqual(new["values"][:12], old["values"])
            self.assertEqual(new["baseline2018To2019"], old["baseline2018To2019"])
        self.assertIn("修订", history["reconciliation"]["note"])
        self.assertIn("null", history["reconciliation"]["note"])


class WageHistoryTests(unittest.TestCase):
    def test_mom_never_bridges_a_missing_calendar_month(self):
        from scripts.refresh_ifind_us_employment import month_over_month
        dates, values = month_over_month(
            ["20241231", "20250131", "20250331", "20250430"],
            [20, 22, 33, 36.3],
        )
        self.assertEqual(dates, ["20250131", "20250430"])
        self.assertEqual([round(v, 4) for v in values], [10, 10])


class PublishedHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inflation = json.loads((ROOT / "src/data/usInflationData.json").read_text(encoding="utf-8"))
        cls.employment = json.loads((ROOT / "src/data/usEmploymentData.json").read_text(encoding="utf-8"))

    def tables(self):
        return [self.inflation["actual"]["cpiHeatmap"], self.employment["sections"]["officialSurveys"]["sectorMonitor"], self.employment["sections"]["wages"]["wageSectorMonitor"]]

    def test_all_published_histories_have_continuous_descending_axes_and_legacy_parity(self):
        for table in self.tables():
            self.assertIn("history", table)
            history = table["history"]
            periods = history["periods"]
            self.assertGreater(len(periods), 12)
            self.assertEqual(len(periods), len(set(periods)))
            self.assertTrue(all(employment.shift_month(a, -1) == b for a, b in zip(periods, periods[1:])))
            for old, row in zip(table["rows"], history["rows"]):
                self.assertEqual(old["id"], row["id"])
                for field in ("values", "yoy", "mom"):
                    if field not in row:
                        continue
                    self.assertEqual(len(row[field]), len(periods))
                    self.assertEqual([row[field][periods.index(p)] for p in table["periods"]], old[field])
            self.assertEqual(len(history["rows"]), len(table["rows"]))
            self.assertTrue(history["note"])

    def test_cpi_october_2025_is_a_null_calendar_column_not_a_removed_month(self):
        table = self.inflation["actual"]["cpiHeatmap"]
        self.assertIn("history", table)
        history = table["history"]
        index = history["periods"].index("202510")
        self.assertIsNone(history["rows"][0]["yoy"][index])
        self.assertEqual(history["periods"][-1], "191302")
        self.assertIn("非逐月历史权重", history["note"])

    def test_employment_reconciles_all_history_months_not_only_intersection(self):
        table = self.employment["sections"]["officialSurveys"]["sectorMonitor"]
        self.assertIn("history", table)
        history = table["history"]
        rows = {r["id"]: r for r in history["rows"]}
        self.assertEqual(history["periods"][-1], "201702")
        monthly = next(c for c in self.employment["sections"]["officialSurveys"]["charts"] if c["id"] == "payroll-momentum")["series"][0]
        payroll = dict(zip((d[:6] for d in monthly["dates"]), monthly["values"]))
        relations = {
            "private-leaves": ([r["id"] for r in rows.values() if r["parentId"] in ("payroll_goods", "payroll_services")], "payroll_private"),
            "government-leaves": (["sector_federal", "sector_state", "sector_local"], "payroll_government"),
            "nonfarm-total": (["payroll_private", "payroll_government"], "payroll_total"),
            "goods-subtotal": ([r["id"] for r in rows.values() if r["parentId"] == "payroll_goods"], "payroll_goods"),
            "services-subtotal": ([r["id"] for r in rows.values() if r["parentId"] == "payroll_services"], "payroll_services"),
            "private-subtotals": (["payroll_goods", "payroll_services"], "payroll_private"),
        }
        checks = history["reconciliation"]["checks"]
        self.assertEqual({c["id"] for c in checks}, {*relations, "table-vs-payroll"})
        for check in checks:
            self.assertEqual(len(check["values"]), len(history["periods"]))
            for i, period in enumerate(history["periods"]):
                if check["id"] == "table-vs-payroll":
                    values = [rows["payroll_total"]["values"][i], payroll.get(period)]
                    expected = round(values[0] - values[1], 4) if all(v is not None for v in values) else None
                else:
                    children, parent = relations[check["id"]]
                    values = [rows[k]["values"][i] for k in [*children, parent]]
                    expected = round(sum(values[:-1]) - values[-1], 1) if all(v is not None for v in values) else None
                self.assertEqual(check["values"][i], expected)


class ArchivedReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.originals, cls.rebuilt = rebuild_snapshots()

    def test_wage_history_contains_all_actual_mom_observations(self):
        table = self.rebuilt["usEmploymentData"]["sections"]["wages"]["wageSectorMonitor"]
        self.assertIn("history", table)
        history = table["history"]
        self.assertEqual(history["periods"][-1], "201702")
        self.assertEqual(len(history["rows"]), 9)
        ref = self.originals["usEmploymentData"]["rawSnapshots"]["blsSectorWages"]
        raw = json.loads((ROOT / ref).read_text(encoding="utf-8"))
        parsed = employment.parse_bls_series(raw, {s[0] for s in employment.BLS_SECTOR_WAGE_SPEC.values()})
        for row in history["rows"]:
            dates, values = parsed[row["source"]["code"]]
            levels = {d[:6]: v for d, v in zip(dates, values)}
            for period, value in zip(history["periods"], row["values"]):
                previous = employment.shift_month(period, -1)
                expected = round((levels[period] / levels[previous] - 1) * 100, 3) if period in levels and previous in levels else None
                self.assertEqual(value, expected)

    def test_all_cpi_history_cells_and_weight_dates_equal_original_payload(self):
        ref = self.originals["usInflationData"]["rawSnapshots"]["ifind"]
        raw = json.loads((ROOT / ref).read_text(encoding="utf-8"))
        parsed = {key: inflation.fetch_response_series(raw[key], spec[0]) for key, spec in inflation.SERIES_SPEC.items()}
        history = self.rebuilt["usInflationData"]["actual"]["cpiHeatmap"]["history"]
        for row, (_, _, yoy, mom, weight, _) in zip(history["rows"], inflation.HEATMAP_ROWS):
            for field, key in (("yoy", yoy), ("mom", mom)):
                values = {d[:6]: v for d, v in zip(*parsed[key])}
                self.assertEqual(row[field], [round(values[p], 2) if p in values else None for p in history["periods"]])
            self.assertEqual(row["weightDate"], parsed[weight][0][-1] if weight else None)
            self.assertEqual(row["weight"], round(parsed[weight][1][-1], 2) if weight else 100)

    def test_all_employment_cells_equal_consecutive_raw_level_differences(self):
        from decimal import Decimal
        doc = self.originals["usEmploymentData"]
        ref = doc["rawSnapshots"]["blsSectorEmployment"]
        raw = json.loads((ROOT / ref).read_text(encoding="utf-8"))
        levels = {}
        for batch in raw["responses"]:
            for series in batch["response"]["Results"]["series"]:
                levels.setdefault(series["seriesID"], {}).update({p["year"] + p["period"][1:]: Decimal(p["value"]) for p in series["data"] if p["period"] != "M13"})
        history = self.rebuilt["usEmploymentData"]["sections"]["officialSurveys"]["sectorMonitor"]["history"]
        for row in history["rows"]:
            values = levels[row["source"]["code"]]
            for period, value in zip(history["periods"], row["values"]):
                previous = employment.shift_month(period, -1)
                expected = float(values[period] - values[previous]) if period in values and previous in values else None
                self.assertEqual(value, expected)

    def test_wage_history_keeps_one_industry_gap_and_following_mom_null(self):
        doc = self.originals["usEmploymentData"]
        refs = doc["rawSnapshots"]
        load = lambda key: json.loads((ROOT / refs[key]).read_text(encoding="utf-8"))
        wages = load("blsSectorWages")
        wages["Results"]["series"][0]["data"] = [p for p in wages["Results"]["series"][0]["data"] if (p["year"], p["period"]) != ("2021", "M05")]
        rebuilt = employment.build_dataset(load("ifind"), doc["generatedAt"], refs["ifind"], wages, refs["blsSectorWages"], load("blsSectorEmployment"), refs["blsSectorEmployment"])
        history = rebuilt["sections"]["wages"]["wageSectorMonitor"]["history"]
        for period in ("202105", "202106"):
            i = history["periods"].index(period)
            self.assertIsNone(history["rows"][0]["values"][i])
            self.assertTrue(all(row["values"][i] is not None for row in history["rows"][1:]))
        self.assertEqual(history["rows"][0]["values"][:12], self.rebuilt["usEmploymentData"]["sections"]["wages"]["wageSectorMonitor"]["history"]["rows"][0]["values"][:12])

    def test_same_snapshot_replay_preserves_every_existing_field(self):
        def strip_history(value):
            if isinstance(value, dict):
                return {k: strip_history(v) for k, v in value.items() if k != "history"}
            if isinstance(value, list):
                return [strip_history(v) for v in value]
            return value
        for name, rebuilt in self.rebuilt.items():
            self.assertEqual(strip_history(rebuilt), strip_history(self.originals[name]))


if __name__ == "__main__":
    unittest.main()
