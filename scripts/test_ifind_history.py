import unittest

from scripts.ifind_history import assert_full_history, metadata_start_date


class IfindHistoryTest(unittest.TestCase):
    def test_metadata_start_date_uses_series_disclosure_start(self):
        self.assertEqual(metadata_start_date({"sdate": "19470331"}, "G002599633"), "1947-03-31")

    def test_metadata_start_date_rejects_missing_or_malformed_dates(self):
        with self.assertRaisesRegex(ValueError, "missing disclosure start"):
            metadata_start_date({}, "G000000001")
        with self.assertRaisesRegex(ValueError, "invalid disclosure start"):
            metadata_start_date({"sdate": "1947Q1"}, "G000000001")

    def test_assert_full_history_requires_first_observation_to_match_metadata(self):
        assert_full_history(["19470331", "19470630"], {"sdate": "19470331"}, "G002599633")
        with self.assertRaisesRegex(ValueError, "history is truncated"):
            assert_full_history(["19900331", "19900630"], {"sdate": "19470331"}, "G002599633")


if __name__ == "__main__":
    unittest.main()
