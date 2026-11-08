"""Approved openings must pass a new gate without rewriting frozen research."""
import importlib.util
from pathlib import Path
import unittest

class EditorialPublicationTests(unittest.TestCase):
    def test_scoped_gate_exists_and_restores_exact_predecessor(self):
        path = Path(__file__).with_name('verify_editorial_openings_publish.py')
        self.assertTrue(path.is_file(), 'Missing authorized editorial publication wrapper')
        spec = importlib.util.spec_from_file_location('verify_editorial_openings_publish', path)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        result = gate.verify(gate.make_receipt())
        self.assertTrue(result['legacyGateReplayed'])
        self.assertEqual(result['editorialCells'], 50)
        self.assertFalse(result['fullStageReady'])

    def test_missing_authorization_expanded_scope_or_pin_sets_rejected(self):
        import copy
        import verify_editorial_openings_publish as g
        receipt = g.make_receipt()
        for key, value in [('publicationAuthorized', False), ('fullStageReady', True), ('scope', 'all-research'), ('authorizationSHA256', '0' * 64)]:
            changed = copy.deepcopy(receipt)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                g.verify(changed)
        for extra in (False, True):
            changed = copy.deepcopy(receipt)
            if extra:
                changed['publicFilePins']['data/raw/private.json'] = '0' * 64
            else:
                del changed['publicFilePins'][g.DATA['A']]
            with self.assertRaises(ValueError):
                g.verify(changed)

    def test_out_of_scope_semantics_rejected_before_hash_checks(self):
        import copy
        import json
        import verify_editorial_openings_publish as g
        base = g.snapshot_files()
        inverse = g.inverse_contract()
        for key, name in g.DATA.items():
            original = json.loads((g.ROOT / name).read_bytes())
            changes = inverse[name]['semanticChanges']
            baseline = json.loads(base[name])
            for field, value in [('startDate', '2000-01-01'), ('endDate', '2099-01-01'), ('title', 'unapproved')]:
                altered = copy.deepcopy(original)
                altered[field] = value
                with self.subTest(page=key, field=field), self.assertRaisesRegex(ValueError, 'out-of-scope'):
                    g.check_semantics(altered, baseline, changes, [])
            for mutation in ('eligibility', 'market', 'deep', 'quota', 'opening'):
                altered = copy.deepcopy(original)
                if mutation == 'eligibility': altered['localReview']['fullStageReady'] = True
                if mutation == 'market': altered['marketPaths']['series'][0]['observations'][0]['value'] = 99999
                if mutation == 'deep': altered['marketAnalysis']['sections'][0]['deepDive'] = {}
                if mutation == 'quota': altered['localReview']['coverage'] = []
                if mutation == 'opening': g.put(altered, changes[0]['pointer'], 'unapproved economic claim')
                with self.subTest(page=key, mutation=mutation), self.assertRaises(ValueError):
                    g.check_semantics(altered, baseline, changes, [])

    def test_rehash_does_not_authorize_unrelated_macro_change(self):
        from unittest.mock import patch
        import verify_editorial_openings_publish as g
        name = 'src/data/usInflationData.json'
        target = g.ROOT / name
        original_read = Path.read_bytes
        replacement = original_read(target) + b'\n'
        receipt = g.make_receipt()
        receipt['publicFilePins'][name] = g.sha(replacement)
        def read(path):
            return replacement if path == target else original_read(path)
        with patch.object(Path, 'read_bytes', read), self.assertRaisesRegex(ValueError, 'immutable'):
            g.verify(receipt)

    def test_exact_mixed_newline_inverse_and_safe_paths(self):
        import verify_editorial_openings_publish as g
        base = g.snapshot_files()
        for name in g.DATA.values():
            self.assertEqual(g.restore(name), base[name])
        for name in ('/absolute', '../escape', 'C:/private', 'a\\\\b', '.env', 'data/raw/private'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                g.safe(name)

    def test_changed_auth_snapshot_fixture_and_inverse_fail_closed(self):
        from unittest.mock import patch
        import verify_editorial_openings_publish as g
        receipt = g.make_receipt()
        original_read = Path.read_bytes
        for name in (g.AUTH, g.SNAPSHOT, g.MATRIX, g.INVERSE):
            target = g.ROOT / name
            def read(path):
                raw = original_read(path)
                return raw + b'\n' if path == target else raw
            with self.subTest(name=name), patch.object(Path, 'read_bytes', read), self.assertRaises(ValueError):
                g.verify(receipt)

if __name__ == '__main__':
    unittest.main()
