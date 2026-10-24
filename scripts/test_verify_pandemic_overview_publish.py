"""Fail-closed six-card authorization and unchanged prior publication chain."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from verify_pandemic_overview_publish import ROOT, RECEIPT, PREVIOUS, INVERSE, restore, previous_root, verify_pandemic, sha


class PandemicPublicationTests(unittest.TestCase):
    def setUp(self):
        self.receipt = json.loads((ROOT / RECEIPT).read_bytes())

    def test_authorized_chain(self):
        result = verify_pandemic(self.receipt)
        self.assertTrue(result['legacyGateReplayed'])
        self.assertEqual(result['heatmapTables'], 3)
        self.assertEqual(result['officialParagraphs'], 16)
        self.assertEqual(result['overviewPeriods'], 6)
        self.assertEqual(result['previousOverviewPeriods'], 8)
        self.assertFalse(result['fullStageReady'])
        with previous_root() as root:
            prior = json.loads((root / PREVIOUS).read_bytes())
            for name in ('src/App.tsx', '.github/workflows/deploy.yml'):
                self.assertEqual(sha((root / name).read_bytes()), prior['publicFilePins'][name])

    def test_authorization_and_scope(self):
        for name, value in [('publicationAuthorized', False), ('pageQAComplete', False),
                            ('fullResearchComplete', True), ('scope', 'all-research'),
                            ('legacyReceiptSHA256', '0'*64), ('approvedOverviewSHA256', '0'*64)]:
            changed = copy.deepcopy(self.receipt)
            changed[name] = value
            with self.assertRaises(ValueError, msg=name):
                verify_pandemic(changed)
        for mode in ('missing', 'extra', 'altered'):
            changed = copy.deepcopy(self.receipt)
            name = 'src/pandemicOverview.ts'
            if mode == 'missing':
                del changed['publicFilePins'][name]
            if mode == 'extra':
                changed['publicFilePins']['../escape'] = '0'*64
            if mode == 'altered':
                changed['publicFilePins'][name] = '0'*64
            with self.assertRaises(ValueError):
                verify_pandemic(changed)

    def test_rehashed_mutations_rejected(self):
        with tempfile.TemporaryDirectory(prefix='pandemic-negative-') as directory:
            root = Path(directory)
            with previous_root() as baseline:
                shutil.copytree(baseline, root, dirs_exist_ok=True)
            for name in set(self.receipt['publicFilePins']) | {RECEIPT}:
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, dest)
            for name in ('src/App.tsx', '.github/workflows/deploy.yml',
                         'src/pandemicOverview.ts', 'src/inflationOverview.ts',
                         'src/data/usEmploymentData.json', 'src/data/usInflationData.json',
                         'src/data/historyReplayRenewedEasingQtEnd.json', PREVIOUS):
                original = (root / name).read_bytes()
                (root / name).write_bytes(original + b'\n ')
                changed = copy.deepcopy(self.receipt)
                changed['publicFilePins'][name] = sha((root / name).read_bytes())
                with self.assertRaises(ValueError, msg=name):
                    verify_pandemic(changed, root=root)
                (root / name).write_bytes(original)
            inverse = json.loads((root / INVERSE).read_bytes())
            inverse['src/App.tsx']['operations'][0]['baselineText'] += '\n'
            (root / INVERSE).write_text(json.dumps(inverse), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'inverse baseline'):
                restore('src/App.tsx', root)

    def test_asset_mutations(self):
        from verify_renewed_limited_publish import verify_assets
        with tempfile.TemporaryDirectory(prefix='pandemic-assets-') as directory:
            root = Path(directory)
            (root / 'index.html').write_text('<html></html>', encoding='utf-8')
            with self.assertRaises(ValueError):
                verify_assets(root, self.receipt)
            (root / 'unapproved.txt').write_text('extra', encoding='utf-8')
            with self.assertRaises(ValueError):
                verify_assets(root, self.receipt)


if __name__ == '__main__':
    unittest.main()
