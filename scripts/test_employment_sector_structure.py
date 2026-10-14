"""Offline unit fixtures are synthetic by design, never written to dashboard data."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import refresh_ifind_us_employment as refresh
from scripts.employment_sector_structure import (
    SECTORS, BASELINE_PERIODS, ReconciliationError,
    build_sector_monitor, fetch_sector_levels, parse_sector_levels, shift_month,
)


def fixture():
    """Synthetic balanced hierarchy, with true 0.1-thousand utility changes."""
    periods = [shift_month("201712", i) for i in range(106)]
    parents = {s[3] for s in SECTORS}
    values = {}
    for key, _, code, parent, _ in reversed(SECTORS):
        if key not in parents:
            step = 0.1 if key == "sector_utilities" else 9.9 if key == "sector_retail" else 10
            values[key] = [round(1000 + i * step, 1) for i in range(len(periods))]
        else:
            children = [s[0] for s in SECTORS if s[3] == key]
            values[key] = [round(sum(values[c][i] for c in children), 1) for i in range(len(periods))]
    payload = {"status": "REQUEST_SUCCEEDED", "Results": {"series": [
        {"seriesID": code, "data": [{"year": p[:4], "period": "M" + p[4:], "value": str(v)} for p, v in zip(periods, values[key])]}
        for key, _, code, _, _ in SECTORS
    ]}}
    dates = [p + "01" for p in periods[1:]]
    payroll = [round(b - a, 1) for a, b in zip(values["payroll_total"], values["payroll_total"][1:])]
    return payload, dates, payroll


class SectorStructureTests(unittest.TestCase):
    def setUp(self):
        self.payload, self.dates, self.payroll = fixture()

    def build(self):
        return build_sector_monitor(self.payload, self.dates, self.payroll, "data/raw/test.json")

    def test_complete_hierarchy_preserves_tenths_and_full_means(self):
        table = self.build()
        rows = {r["id"]: r for r in table["rows"]}
        self.assertEqual(len(rows), 21)
        self.assertEqual(sum(r["rowType"] == "detail" for r in rows.values()), 16)
        self.assertEqual(rows["sector_utilities"]["values"], [0.1] * 12)
        self.assertEqual(rows["sector_utilities"]["recent12mAverage"], 0.1)
        self.assertEqual(rows["sector_utilities"]["baseline2018To2019"], 0.1)
        self.assertEqual(rows["sector_education_health"]["parentId"], "payroll_services")
        self.assertEqual(rows["sector_local"]["depth"], 2)
        self.assertEqual(rows["sector_utilities"]["depth"], 3)
        for group in ("checks", "baselineChecks"):
            self.assertTrue(all(not any(c["values"]) for c in table["reconciliation"][group]))
        self.assertEqual(table["reconciliation"]["baselinePeriods"], BASELINE_PERIODS)

    def test_missing_recent_month_is_not_skipped_or_imputed(self):
        self.payload["Results"]["series"][7]["data"].pop(-4)
        with self.assertRaisesRegex(ValueError, "Missing contiguous monthly levels"):
            self.build()

    def test_missing_baseline_predecessor_prevents_partial_average(self):
        self.payload["Results"]["series"][0]["data"].pop(0)
        with self.assertRaisesRegex(ValueError, "201801"):
            self.build()

    def test_missing_baseline_month_prevents_partial_average(self):
        self.payload["Results"]["series"][0]["data"].pop(4)
        with self.assertRaisesRegex(ValueError, "Missing contiguous monthly levels"):
            self.build()

    def test_missing_chart_month_is_not_intersected_away(self):
        self.dates.pop(-4)
        self.payroll.pop(-4)
        with self.assertRaisesRegex(ValueError, "Missing monthly payroll comparison"):
            self.build()

    def test_vintage_difference_is_preserved_in_failure_not_forced_to_zero(self):
        self.payroll[-1] += 1
        with self.assertRaises(ReconciliationError) as raised:
            self.build()
        check = raised.exception.reconciliation["checks"][-1]
        self.assertEqual(check["values"][0], -1)
        self.assertEqual(check["tolerance"], 0)

    def test_unbalanced_industry_fails_even_when_headline_matches(self):
        self.payload["Results"]["series"][7]["data"][-1]["value"] = "50000"
        with self.assertRaises(ReconciliationError):
            self.build()

    def test_unbalanced_baseline_fails_even_when_recent_matches(self):
        self.payload["Results"]["series"][7]["data"][5]["value"] = "50000"
        with self.assertRaises(ReconciliationError):
            self.build()

    def test_rounded_level_differencing_has_two_endpoint_error_bound(self):
        self.payload["Results"]["series"][7]["data"][-1]["value"] = str(float(self.payload["Results"]["series"][7]["data"][-1]["value"]) + 0.9)
        table = self.build()
        check = table["reconciliation"]["checks"][0]
        self.assertEqual(check["values"][0], 0.9)
        self.assertEqual(check["tolerance"], 10.4)

    def test_wrong_seasonal_adjustment_or_employee_type_fails(self):
        for code in ("CEU0000000001", "CES0000000003"):
            broken = copy.deepcopy(self.payload)
            broken["Results"]["series"][0]["seriesID"] = code
            with self.assertRaisesRegex(ValueError, "identity"):
                parse_sector_levels(broken)

    def test_missing_series_and_duplicate_observations_fail(self):
        broken = copy.deepcopy(self.payload)
        broken["Results"]["series"].pop()
        with self.assertRaisesRegex(ValueError, "Missing BLS employment series"):
            parse_sector_levels(broken)
        first = self.payload["Results"]["series"][0]["data"]
        first.append(dict(first[0]))
        with self.assertRaisesRegex(ValueError, "Duplicate BLS employment month"):
            self.build()

    def test_unexpected_precision_is_not_silently_rounded_for_display(self):
        latest = self.payload["Results"]["series"][7]["data"][-1]
        latest["value"] = str(float(latest["value"]) + 0.01)
        with self.assertRaisesRegex(ValueError, "precision"):
            self.build()

    def test_nonfinite_and_nonpositive_levels_fail(self):
        for bad in ("NaN", "Infinity", "0", "-1"):
            self.payload["Results"]["series"][0]["data"][0]["value"] = bad
            with self.assertRaisesRegex(ValueError, "range check"):
                self.build()

    def test_fetch_after_2026_keeps_baseline_and_uses_complete_industry_batches(self):
        requests = []
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return b'{"status":"REQUEST_SUCCEEDED","Results":{"series":[]}}'
        def get(request, timeout):
            requests.append(json.loads(request.data))
            return Response()
        with patch("scripts.employment_sector_structure.urllib.request.urlopen", get):
            bundle = fetch_sector_levels(2030)
        self.assertEqual([(r["startyear"], r["endyear"]) for r in requests], [("2017", "2019"), ("2028", "2030")])
        self.assertTrue(all(len(r["seriesid"]) == 21 for r in requests))
        self.assertEqual(len(bundle["responses"]), 2)

    def test_atomic_publish_keeps_previous_valid_json_on_write_failure(self):
        publish = getattr(refresh, "publish_dataset", None)
        self.assertIsNotNone(publish, "Publish must atomically replace only a valid complete JSON")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "dataset.json"
            output.write_text('{"previous":true}', encoding="utf-8")
            with patch.object(Path, "replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaises(OSError):
                    publish({"next": 1}, output)
            self.assertEqual(output.read_text(encoding="utf-8"), '{"previous":true}')
            self.assertEqual(list(Path(directory).iterdir()), [output])
            with self.assertRaises(ValueError):
                publish({"invalid": float("nan")}, output)
            self.assertEqual(output.read_text(encoding="utf-8"), '{"previous":true}')
            publish({"valid": 2}, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"valid": 2})

    def test_replay_input_is_archived_inside_repository_not_external_path(self):
        helper = getattr(refresh, "load_archived_input", None)
        self.assertIsNotNone(helper, "Replay inputs must be archived and referenced repo-relatively")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "external" / "original.json"
            source.parent.mkdir()
            original = b'{"raw": 1}\n'
            source.write_bytes(original)
            repo = root / "repo"
            raw_dir = repo / "data" / "raw" / "employment"
            with patch.object(refresh, "REPO_ROOT", repo):
                payload, snapshot = helper(source, raw_dir)
            self.assertEqual(payload, {"raw": 1})
            self.assertTrue(snapshot.startswith("data/raw/"))
            self.assertEqual((repo / snapshot).read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
