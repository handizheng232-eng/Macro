"""Frozen editorial approval is reconstructed, never re-authorized by data refresh."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ThinSnapshotTests(unittest.TestCase):
    def test_exact_editorial_approval_is_restored_from_thin_archive(self):
        path = ROOT / 'scripts/macro_refresh_v2_snapshot.py'
        self.assertTrue(path.is_file(), 'Missing immutable editorial-to-refresh snapshot adapter')
        spec = importlib.util.spec_from_file_location('macro_refresh_v2_snapshot', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        files = module.snapshot_files()
        receipt = json.loads(files['release/editorial-openings-publication-01.json'])
        self.assertEqual(set(files), set(receipt['publicFilePins']) | {'release/editorial-openings-publication-01.json'})
        for name, expected in receipt['publicFilePins'].items():
            self.assertEqual(module.sha(files[name]), expected, name)
        self.assertLess((ROOT / module.SNAPSHOT).stat().st_size, 1_000_000)

    def test_historical_discovery_is_partitioned_without_omission(self):
        import macro_refresh_v2_snapshot as module
        self.assertTrue(hasattr(module, 'split_history'), 'Missing complete historical partition')
        loader = unittest.TestLoader()
        # This public CI unit tests the gate partition without importing private
        # PDF-intake dependencies. run_data_tests still discovers ALL test_*.py
        # and checks its complete executed/discovered case-ID multiset.
        suite = loader.discover(str(ROOT / 'scripts'), pattern='test_verify*publish*.py')
        self.assertFalse(loader.errors)
        expected = suite.countTestCases()
        current, historical = module.split_history(suite)
        self.assertEqual(len(historical), 54)
        self.assertEqual({case.id() for case in historical}, module.history_ids())
        self.assertEqual(current.countTestCases() + len(historical), expected)
        self.assertGreater(current.countTestCases(), 0)

    def test_changed_snapshots_and_unsafe_members_fail_closed(self):
        import io
        import zipfile
        from unittest.mock import patch
        import macro_refresh_v2_snapshot as module
        original = Path.read_bytes
        for name in (module.SNAPSHOT, 'release/snapshots/editorial-baseline-2e4d735.zip'):
            with self.subTest(name=name), patch.object(Path, 'read_bytes',
                lambda p: original(p) + b'\n' if p == ROOT / name else original(p)), self.assertRaises(ValueError):
                module.snapshot_files()
        for name in ('/absolute', '../escape', 'C:/private', 'a\\b', '.env', 'data/raw/private', './alias'):
            stream = io.BytesIO()
            info = zipfile.ZipInfo('safe')
            info.filename = name  # Preserve the hostile raw name on Windows.
            with zipfile.ZipFile(stream, 'w') as archive: archive.writestr(info, b'not source data')
            with self.subTest(name=name), self.assertRaises(ValueError): module.members(stream.getvalue())


if __name__ == '__main__':
    unittest.main()
