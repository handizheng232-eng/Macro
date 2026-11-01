"""Frozen research and mutable macro refreshes must be verified independently."""
import json
import unittest
from pathlib import Path
from macro_publication_snapshot import baseline_root, BASE_RECEIPT, legacy_case_ids, split_suite
from verify_rate_liftoff_publish_03 import verify


class MacroPublicationSnapshotTests(unittest.TestCase):
    def test_exact_frozen_research_gate(self):
        with baseline_root() as root:
            result = verify(json.loads((root / BASE_RECEIPT).read_bytes()), root=root)
            self.assertTrue(result['legacyGateReplayed'])
            self.assertFalse(result['fullStageReady'])

    def test_discovery_partition_keeps_every_case_once(self):
        root = Path(__file__).resolve().parent
        suite = unittest.TestLoader().discover(str(root), pattern='test_verify*publish*.py')
        local, historical = split_suite(suite)
        ids = [test.id() for test in historical]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any('test_verify_rate_liftoff_publish_03' in identity for identity in ids))
        self.assertEqual(set(ids), legacy_case_ids())
        self.assertEqual(local.countTestCases() + len(ids), suite.countTestCases())


if __name__ == '__main__':
    unittest.main()
