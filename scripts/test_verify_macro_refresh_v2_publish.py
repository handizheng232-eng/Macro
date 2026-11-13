"""A mutable, explicitly authorized five-file refresh cannot re-authorize research."""
import importlib.util
import copy
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RollingRefreshTests(unittest.TestCase):
    def test_only_explicit_authorization_and_qa_admit_current_five_files(self):
        path = ROOT / 'scripts/verify_macro_refresh_v2_publish.py'
        self.assertTrue(path.is_file(), 'Missing data-only successor gate')
        spec = importlib.util.spec_from_file_location('verify_macro_refresh_v2_publish', path)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        with self.assertRaises(ValueError):
            gate.verify(gate.make_receipt())
        evidence = {key: gate.sha(b'unit-test evidence, not a publication') for key in gate.EVIDENCE_KEYS}
        receipt = gate.make_receipt(publication_authorized=True, qa_complete=True, evidence_hashes=evidence)
        result = gate.verify(receipt)
        self.assertEqual(result['macroFiles'], 5)
        self.assertFalse(result['historicalResearchAuthorizationExpanded'])
        self.assertTrue(result['legacyGateReplayed'])

    def test_source_history_and_weight_quality_cannot_be_replaced_by_rehashing(self):
        import verify_macro_refresh_v2_publish as gate
        self.assertTrue(hasattr(gate, 'validate_documents'), 'Missing current-data semantic admission')
        documents = {n: json.loads((ROOT / n).read_bytes()) for n in gate.DATA_FILES}
        baseline = {n: json.loads(gate.snapshot_files()[n]) for n in gate.DATA_FILES}
        self.assertGreater(gate.validate_documents(documents, baseline)['datedSeries'], 0)
        for mutation in ('source', 'history', 'nan', 'gdp', 'bucket', 'weight', 'calendar', 'title', 'pceQuality', 'historyCell', 'historyField'):
            changed = copy.deepcopy(documents)
            gdp = changed['src/data/usGdpData.json']
            series = next(s for sec in gdp['sections'].values() for c in sec.get('charts', []) for s in c.get('series', []))
            pce = changed['src/data/usInflationData.json']['actual']['pceDistribution']
            if mutation == 'source': series['source']['code'] = 'WRONG'
            if mutation == 'history': series['dates'].pop(0); series['values'].pop(0)
            if mutation == 'nan': series['values'][-1] = float('nan')
            if mutation == 'gdp':
                chart = next(c for sec in gdp['sections'].values() for c in sec.get('charts', []) if c['id'] == 'growth-contributions')
                chart['series'][0]['values'][-1] += 1
            if mutation == 'bucket': pce['buckets'][0]['values'][-1] += 1
            if mutation == 'weight': pce['latestComponents'][0]['weight'] += 1
            if mutation == 'pceQuality': pce['quality']['latestWeightSum'] = 0
            if mutation == 'historyCell':
                history = changed['src/data/usInflationData.json']['actual']['cpiHeatmap']['history']
                row = next(r for r in history['rows'] if r['id'] == 'cpi_food_yoy')
                index = history['periods'].index('202001')
                self.assertIsNotNone(row['yoy'][index])
                row['yoy'][index] = None
            if mutation == 'historyField':
                history = changed['src/data/usInflationData.json']['actual']['cpiHeatmap']['history']
                row = next(r for r in history['rows'] if r['id'] == 'cpi_food_yoy')
                del row['yoy']
            if mutation == 'calendar': changed['src/data/usInflationData.json']['actual']['cpiHeatmap']['history']['periods'].pop(0)
            if mutation == 'title': gdp['sections']['benchmark']['charts'][0]['title'] = 'unapproved claim'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                gate.validate_documents(changed, baseline)

    def test_authorization_scope_and_exact_pin_sets_fail_closed(self):
        import verify_macro_refresh_v2_publish as gate
        receipt = gate.make_receipt(publication_authorized=True, qa_complete=True,
            evidence_hashes={k: gate.sha(b'unit-test-only') for k in gate.EVIDENCE_KEYS})
        for key, value in [('publicationAuthorized', False), ('pageQAComplete', False),
                           ('historicalResearchAuthorizationExpanded', True), ('scope', 'all-research'),
                           ('snapshotSHA256', '0' * 64)]:
            changed = copy.deepcopy(receipt); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): gate.verify(changed)
        for field in ('dataPins', 'vintages', 'implementationPins', 'infrastructurePins', 'qualityEvidenceHashes'):
            for extra in (True, False):
                changed = copy.deepcopy(receipt)
                if extra: changed[field]['data/raw/private.json'] = '0' * 64
                else: changed[field].pop(next(iter(changed[field])))
                with self.subTest(field=field, extra=extra), self.assertRaises(ValueError): gate.verify(changed)

    def test_rehashed_bad_data_and_unrelated_research_are_still_rejected(self):
        from unittest.mock import patch
        import verify_macro_refresh_v2_publish as gate
        receipt = gate.make_receipt(publication_authorized=True, qa_complete=True,
            evidence_hashes={k: gate.sha(b'unit-test-only') for k in gate.EVIDENCE_KEYS})
        name = 'src/data/usGdpData.json'; doc = json.loads((ROOT / name).read_bytes())
        chart = next(c for sec in doc['sections'].values() for c in sec.get('charts', []) if c['id'] == 'growth-contributions')
        chart['series'][0]['values'][-1] += 1
        raw = json.dumps(doc).encode(); receipt['dataPins'][name] = gate.sha(raw)
        original = Path.read_bytes
        with patch.object(Path, 'read_bytes', lambda p: raw if p == ROOT / name else original(p)), self.assertRaisesRegex(ValueError, 'GDP'):
            gate.verify(receipt)
        protected = next(n for n in gate.snapshot_files() if n.startswith('src/data/') and n not in gate.DATA_FILES)
        changed = original(ROOT / protected) + b'\n'
        receipt = gate.make_receipt(publication_authorized=True, qa_complete=True,
            evidence_hashes={k: gate.sha(b'unit-test-only') for k in gate.EVIDENCE_KEYS})
        receipt['publicFilePins'] = {protected: gate.sha(changed)}
        with patch.object(Path, 'read_bytes', lambda p: changed if p == ROOT / protected else original(p)), self.assertRaisesRegex(ValueError, 'immutable'):
            gate.verify(receipt)


    def test_rehashing_workflow_does_not_authorize_a_larger_test_budget(self):
        from unittest.mock import patch
        import verify_macro_refresh_v2_publish as gate
        name = '.github/workflows/deploy.yml'
        original = Path.read_bytes
        changed = original(ROOT / name).replace(b'--testTimeout=12000', b'--testTimeout=24000')
        self.assertNotEqual(changed, original(ROOT / name))
        receipt = gate.make_receipt(publication_authorized=True, qa_complete=True,
            evidence_hashes={k: gate.sha(b'unit-test-only') for k in gate.EVIDENCE_KEYS})
        receipt['infrastructurePins'][name] = gate.sha(changed)
        with patch.object(Path, 'read_bytes', lambda p: changed if p == ROOT / name else original(p)), self.assertRaisesRegex(ValueError, 'workflow'):
            gate.verify(receipt)


if __name__ == '__main__':
    unittest.main()
