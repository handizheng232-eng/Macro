import json
import tempfile
import unittest
from pathlib import Path

from scripts.refresh_us_macro import (
    extract_metrics,
    resample_month_end,
    seasonalize,
    transform_values,
)
from scripts.refresh_openbb_us_macro import (
    annualized_quarterly_growth,
    normalize_openbb_series,
    resample_records_month_end,
)
from scripts.run_openbb_refresh import discover_openbb_python


class WindPayloadTests(unittest.TestCase):
    def test_extract_metrics_validates_identity_and_parallel_arrays(self):
        payload = {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "metrics": [{
                        "meta": {"code": "SERIES_A", "name": "Test", "unit": "%", "freq": "月"},
                        "date": ["20240131", "20240229"],
                        "value": [1.0, 2.0],
                    }]
                }),
            }],
            "isError": False,
        }

        metrics = extract_metrics(json.dumps(payload), {"SERIES_A"})

        self.assertEqual(set(metrics), {"SERIES_A"})
        self.assertEqual(metrics["SERIES_A"]["value"], [1.0, 2.0])

    def test_extract_metrics_rejects_unrequested_series(self):
        payload = {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "metrics": [{
                        "meta": {"code": "WRONG"},
                        "date": ["20240131"],
                        "value": [1.0],
                    }]
                }),
            }],
            "isError": False,
        }

        with self.assertRaisesRegex(ValueError, "unexpected series"):
            extract_metrics(json.dumps(payload), {"SERIES_A"})


class TransformationTests(unittest.TestCase):
    def test_yoy_percent_uses_twelve_month_lag(self):
        values = [100.0] + [None] * 11 + [112.0]
        transformed = transform_values(values, "yoy_pct")
        self.assertIsNone(transformed[0])
        self.assertAlmostEqual(transformed[-1], 12.0)

    def test_first_difference_preserves_missing_first_observation(self):
        self.assertEqual(transform_values([100.0, 103.0, 101.0], "diff"), [None, 3.0, -2.0])

    def test_weekly_series_resamples_to_last_observation_of_month(self):
        dates, values = resample_month_end(
            ["20240103", "20240131", "20240207", "20240228"],
            [10.0, 11.0, 12.0, 13.0],
        )
        self.assertEqual(dates, ["20240131", "20240228"])
        self.assertEqual(values, [11.0, 13.0])

    def test_seasonalize_groups_months_by_calendar_year(self):
        seasonal = seasonalize(
            ["20240131", "20240229", "20250131"],
            [1.0, 2.0, 3.0],
            frequency="月",
            first_year=2024,
        )
        self.assertEqual([item["year"] for item in seasonal], [2024, 2025])
        self.assertEqual(seasonal[0]["values"][:2], [1.0, 2.0])
        self.assertEqual(seasonal[1]["values"][0], 3.0)
        self.assertEqual(len(seasonal[0]["values"]), 12)


class OpenBBTransformationTests(unittest.TestCase):
    def test_normalize_openbb_series_validates_provider_and_scales_decimal_percent(self):
        payload = {
            "provider": "oecd",
            "warnings": None,
            "results": [
                {"date": "2026-07-01", "country": "united_states", "value": 0.03364825},
                {"date": "2026-08-01", "country": "united_states", "value": 0.03396548},
            ],
        }

        dates, values = normalize_openbb_series(
            payload,
            provider="oecd",
            value_field="value",
            scale=100,
        )

        self.assertEqual(dates, ["20260701", "20260801"])
        self.assertAlmostEqual(values[-1], 3.396548)

    def test_normalize_openbb_series_rejects_wrong_provider(self):
        with self.assertRaisesRegex(ValueError, "provider mismatch"):
            normalize_openbb_series(
                {"provider": "fred", "results": [{"date": "2026-08-01", "value": 1.0}]},
                provider="oecd",
                value_field="value",
            )

    def test_annualized_quarterly_growth_uses_real_gdp_levels(self):
        values = [100.0, 101.0, 102.0]
        result = annualized_quarterly_growth(values)
        self.assertIsNone(result[0])
        self.assertAlmostEqual(result[1], (1.01 ** 4 - 1) * 100)

    def test_resample_records_month_end_keeps_last_daily_effr(self):
        dates, values = resample_records_month_end(
            ["2026-08-28", "2026-08-31", "2026-09-01"],
            [0.0363, 0.0363, 0.0364],
        )
        self.assertEqual(dates, ["20260831", "20260901"])
        self.assertEqual(values, [0.0363, 0.0364])

    def test_discovers_python_next_to_openbb_mcp_executable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scripts_dir = Path(temp_dir) / "archive-v0" / "env" / "Scripts"
            scripts_dir.mkdir(parents=True)
            (scripts_dir / "openbb-mcp.exe").write_bytes(b"")
            python = scripts_dir / "python.exe"
            python.write_bytes(b"")

            self.assertEqual(discover_openbb_python(Path(temp_dir)), python)


if __name__ == "__main__":
    unittest.main()
