"""The previous macro publication stays immutable and is executed, not skipped."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch
from pce_publication_snapshot import previous_root, previous_case_ids, split_previous_tests, safe, ROOT
from verify_macro_refresh_publish import verify, RECEIPT


class PcePublicationSnapshotTests(unittest.TestCase):
    def test_exact_previous_macro_gate(self):
        with previous_root() as root:
            result = verify(json.loads((root / RECEIPT).read_bytes()), root=root)
            self.assertTrue(result['legacyGateReplayed'])
            self.assertFalse(result['previousGate']['fullStageReady'])

    def test_original_case_bodies_are_unchanged(self):
        name = 'scripts/test_verify_macro_refresh_publish.py'
        with previous_root() as root:
            self.assertEqual((ROOT / name).read_bytes().replace(b'\r\n', b'\n'), (root / name).read_bytes())
        self.assertEqual(len(previous_case_ids()), 3)

    def test_partition_preserves_every_discovered_case(self):
        suite = unittest.TestLoader().discover(str(Path(__file__).parent), pattern='test_verify*publish*.py')
        remaining, previous = split_previous_tests(suite)
        self.assertEqual({case.id() for case in previous}, previous_case_ids())
        self.assertEqual(remaining.countTestCases() + len(previous), suite.countTestCases())

    def test_snapshot_binding_and_path_safety(self):
        with patch('pce_publication_snapshot.SNAPSHOT_SHA', '0' * 64):
            with self.assertRaises(ValueError):
                with previous_root():
                    self.fail('tampered binding admitted')
        for value in ['../escape', '/absolute', 'C:/private', 'a\\b', 'data/raw/private.json', '.env']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                safe(value)
        self.assertEqual(safe('src/data/usInflationData.json').as_posix(), 'src/data/usInflationData.json')


if __name__ == '__main__':
    unittest.main()
