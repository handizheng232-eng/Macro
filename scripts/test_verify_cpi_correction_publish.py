"""Synthetic approval fixtures never constitute publication or source evidence."""
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class CorrectionAdmissionTests(unittest.TestCase):
    def test_default_authorization_is_closed_and_reference_is_deterministic(self):
        path = ROOT / 'scripts/verify_cpi_correction_publish.py'
        self.assertTrue(path.is_file(), 'Missing independently authorized CPI correction gate')
        import verify_cpi_correction_publish as gate
        with self.fixture(gate) as (root, bindings):
            first, raw = gate.make_authorization(root, source_files=gate.REQUIRED_SOURCE_FILES,
                sa_bindings=bindings, inflation_change_paths=[['actual', 'cpiHeatmap'], ['actual', 'cpiSeasonality']],
                source_audit_sha256=gate.sha(b'unit-test evidence only'))
            second, again = gate.make_authorization(root, source_files=gate.REQUIRED_SOURCE_FILES,
                sa_bindings=bindings, inflation_change_paths=[['actual', 'cpiHeatmap'], ['actual', 'cpiSeasonality']],
                source_audit_sha256=gate.sha(b'unit-test evidence only'))
            self.assertEqual((first, raw), (second, again))
            self.assertFalse(first['correctionAuthorized'])
            self.assertFalse(first['sourceReviewComplete'])
            self.assertEqual(json.loads(gzip.decompress(raw)), json.loads((root / gate.INFLATION).read_bytes()))
            self.persist(root, gate, first, raw)
            with self.assertRaisesRegex(ValueError, 'authorization|binding'):
                gate.load_authorization(root)

    def test_reviewed_reference_and_source_approval_cannot_be_rehashed(self):
        import verify_cpi_correction_publish as gate
        with self.fixture(gate) as (root, bindings):
            approval, raw = gate.make_authorization(root, source_files=gate.REQUIRED_SOURCE_FILES,
                sa_bindings=bindings, inflation_change_paths=[['actual', 'cpiHeatmap'], ['actual', 'cpiSeasonality']],
                source_audit_sha256=gate.sha(b'unit-test only'), correction_authorized=True, source_review_complete=True)
            self.persist(root, gate, approval, raw)
            with patch.object(gate, 'AUTHORIZATION_SHA256', gate.sha((root / gate.AUTHORIZATION).read_bytes())):
                loaded = gate.load_authorization(root)
                self.assertIsInstance(loaded, tuple, 'Loader must validate and return the frozen corrected document')
                self.assertEqual(loaded[0], approval)
                for name in (gate.CORRECTED_REFERENCE, 'scripts/cpi_seasonality.py', gate.AUTHORIZATION):
                    path = root / name; original = path.read_bytes(); path.write_bytes(original + b'\n')
                    with self.subTest(path=name), self.assertRaises(ValueError):
                        gate.load_authorization(root)
                    path.write_bytes(original)

    def test_source_metadata_scope_and_non_cpi_data_are_not_blanket_authorized(self):
        import verify_cpi_correction_publish as gate
        with self.fixture(gate) as (root, bindings):
            document = json.loads((root / gate.INFLATION).read_bytes())
            for mutation in ('nsa', 'label_only', 'missing_row', 'foreign_path', 'foreign_source', 'pce'):
                changed = copy.deepcopy(document); changed_bindings = copy.deepcopy(bindings)
                if mutation == 'nsa': changed['actual']['cpiHeatmap']['rows'][0]['momSource']['code'] = 'G002600387'
                if mutation == 'label_only': del changed['actual']['cpiHeatmap']['rows'][0]['momSource']['seasonalAdjustment']
                if mutation == 'missing_row': changed_bindings.pop()
                if mutation == 'foreign_path': changed_bindings[0]['paths'][0] = ['actual', 'cpiSeasonality', 'cpi']
                if mutation == 'pce': changed['actual']['pceTrend']['series'][0]['values'][-1] += 1
                (root / gate.INFLATION).write_bytes(gate.canonical(changed))
                files = gate.REQUIRED_SOURCE_FILES | ({'src/historyReplay.tsx'} if mutation == 'foreign_source' else set())
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    gate.make_authorization(root, source_files=files, sa_bindings=changed_bindings,
                        inflation_change_paths=[['actual', 'cpiHeatmap'], ['actual', 'cpiSeasonality']],
                        source_audit_sha256=gate.sha(b'unit-test only'))

    def test_current_quality_uses_corrected_reference_and_keeps_original_assertions(self):
        import verify_cpi_correction_publish as gate
        self.assertTrue(hasattr(gate, 'validate_current'), 'Missing corrected-reference quality admission')
        with self.fixture(gate) as (root, bindings):
            approval, raw = gate.make_authorization(root, source_files=gate.REQUIRED_SOURCE_FILES,
                sa_bindings=bindings, inflation_change_paths=[['actual', 'cpiHeatmap'], ['actual', 'cpiSeasonality']],
                source_audit_sha256=gate.sha(b'unit-test only'))
            reference = json.loads(gzip.decompress(raw))
            documents = {n: json.loads((root / n).read_bytes()) for n in gate.DATA_FILES}
            baseline = {n: json.loads(v) for n, v in gate.snapshot_files(root).items() if n in gate.DATA_FILES}
            baseline[gate.INFLATION] = reference
            report = gate.validate_current(documents, baseline, approval, root)
            self.assertEqual(report['totalRows'], 23)
            self.assertEqual(report['saRows'], 21)
            self.assertEqual(report['nsaRows'], 2)
            self.assertEqual(report['independentMomSources'], {'total': 24, 'SA': 22, 'NSA': 2})
            revised = copy.deepcopy(documents)
            # Legitimate value revisions remain possible, unlike source replacement.
            chart = revised[gate.INFLATION]['actual']['cpiTrend']['series'][0]
            chart['values'][-1] += 0.1
            self.assertGreater(gate.validate_current(revised, baseline, approval, root)['datedSeries'], 0)
            for mutation in ('source', 'sa_flag', 'history_cell', 'history_field', 'gdp', 'pce'):
                changed = copy.deepcopy(documents)
                table = changed[gate.INFLATION]['actual']['cpiHeatmap']
                if mutation == 'source': table['rows'][0]['momSource']['code'] = 'G002600387'
                if mutation == 'sa_flag': table['rows'][0]['momSource']['seasonalAdjustment'] = 'NSA'
                if mutation == 'history_cell':
                    row = table['history']['rows'][0]; i = next(i for i,v in enumerate(row['mom']) if v is not None); row['mom'][i] = None
                if mutation == 'history_field': del table['history']['rows'][0]['mom']
                if mutation == 'gdp':
                    chart = next(c for sec in changed['src/data/usGdpData.json']['sections'].values() for c in sec.get('charts', []) if c['id'] == 'growth-contributions')
                    chart['series'][0]['values'][-1] += 1
                if mutation == 'pce': changed[gate.INFLATION]['actual']['pceDistribution']['latestComponents'][0]['weight'] += 1
                expected_error = {
                    'source': 'Ordinary CPI mom', 'sa_flag': 'Explicit SA',
                    'history_cell': 'previous historical table observations became missing',
                    'history_field': 'historical measurement field removed or changed',
                    'gdp': 'GDP published-precision closure failed',
                    'pce': 'PCE component weights do not close',
                }[mutation]
                with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, expected_error):
                    gate.validate_current(changed, baseline, approval, root)

    def test_per_run_receipt_and_frozen_research_are_independently_verified(self):
        import verify_cpi_correction_publish as gate
        self.assertTrue(hasattr(gate, 'verify'), 'Missing actual correction publication verifier')
        with self.fixture(gate) as (root, bindings):
            for name in gate.IMPLEMENTATION | gate.INFRASTRUCTURE:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((ROOT / name).read_bytes())
            approval, raw = gate.make_authorization(root, source_files=gate.REQUIRED_SOURCE_FILES,
                sa_bindings=bindings, inflation_change_paths=[['actual', 'cpiHeatmap'], ['actual', 'cpiSeasonality']],
                source_audit_sha256=gate.sha(b'unit-test only'), correction_authorized=True, source_review_complete=True)
            self.persist(root, gate, approval, raw)
            evidence = {k: gate.sha(b'unit-test evidence only') for k in gate.EVIDENCE_KEYS}
            with patch.object(gate, 'AUTHORIZATION_SHA256', gate.sha((root / gate.AUTHORIZATION).read_bytes())):
                with self.assertRaisesRegex(ValueError, 'authorization|QA'):
                    gate.verify(gate.make_receipt(root), root)
                receipt = gate.make_receipt(root, publication_authorized=True, qa_complete=True, evidence_hashes=evidence)
                result = gate.verify(receipt, root)
                self.assertTrue(result['legacyGateReplayed'])
                self.assertEqual(result['macroFiles'], 5)
                self.assertFalse(result['historicalResearchAuthorizationExpanded'])
                # A later verified data update needs only a fresh per-run receipt,
                # not re-approval of sources or replacement of the fixed reference.
                document = json.loads((root / gate.INFLATION).read_bytes())
                document['actual']['cpiTrend']['series'][0]['values'][-1] += 0.1
                (root / gate.INFLATION).write_bytes(gate.canonical(document))
                refreshed = gate.make_receipt(root, publication_authorized=True, qa_complete=True, evidence_hashes=evidence)
                self.assertNotEqual(receipt['dataPins'], refreshed['dataPins'])
                self.assertEqual(receipt['approvalPins'], refreshed['approvalPins'])
                self.assertEqual(gate.verify(refreshed, root)['macroFiles'], 5)
                for field in ('dataPins', 'implementationPins', 'infrastructurePins', 'approvalPins', 'vintages', 'qualityEvidenceHashes'):
                    invalid = copy.deepcopy(refreshed); invalid[field]['src/unapproved.json'] = '0' * 64
                    with self.subTest(field=field), self.assertRaises(ValueError): gate.verify(invalid, root)
                for name in ('src/data/replayTagDefinitions.json', 'release/macro-refresh-publication-02.json'):
                    # Choose a real frozen public file; no fabricated research data.
                    if not (root / name).exists(): name = 'package.json'
                    original = (root / name).read_bytes(); (root / name).write_bytes(original + b'\n')
                    with self.subTest(frozen=name), self.assertRaisesRegex(ValueError, 'immutable'):
                        gate.verify(gate.make_receipt(root, publication_authorized=True, qa_complete=True, evidence_hashes=evidence), root)
                    (root / name).write_bytes(original)
                for name in gate.INFRASTRUCTURE:
                    original = (root / name).read_bytes()
                    changed = original.replace(b'--testTimeout=12000', b'--testTimeout=24000') if name.endswith('.yml') else original + b'\n# weakened runner\n'
                    (root / name).write_bytes(changed)
                    with self.subTest(infrastructure=name), self.assertRaisesRegex(ValueError, 'workflow|runner'):
                        gate.verify(gate.make_receipt(root, publication_authorized=True, qa_complete=True, evidence_hashes=evidence), root)
                    (root / name).write_bytes(original)

    def test_named_semantic_checker_is_required_and_executed(self):
        import verify_cpi_correction_publish as gate
        self.assertTrue(hasattr(gate, 'semantic_guard'), 'Missing current CPI semantic checker integration')
        with self.fixture(gate) as (root, _bindings):
            document = json.loads((root / gate.INFLATION).read_bytes())
            gate.semantic_guard(document, root)
            document['testSemanticFailure'] = True
            with self.assertRaisesRegex(ValueError, 'semantic guard'):
                gate.semantic_guard(document, root)
            (root / 'scripts/cpi_seasonality.py').write_text('# checker removed\n')
            with self.assertRaisesRegex(ValueError, 'validate_dataset'):
                gate.semantic_guard(document, root)

    def test_public_scope_rejects_unapproved_added_research(self):
        import verify_cpi_correction_publish as gate
        self.assertTrue(hasattr(gate, 'check_public_scope'), 'Missing closed public file scope')
        with self.fixture(gate) as (root, _bindings):
            base = gate.snapshot_files(root)
            gate.check_public_scope(root, base, gate.REQUIRED_SOURCE_FILES)
            for name in ('src/newResearch.ts', 'scripts/unapproved_contract.py', 'docs/unapproved.md', 'public/unapproved.svg'):
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('not approved')
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Unapproved public'):
                    gate.check_public_scope(root, base, gate.REQUIRED_SOURCE_FILES)
                path.unlink()

    def test_only_exact_exception_roles_codes_names_and_basis_are_admitted(self):
        import verify_cpi_correction_publish as gate
        with self.fixture(gate) as (root, bindings):
            document = json.loads((root / gate.INFLATION).read_bytes())
            valid = gate.bind_sources(document, bindings)
            self.assertEqual(sum(b['identity']['seasonalAdjustment'] == 'NSA' for b in valid), 2)
            rows = document['actual']['cpiHeatmap']['rows']
            food = next(i for i, r in enumerate(rows) if r['id'] == 'food_away_yoy')
            misc = next(i for i, r in enumerate(rows) if r['id'] == 'personal_services_yoy')
            cases = [(food, 'seasonalAdjustment', 'SA', 'Registered NSA'),
                     (misc, 'name', '美国:CPI:服务(不含能源):其他:环比', 'Registered NSA'),
                     (misc, 'code', 'G004765676', 'Registered NSA'),
                     (misc, 'entityAlias', 'Other personal services', 'Registered NSA'),
                     (food, 'adjustmentBasis', 'all-history-NSA', 'Registered NSA'),
                     (0, 'seasonalAdjustment', 'NSA', 'Explicit SA'),
                     (0, 'code', 'G002600387', 'Ordinary CPI mom')]
            for index, field, value, message in cases:
                wrong = copy.deepcopy(document)
                for collection in (wrong['actual']['cpiHeatmap']['rows'], wrong['actual']['cpiHeatmap']['history']['rows']):
                    collection[index]['momSource'][field] = value
                with self.subTest(index=index, field=field), self.assertRaisesRegex(ValueError, message):
                    gate.bind_sources(wrong, bindings)
            wrong = copy.deepcopy(document)
            for collection in (wrong['actual']['cpiHeatmap']['rows'], wrong['actual']['cpiHeatmap']['history']['rows']):
                collection[0]['momSource'] = copy.deepcopy(collection[food]['momSource'])
            with self.assertRaisesRegex(ValueError, 'Explicit SA'):
                gate.bind_sources(wrong, bindings)
            for role in ('cpi', 'core'):
                wrong = copy.deepcopy(document)
                wrong['actual']['cpiSeasonality'][role]['seasonalAdjustment'] = 'NSA'
                with self.subTest(role=role), self.assertRaisesRegex(ValueError, 'Explicit SA'):
                    gate.bind_sources(wrong, bindings)

    from contextlib import contextmanager

    @contextmanager
    def fixture(self, gate):
        # Real baseline bytes; contract identities attached to old values are synthetic, not evidence.
        with tempfile.TemporaryDirectory(prefix='test-cpi-approval-') as folder:
            root = Path(folder)
            for name, raw in gate.snapshot_files().items():
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
            (root / gate.SNAPSHOT).write_bytes((ROOT / gate.SNAPSHOT).read_bytes())
            (root / 'scripts/cpi_seasonality.py').write_text('# unit-test fixture only\ndef validate_dataset(dataset):\n    if dataset.get("testSemanticFailure"):\n        raise ValueError("CPI semantic guard rejected fixture")\n')
            fixture = root / 'scripts/fixtures/cpi_sa_contract.json'
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_bytes((ROOT / 'scripts/fixtures/cpi_sa_contract.json').read_bytes())
            doc = json.loads((root / gate.INFLATION).read_bytes())
            from cpi_seasonality import source_metadata
            table = doc['actual']['cpiHeatmap']; bindings = []
            for i, row in enumerate(table['rows']):
                source = source_metadata(row['id'].removesuffix('_yoy') + '_mom')
                row['momSource'] = dict(source); table['history']['rows'][i]['momSource'] = dict(source)
                bindings.append({'role': 'row:' + row['id'], 'paths': [
                    ['actual', 'cpiHeatmap', 'rows', i, 'momSource'],
                    ['actual', 'cpiHeatmap', 'history', 'rows', i, 'momSource']]})
            doc['actual']['cpiSeasonality'] = {
                'cpi': source_metadata('cpi_mom'),
                'core': source_metadata('core_cpi_mom')}
            for role in ('cpi', 'core'):
                bindings.append({'role': 'headline:' + role, 'paths': [['actual', 'cpiSeasonality', role]]})
            (root / gate.INFLATION).write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
            yield root, bindings

    def persist(self, root, gate, authorization, raw):
        (root / gate.AUTHORIZATION).write_text(json.dumps(authorization), encoding='utf-8')
        (root / gate.CORRECTED_REFERENCE).write_bytes(raw)


if __name__ == '__main__':
    unittest.main()
