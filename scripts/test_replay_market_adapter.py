"""Test-only market-contract fixtures; never used as research values."""
import unittest
import build_history_replay as builder


class AdmittedMarketPresentationTests(unittest.TestCase):
    def adapt(self, original):
        self.assertTrue(hasattr(builder, '_admitted_market_presentation'), 'Missing admitted market UI contract adapter')
        return builder._admitted_market_presentation(original)

    def sample(self):
        return {'sources': [{'id': 'test-source', 'url': 'https://example.org/test-series'}],
                'series': [{'id': 'test-dollar', 'title': 'TEST ONLY',
                            'unit': 'index_January_2006_100',
                            'observations': [{'date': '2026-09-01', 'value': 1,
                                              'sourceId': 'test-source', 'releaseDate': None,
                                              'historicalAsOfEligible': False}]}],
                'missingSeries': [{'id': 'CME_FedWatch', 'reason': 'TEST ONLY missing'}]}

    def test_native_verified_series_becomes_complete_existing_ui_contract_without_losing_metadata(self):
        original = self.sample()
        result = self.adapt(original)
        row = result['series'][0]
        self.assertEqual(row['sourceUrl'], 'https://example.org/test-series')
        self.assertEqual(row['unit'], 'index_Jan2006_100')
        self.assertEqual(row['sourceUnit'], 'index_January_2006_100')
        self.assertTrue(row['status'])
        self.assertTrue(row['limitations'])
        self.assertEqual(row['observations'], original['series'][0]['observations'])
        self.assertNotIn('sourceUrl', original['series'][0])
        self.assertEqual(result['cmeHistoricalImpliedPath']['observations'], [])

    def test_a_declared_unknown_original_source_is_rejected_instead_of_inventing_url(self):
        original = self.sample()
        original['series'][0]['observations'][0]['sourceId'] = 'unadmitted-source'
        with self.assertRaisesRegex(ValueError, 'source identity'):
            self.adapt(original)


if __name__ == '__main__':
    unittest.main()
