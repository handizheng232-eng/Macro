"""Additive heatmap release retains the exact preceding research releases."""
import copy
import json
import unittest
from verify_heatmap_publish import ROOT, RECEIPT, MACRO_FILES, previous_root, restore_macro, verify_heatmap, validate_history
from verify_economic_mechanisms_publish import RECEIPT as ECONOMIC, verify_economic


class HeatmapPublicationTests(unittest.TestCase):
    def test_current_authorized_release_and_legacy_gate(self):
        receipt = json.loads((ROOT / RECEIPT).read_bytes())
        result = verify_heatmap(receipt)
        self.assertTrue(result['legacyGateReplayed'])
        self.assertFalse(result['fullStageReady'])
        self.assertEqual(result['heatmapTables'], 3)
        with previous_root() as root:
            self.assertEqual(verify_economic(json.loads((root / ECONOMIC).read_bytes()), root=root)['officialParagraphs'], 16)

    def test_non_history_changes_cannot_be_removed_by_projection(self):
        pins = json.loads((ROOT / ECONOMIC).read_bytes())['publicFilePins']
        for name in MACRO_FILES:
            doc = json.loads((ROOT / name).read_bytes())
            changed = copy.deepcopy(doc)
            changed['generatedAt'] = '2099-01-01'
            with self.assertRaisesRegex(ValueError, 'preceding macro bytes'):
                restore_macro(name, changed, pins[name])
            changed = copy.deepcopy(doc)
            changed['unapproved'] = 'extra'
            with self.assertRaises(ValueError):
                restore_macro(name, changed, pins[name])

    def test_authorization_scope_and_all_pins_fail_closed(self):
        receipt = json.loads((ROOT / RECEIPT).read_bytes())
        for key, value in [('schemaVersion', 'wrong'), ('scope', 'all-data'), ('publicationAuthorized', False), ('pageQAComplete', False), ('legacyReceiptSHA256', '0'*64)]:
            changed = copy.deepcopy(receipt)
            changed[key] = value
            with self.assertRaises(ValueError):
                verify_heatmap(changed)
        for name in receipt['publicFilePins']:
            changed = copy.deepcopy(receipt)
            changed['publicFilePins'][name] = '0'*64
            with self.assertRaises(ValueError):
                verify_heatmap(changed)
        changed = copy.deepcopy(receipt)
        changed['publicFilePins']['../escape'] = '0'*64
        with self.assertRaises(ValueError):
            verify_heatmap(changed)

    def test_history_axes_cells_and_recent_parity_are_independent_contracts(self):
        doc = json.loads((ROOT / 'src/data/usInflationData.json').read_bytes())
        table = doc['actual']['cpiHeatmap']
        validate_history(table)
        for mode in ['gap', 'cell-count', 'recent-value', 'row-id', 'nonfinite']:
            changed = copy.deepcopy(table)
            h = changed['history']
            if mode == 'gap': h['periods'][1] = h['periods'][0]
            if mode == 'cell-count': h['rows'][0]['yoy'].pop()
            if mode == 'recent-value': h['rows'][0]['yoy'][0] += 1
            if mode == 'row-id': h['rows'][0]['id'] = 'unknown'
            if mode == 'nonfinite': h['rows'][0]['yoy'][-1] = float('inf')
            with self.assertRaises(ValueError):
                validate_history(changed)


if __name__ == '__main__':
    unittest.main()
