import copy
import hashlib
import json
import unittest
from pathlib import Path
from verify_macro_refresh_publish import ROOT, DATA_FILES, verify, make_receipt


class MacroRefreshPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # In-memory fixture only. Actual publication requires its own persisted QA receipt.
        cls.receipt = make_receipt(ROOT, authorized=True, qa_complete=True)

    def test_all_old_research_guards_remain_effective(self):
        result = verify(self.receipt)
        self.assertTrue(result['legacyGateReplayed'])
        self.assertEqual(result['macroFiles'], 5)
        self.assertFalse(result['previousGate']['fullStageReady'])

    def test_authorization_exact_data_and_scope_are_required(self):
        for key, val in [('publicationAuthorized', False), ('pageQAComplete', False), ('scope', 'all-research'), ('snapshotSHA256', '0'*64)]:
            r = copy.deepcopy(self.receipt)
            r[key] = val
            with self.assertRaises(ValueError):
                verify(r)
        for name in DATA_FILES:
            r = copy.deepcopy(self.receipt)
            r['dataPins'][name] = '0'*64
            with self.assertRaises(ValueError):
                verify(r)
        r = copy.deepcopy(self.receipt)
        r['dataPins']['src/data/historyReplay.json'] = '0'*64
        with self.assertRaises(ValueError):
            verify(r)

    def test_infrastructure_permission_cannot_authorize_research_changes(self):
        r = copy.deepcopy(self.receipt)
        name = 'src/data/historyReplayRateLiftoffQtGuidance.json'
        r['infrastructurePins'][name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            verify(r)


if __name__ == '__main__':
    unittest.main()
