"""Comments-only release boundary; old receipts remain immutable."""
import importlib.util
import unittest
from pathlib import Path

class CommentsPublicationTests(unittest.TestCase):
    def test_comments_gate_exists_and_checks_exact_reviewed_tree(self):
        path = Path(__file__).with_name('verify_comments_publish.py')
        self.assertTrue(path.is_file(), 'A separate comments publication gate is required')
        spec = importlib.util.spec_from_file_location('comments_gate', path)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        self.assertEqual(gate.verify()['status'], 'PASS_COMMENTS_SCOPE_01')

    def test_rejects_unsafe_archive_paths(self):
        import verify_comments_publish as gate
        for name in ('/absolute', '../escape', 'C:/private', 'a\\\\b', '.env', 'node_modules/x'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                gate.safe(name)

    def test_inverse_restores_complete_baseline(self):
        import verify_comments_publish as gate
        manifest, _ = gate.contract()
        with gate.previous_root() as prior:
            actual = {p.relative_to(prior).as_posix(): gate.sha(p.read_bytes()) for p in prior.rglob('*') if p.is_file()}
        self.assertEqual(actual, manifest['baselinePins'])

    def test_negative_mutations(self):
        import json
        import shutil
        import tempfile
        import verify_comments_publish as gate
        manifest, _ = gate.contract()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            names = set(manifest['baselinePins']) | set(manifest['allowedChanges']) | {gate.RECEIPT, gate.INVERSE}
            for name in names:
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(gate.ROOT / name, dest)
            self.assertEqual(gate.verify(root)['status'], 'PASS_COMMENTS_SCOPE_01')
            receipt_path = root / gate.RECEIPT
            original = receipt_path.read_bytes()
            for key, value, reason in [('publicationAuthorized', False, 'authorization absent'), ('scope', 'all-articles', 'scope differs'), ('historicalResearchAuthorizationExpanded', True, 'scope differs'), ('sourcePins', {}, 'pin scope differs')]:
                receipt = json.loads(original)
                receipt[key] = value
                receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, reason):
                    gate.verify(root)
                receipt_path.write_bytes(original)
            for name, reason in [('src/data/usInflationData.json', 'immutable baseline differs'), ('release/cpi-correction-publication-01.json', 'immutable baseline differs'), ('src/replayComments.css', 'approved source differs')]:
                path = root / name
                raw = path.read_bytes()
                path.write_bytes(raw + b'\n')
                # Even rebinding the new receipt cannot authorize research or approved-UI drift.
                receipt = json.loads(original)
                if name in receipt['sourcePins']:
                    receipt['sourcePins'][name] = gate.sha(path.read_bytes())
                receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, reason):
                    gate.verify(root)
                path.write_bytes(raw)
                receipt_path.write_bytes(original)
            (root / 'src/unapproved.txt').write_text('unexpected')
            with self.assertRaisesRegex(ValueError, 'unapproved public file'):
                gate.verify(root)

if __name__ == '__main__':
    unittest.main()
