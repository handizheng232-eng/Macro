"""Fail-closed overview scope, inverse, immutable evidence, and asset checks."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from verify_inflation_overview_publish import ROOT, RECEIPT, HEATMAP, INVERSE, restore, previous_root, verify_overview, sha


class OverviewPublicationTests(unittest.TestCase):
    def setUp(self):
        self.receipt = json.loads((ROOT / RECEIPT).read_bytes())

    def test_authorized_full_chain(self):
        result = verify_overview(self.receipt)
        self.assertTrue(result['legacyGateReplayed'])
        self.assertEqual(result['heatmapTables'], 3)
        self.assertEqual(result['officialParagraphs'], 16)
        self.assertEqual(result['overviewPeriods'], 8)
        self.assertFalse(result['fullStageReady'])
        with previous_root() as root:
            old = json.loads((root / HEATMAP).read_bytes())
            for name in ('src/App.tsx', 'src/styles.css'):
                self.assertEqual(sha((root / name).read_bytes()), old['publicFilePins'][name])

    def test_authorization_scope_and_pin_set(self):
        for name, value in [('publicationAuthorized', False), ('pageQAComplete', False), ('fullResearchComplete', True), ('scope', 'all-research'), ('legacyReceiptSHA256', '0'*64), ('approvedOverviewSHA256', '0'*64)]:
            changed = copy.deepcopy(self.receipt)
            changed[name] = value
            with self.assertRaises(ValueError):
                verify_overview(changed)
        for mode in ('missing', 'extra', 'altered'):
            changed = copy.deepcopy(self.receipt)
            name = 'src/inflationOverview.ts'
            if mode == 'missing': del changed['publicFilePins'][name]
            if mode == 'extra': changed['publicFilePins']['../escape'] = '0'*64
            if mode == 'altered': changed['publicFilePins'][name] = '0'*64
            with self.assertRaises(ValueError):
                verify_overview(changed)

    def test_mutations_rehashed_outer_pins_still_fail(self):
        with tempfile.TemporaryDirectory(prefix='overview-negative-') as directory:
            root = Path(directory)
            with previous_root() as baseline:
                shutil.copytree(baseline, root, dirs_exist_ok=True)
            for name in set(self.receipt['publicFilePins']) | {RECEIPT}:
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, dest)
            for name in ('src/App.tsx', 'src/styles.css', 'src/inflationOverview.ts', 'src/data/usEmploymentData.json', HEATMAP):
                original = (root / name).read_bytes()
                (root / name).write_bytes(original + b'\n ')
                changed = copy.deepcopy(self.receipt)
                changed['publicFilePins'][name] = sha((root / name).read_bytes())
                with self.assertRaises(ValueError, msg=name):
                    verify_overview(changed, root=root)
                (root / name).write_bytes(original)
            inverse = json.loads((root / INVERSE).read_bytes())
            inverse['src/App.tsx']['operations'][0]['baselineText'] += '\n'
            (root / INVERSE).write_text(json.dumps(inverse), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'inverse baseline'):
                restore('src/App.tsx', root)


if __name__ == '__main__':
    unittest.main()
