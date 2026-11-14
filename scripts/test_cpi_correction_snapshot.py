"""The CPI correction inherits exact public baseline48, not rehashed research."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CorrectionSnapshotTests(unittest.TestCase):
    def test_exact_baseline48_thin_overlay(self):
        path = ROOT / 'scripts/cpi_correction_snapshot.py'
        self.assertTrue(path.is_file(), 'Missing baseline48 correction snapshot helper')
        import cpi_correction_snapshot as snapshot
        files = snapshot.snapshot_files()
        self.assertEqual(len(files), 258)
        receipt = json.loads(files['release/macro-refresh-publication-02.json'])
        for field in ('dataPins', 'infrastructurePins', 'implementationPins'):
            for name, expected in receipt[field].items():
                self.assertEqual(snapshot.sha(files[name]), expected, name)
        manifest = json.loads(snapshot.members((ROOT / snapshot.SNAPSHOT).read_bytes())['__manifest__.json'])
        self.assertEqual(set(files), set(manifest['filePins']))
        self.assertFalse(any(n.endswith('.zip') for n in manifest['overlayFiles']))
        self.assertIn('release/snapshots/macro-refresh-base-a2069bd.delta.zip', manifest['externalFiles'])
        self.assertLess((ROOT / snapshot.SNAPSHOT).stat().st_size, 2_000_000)

    def test_partition_preserves_every_case_and_assertion_without_private_imports(self):
        import cpi_correction_snapshot as snapshot
        self.assertTrue(hasattr(snapshot, 'split_history'), 'Missing 59-case historical partition')
        loader = unittest.TestLoader()
        suite = loader.discover(str(ROOT / 'scripts'), pattern='test_verify*publish*.py')
        self.assertFalse(loader.errors)
        expected = suite.countTestCases()
        current, historical = snapshot.split_history(suite)
        self.assertEqual(len(historical), 59)
        self.assertEqual(Counter(c.id() for c in historical), Counter(snapshot.history_ids()))
        self.assertEqual(current.countTestCases() + len(historical), expected)
        self.assertNotIn('test_refresh_ifind_us_inflation', snapshot.HISTORY_MODULES)
        from unittest.mock import patch
        original = Path.read_bytes
        name = ROOT / 'scripts/test_verify_macro_refresh_v2_publish.py'
        with patch.object(Path, 'read_bytes', lambda p: original(p) + b'\n# changed assertion source' if p == name else original(p)):
            with self.assertRaisesRegex(ValueError, 'assertions'):
                snapshot.split_history(loader.discover(str(ROOT / 'scripts'), pattern='test_verify*publish*.py'))

    def test_execution_report_rejects_missing_duplicate_skipped_and_failed_cases(self):
        import cpi_correction_snapshot as snapshot
        self.assertTrue(hasattr(snapshot, 'execution_report'), 'Missing exact historical execution ledger')
        ids = ['module.Case.test_one', 'module.Case.test_two']
        text = '\n'.join(f'{identity.rsplit(".", 1)[1]} ({identity}) ... ok' for identity in ids)
        report = snapshot.execution_report(text, ids)
        self.assertEqual(report['ids'], ids)
        self.assertEqual(report['run'], 2)
        for bad in (text.splitlines()[0], text + '\n' + text.splitlines()[0], text.replace('... ok', '... skipped'), text + '\n_FailedTest', text + '\nFAILED (expected failures=1)'):
            with self.subTest(text=bad), self.assertRaises(ValueError):
                snapshot.execution_report(bad, ids)

    def test_exact_snapshot_rejects_mutated_delta_and_external_archives(self):
        import cpi_correction_snapshot as snapshot
        from unittest.mock import patch
        original = Path.read_bytes
        for name in (snapshot.SNAPSHOT, 'release/snapshots/macro-refresh-base-a2069bd.delta.zip'):
            with self.subTest(name=name), patch.object(Path, 'read_bytes', lambda p: original(p) + b'x' if p == ROOT / name else original(p)):
                with self.assertRaises(ValueError):
                    snapshot.snapshot_files()


if __name__ == '__main__':
    unittest.main()
