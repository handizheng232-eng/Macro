import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from verify_pce_distribution_publish import ROOT, DATA, make_receipt, verify, check_semantics, sha
from pce_publication_snapshot import snapshot_files


class PceDistributionPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = make_receipt(authorized=True, qa_complete=True)
        cls.current = json.loads((ROOT / DATA).read_bytes())
        cls.previous = json.loads(snapshot_files()[DATA])

    def test_scoped_addition_preserves_all_preceding_gates(self):
        result = verify(self.receipt)
        self.assertTrue(result['legacyGateReplayed'])
        self.assertFalse(result['previousGate']['previousGate']['fullStageReady'])
        self.assertEqual(result['distributionMonths'], 13)
        self.assertEqual(result['latestComponentCount'], 177)

    def test_authorization_scope_and_pin_coverage_fail_closed(self):
        for key, value in [('publicationAuthorized', False), ('pageQAComplete', False),
                           ('scope', 'all-research'), ('snapshotSHA256', '0' * 64),
                           ('authorizationSHA256', '0' * 64), ('baselineReceiptSHA256', '0' * 64)]:
            changed = copy.deepcopy(self.receipt)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify(changed)
        for extra in (False, True):
            changed = copy.deepcopy(self.receipt)
            if extra:
                changed['publicFilePins']['data/raw/private.json'] = '0' * 64
            else:
                del changed['publicFilePins'][DATA]
            with self.assertRaises(ValueError):
                verify(changed)
        changed = copy.deepcopy(self.receipt)
        changed['changedPins']['src/data/usGdpData.json'] = changed['publicFilePins']['src/data/usGdpData.json']
        with self.assertRaises(ValueError):
            verify(changed)

    def test_official_semantics_are_checked_without_an_outer_hash_shortcut(self):
        def observation(d): d['actual']['pceDistribution']['buckets'][0]['values'][0] += 1
        def periods(d): d['actual']['pceDistribution']['periods'].reverse()
        def count(d): d['actual']['pceDistribution']['quality']['latestComponentCount'] += 1
        def method(d): d['actual']['pceDistribution']['methodology']['rate'] = '同比'
        def old_data(d): d['headline'][0]['value'] += 1
        def timestamp(d): d['actual']['pceDistribution']['source']['fetchedAt'] = '2027-01-01T00:00:00+00:00'
        def source(d): d['actual']['pceDistribution']['source']['resources']['chart']['sha256'] = '0' * 64
        for mutation in (observation, periods, count, method, old_data, timestamp, source):
            changed = copy.deepcopy(self.current)
            mutation(changed)
            with self.subTest(mutation=mutation.__name__), self.assertRaises(ValueError):
                check_semantics(changed, self.previous)

    def test_rehash_cannot_authorize_immutable_research_changes(self):
        name = 'src/data/historyReplay.json'
        target = ROOT / name
        original_read = Path.read_bytes
        replacement = original_read(target) + b'\n'
        changed = copy.deepcopy(self.receipt)
        changed['publicFilePins'][name] = sha(replacement)
        def read(path):
            return replacement if path == target else original_read(path)
        with patch.object(Path, 'read_bytes', read), self.assertRaisesRegex(ValueError, 'immutable'):
            verify(changed)

    def test_default_receipt_cannot_publish_before_explicit_qa(self):
        pending = make_receipt()
        self.assertFalse(pending['publicationAuthorized'])
        self.assertFalse(pending['pageQAComplete'])
        with self.assertRaises(ValueError):
            verify(pending)


if __name__ == '__main__':
    unittest.main()
