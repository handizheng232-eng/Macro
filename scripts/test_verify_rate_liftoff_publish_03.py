import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from verify_rate_liftoff_publish_03 import ROOT, RECEIPT, AUTH, INVERSE, PREVIOUS, DATA, sha, verify, verify_assets

class LabelPublicationTests(unittest.TestCase):
    def setUp(self):
        self.r = json.loads((ROOT / RECEIPT).read_bytes())

    def test_complete_inherited_gate(self):
        r = verify(self.r, dist=ROOT / 'dist')
        self.assertTrue(r['legacyGateReplayed'])
        self.assertFalse(r['fullStageReady'])
        self.assertEqual(r['distFilesScanned'], 15)

    def test_absent_authorization_and_changed_scope(self):
        for k, v in [('publicationAuthorized', False), ('scope', 'all-history'), ('fullStageReady', True), ('authorizationSHA256', '0' * 64)]:
            r = copy.deepcopy(self.r)
            r[k] = v
            with self.assertRaises(ValueError):
                verify(r)

    def test_missing_extra_and_unsafe_pins(self):
        for extra in [True, False]:
            r = copy.deepcopy(self.r)
            if extra:
                r['publicFilePins']['../private'] = '0' * 64
            else:
                del r['publicFilePins'][DATA]
            with self.assertRaises(ValueError):
                verify(r)

    def test_rehashed_source_research_previous_receipt_and_contract_mutations(self):
        with tempfile.TemporaryDirectory(prefix='label-negative-') as folder:
            root = Path(folder)
            for n in set(self.r['publicFilePins']) | {RECEIPT}:
                p = root / n
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / n, p)
            for n in [DATA, 'src/historyReplay.tsx', 'src/App.tsx', PREVIOUS, AUTH, INVERSE, 'src/data/historyReplayTaper.json', 'public/replay-rate-liftoff/06-event-window.svg']:
                original = (root / n).read_bytes()
                raw = original + b'\n '
                (root / n).write_bytes(raw)
                r = copy.deepcopy(self.r)
                r['publicFilePins'][n] = sha(raw)
                with self.assertRaises(ValueError, msg=n):
                    verify(r, root)
                (root / n).write_bytes(original)

    def test_all_twelve_rehashed_svg_and_private_dist_mutations(self):
        with tempfile.TemporaryDirectory(prefix='label-assets-') as folder:
            dist = Path(folder)
            for n in self.r['distPins']:
                p = dist / n
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / 'dist' / n, p)
            charts = [n for n in self.r['distPins'] if n.endswith('.svg')]
            self.assertEqual(len(charts), 12)
            for n in charts:
                original = (dist / n).read_bytes()
                raw = original + b'<!-- changed -->'
                (dist / n).write_bytes(raw)
                r = copy.deepcopy(self.r)
                r['distPins'][n] = sha(raw)
                with self.assertRaises(ValueError):
                    verify_assets(dist, r, ROOT)
                (dist / n).write_bytes(original)
            n = next(n for n in self.r['distPins'] if n.endswith('.js'))
            raw = (dist / n).read_bytes() + b' E:/private/report.pdf'
            (dist / n).write_bytes(raw)
            r = copy.deepcopy(self.r)
            r['distPins'][n] = sha(raw)
            with self.assertRaisesRegex(ValueError, 'private'):
                verify_assets(dist, r, ROOT)

if __name__ == '__main__':
    unittest.main()
