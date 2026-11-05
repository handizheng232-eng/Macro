"""Offline tests replay actual Dallas Fed source bytes; never fetch implicitly."""
import base64
import copy
import importlib.util
import json
import hashlib
import io
import math
import xml.etree.ElementTree as ET
import zipfile
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'scripts/fixtures/pce_distribution_20261105.json'


def fixture():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def replace_body(bundle, key, data):
    resource = bundle['resources'][key]
    resource['body'] = base64.b64encode(data).decode()
    resource['sha256'] = hashlib.sha256(data).hexdigest()


def mutate_cell(bundle, key, reference, value):
    """Mutate official bytes and recompute transport SHA, exercising semantic gates."""
    data = io.BytesIO()
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(bundle['resources'][key]['body']))) as source:
        with zipfile.ZipFile(data, 'w', zipfile.ZIP_DEFLATED) as target:
            for name in source.namelist():
                content = source.read(name)
                if name == 'xl/worksheets/sheet1.xml':
                    tree = ET.fromstring(content)
                    cell = next(c for c in tree.findall('.//s:c', ns) if c.get('r') == reference)
                    for child in list(cell):
                        cell.remove(child)
                    if value is not None:
                        cell.set('t', 'str' if isinstance(value, str) else 'n')
                        ET.SubElement(cell, '{' + ns['s'] + '}v').text = str(value)
                    content = ET.tostring(tree)
                target.writestr(name, content)
    replace_body(bundle, key, data.getvalue())


class PceDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = Path(os.environ.get('TMPDIR') or ROOT / 'data/raw/pce-test-tmp')
        cls.scratch.mkdir(parents=True, exist_ok=True)

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.pce_distribution'),
                             'Missing standard-library Dallas XLSX replay module')
        from scripts import pce_distribution
        return pce_distribution

    def test_real_xlsx_relationships_shared_strings_cached_values_dates(self):
        mod = self.module()
        raw = fixture()
        chart = mod.read_xlsx(base64.b64decode(raw['resources']['chart']['body']), 'Web - Chart Data')
        detail = mod.read_xlsx(base64.b64decode(raw['resources']['detail']['body']), 'Web - Underlying detail')
        self.assertEqual(chart['A4'], 'Rose at 0-2% rate')
        self.assertEqual(mod.excel_month(chart['B3']), '202509')
        self.assertEqual(mod.excel_month(chart['N3']), '202609')
        self.assertEqual(detail['B2'], 'Annualized 1-month % change')
        self.assertAlmostEqual(chart['N4'], 6.25029260707453, places=12)
        self.assertLess(detail['B3'], 0)

    def test_real_distribution_replays_all_months_and_latest_components(self):
        mod = self.module()
        self.assertTrue(hasattr(mod, 'build_distribution'), 'Missing complete Dallas replay builder')
        result = mod.build_distribution(fixture())
        self.assertEqual(result['periods'], ['202509', '202510', '202511', '202512', '202601', '202602', '202603', '202604', '202605', '202606', '202607', '202608', '202609'])
        self.assertEqual([b['id'] for b in result['buckets']], ['nonpositive', '0-2', '2-3', '3-5', '5-10', 'gt10'])
        self.assertEqual(result['quality']['latestComponentCount'], 177)
        self.assertAlmostEqual(result['quality']['latestWeightSum'], 100, places=10)
        self.assertLess(result['quality']['latestBucketMaxDifference'], 1e-10)
        self.assertLess(result['quality']['maximumSumResidual'], 1e-10)
        self.assertEqual(result['source']['latestObservation'], '202609')
        self.assertEqual(result['source']['detailObservation'], None)
        self.assertEqual(result['source']['fetchedAt'], fixture()['resources']['detail']['fetchedAt'])
        zero = sum(c['weight'] for c in result['latestComponents'] if c['annualizedRate'] == 0)
        self.assertGreater(zero, 0)
        self.assertIn('不是同比', result['methodology']['rate'])
        self.assertIn('不是两个月名义支出占比', result['methodology']['weight'])
        for bucket in result['buckets']:
            self.assertEqual(len(bucket['values']), 13)
        # Pin original transport bytes and compare every historical published cell,
        # not only latest values or the tautological residual-based sum.
        self.assertEqual(fixture()['resources']['chart']['sha256'], '87188f3257b1de70bc0f4321f5f672d15163fd99ff687bb2eff15cd4dc4240cd')
        self.assertEqual(fixture()['resources']['detail']['sha256'], '9527a5718a4eb8ab7c537c4d3b9918480646599d117b04feffd1c33d1e0340ce')
        chart = mod.parse_tables(fixture())['chart']
        for row, bucket in enumerate(result['buckets'][1:], 4):
            for column, value in enumerate(bucket['values'], ord('B')):
                self.assertEqual(value, chart[f'{chr(column)}{row}'])
        for i, value in enumerate(result['buckets'][0]['values']):
            self.assertEqual(value, 100 - math.fsum(b['values'][i] for b in result['buckets'][1:]))
        expected = [25.5764046658457, 6.25029260707453, 15.5276880449415, 25.840403256328, 10.1602334209278, 16.6449780048825]
        for b, value in zip(result['buckets'], expected):
            self.assertAlmostEqual(b['values'][-1], value, places=10)

    def test_semantically_invalid_source_cells_fail_closed(self):
        cases = [
            ('chart', 'A4', 'Rose at 0-3% rate', 'header'),
            ('detail', 'B2', '12-month % change', 'header'),
            ('chart', 'B4', 101, 'range'), ('chart', 'B4', -1, 'range'),
            ('chart', 'B4', float('nan'), 'finite'),
            ('chart', 'B4', None, 'missing'),
            ('chart', 'B4', 99, 'total'),
            ('detail', 'C3', -1, 'weight'), ('detail', 'C3', 101, 'weight'),
            ('detail', 'B3', float('inf'), 'finite'),
            ('detail', 'C3', None, 'missing'),
            ('detail', 'A3', None, 'missing'),
            ('detail', 'D3', 7, 'cumulative'),
            ('chart', 'N4', 7, 'closure'),
            ('chart', 'C3', None, 'month'),
            ('chart', 'C3', 45901, 'month'),
            ('chart', 'N3', 46296, 'month'),
        ]
        for key, ref, value, reason in cases:
            with self.subTest(key=key, cell=ref, reason=reason):
                raw = fixture()
                mutate_cell(raw, key, ref, value)
                with self.assertRaises(ValueError):
                    self.module().build_distribution(raw)

    def test_metadata_hash_month_and_parsed_table_tampering_rejected(self):
        for kind in ['hash', 'month', 'timestamp', 'url', 'schema', 'tables', 'batch']:
            with self.subTest(kind=kind):
                raw = fixture()
                if kind == 'hash':
                    raw['resources']['chart']['sha256'] = '0' * 64
                elif kind == 'month':
                    page = base64.b64decode(raw['resources']['page']['body']).replace(b'September 2026', b'August 2026')
                    replace_body(raw, 'page', page)
                elif kind == 'timestamp':
                    raw['resources']['chart']['fetchedAt'] = '2026-11-05'
                elif kind == 'url':
                    raw['resources']['chart']['url'] = raw['resources']['detail']['url']
                elif kind == 'schema':
                    raw['schemaVersion'] = 2
                elif kind == 'tables':
                    raw['tables'] = {'chart': {}, 'detail': {}}
                else:
                    raw['resources']['detail']['fetchedAt'] = '2026-10-05T00:17:39+00:00'
                with self.assertRaises(ValueError):
                    self.module().build_distribution(raw)

    def test_exact_bucket_boundaries_and_no_rounding(self):
        mod = self.module()
        for value, expected in [(-1, 0), (0, 0), (0.000001, 1), (2, 1), (2.000001, 2),
                                (3, 2), (3.000001, 3), (5, 3), (5.000001, 4), (10, 4), (10.000001, 5)]:
            self.assertEqual(mod.bucket_index(value), expected)
        for invalid in [float('inf'), float('-inf'), float('nan')]:
            with self.assertRaises(ValueError):
                mod.bucket_index(invalid)

    def test_fetch_archives_exact_workbook_bytes_with_replayable_tables_and_backups(self):
        mod = self.module()
        self.assertTrue(hasattr(mod, 'fetch_distribution'), 'Missing real Dallas network/archive path')
        original = fixture()['resources']
        by_url = {r['url']: r for r in original.values()}
        def open_response(request, timeout):
            return io.BytesIO(base64.b64decode(by_url[request.full_url]['body']))
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            raw_dir, backup_dir = Path(folder) / 'raw', Path(folder) / 'durable'
            with patch('urllib.request.urlopen', side_effect=open_response) as network:
                bundle = mod.fetch_distribution(raw_dir, backup_dir)
            self.assertEqual(network.call_count, 3)
            self.assertEqual(bundle['tables'], mod.parse_tables(bundle))
            result = mod.build_distribution(bundle)
            self.assertEqual(result['quality']['latestComponentCount'], 177)
            for name, resource in bundle['resources'].items():
                self.assertEqual(resource['sha256'], original[name]['sha256'])
                for field in ['rawPath', 'backupPath']:
                    self.assertEqual(Path(resource[field]).read_bytes(), base64.b64decode(original[name]['body']))
            # The archived bundle must remain replayable after source files vanish.
            saved = json.loads(Path(bundle['archivePath']).read_text(encoding='utf-8'))
            with patch('urllib.request.urlopen', side_effect=AssertionError('offline')):
                self.assertEqual(mod.build_distribution(saved), result)

    def test_build_dataset_integrates_optional_key_without_network_or_changing_existing_series(self):
        from scripts import refresh_ifind_us_inflation as inflation
        raw = synthetic_ifind()
        baseline = inflation.build_dataset(raw, 'old-ifind-time', 'original.json')
        raw['__pceDistribution'] = fixture()
        with patch('urllib.request.urlopen', side_effect=AssertionError('offline')):
            combined = inflation.build_dataset(raw, 'old-ifind-time', 'original.json')
        self.assertIn('pceDistribution', combined['actual'])
        self.assertEqual(combined['actual'].pop('pceDistribution'), self.module().build_distribution(fixture()))
        self.assertEqual(combined.pop('sourceProviders'), ['iFinD EDB', 'Federal Reserve Bank of Dallas'])
        self.assertEqual(combined.pop('source'), 'iFinD EDB；PCE分项涨幅分布来自Dallas Fed官方')
        baseline.pop('sourceProviders')
        baseline.pop('source')
        self.assertEqual(combined, baseline)

    def test_fresh_cli_fetches_dallas_but_failure_preserves_output(self):
        from scripts import refresh_ifind_us_inflation as inflation
        self.assertTrue(hasattr(inflation, 'fetch_distribution'), 'CLI has not integrated Dallas fetching')
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            output = Path(folder) / 'output.json'
            output.write_text('original')
            args = ['refresh_ifind_us_inflation.py', '--output', str(output), '--raw-dir', str(Path(folder) / 'raw')]
            with patch('sys.argv', args), patch.object(inflation, 'read_token', return_value=('redacted', Path('client.log'))), \
                    patch.object(inflation, 'fetch_all', return_value=synthetic_ifind()), \
                    patch.object(inflation, 'fetch_distribution', side_effect=urllib.error.URLError('unavailable')) as fetch:
                with self.assertRaises(urllib.error.URLError):
                    inflation.main()
            fetch.assert_called_once()
            self.assertEqual(output.read_text(), 'original')

    def test_cli_full_bundle_replay_is_offline_and_invalid_source_preserves_output(self):
        from scripts import refresh_ifind_us_inflation as inflation
        raw = synthetic_ifind()
        raw['__pceDistribution'] = fixture()
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            input_path, output = Path(folder) / 'bundle.json', Path(folder) / 'output.json'
            input_path.write_text(json.dumps(raw), encoding='utf-8')
            args = ['refresh_ifind_us_inflation.py', '--input', str(input_path), '--output', str(output)]
            with patch('sys.argv', args), patch('urllib.request.urlopen', side_effect=AssertionError('offline')):
                inflation.main()
            saved = output.read_bytes()
            self.assertIn('pceDistribution', json.loads(saved)['actual'])
            mutate_cell(raw['__pceDistribution'], 'chart', 'N4', 101)
            input_path.write_text(json.dumps(raw), encoding='utf-8')
            with patch('sys.argv', args), self.assertRaises(ValueError):
                inflation.main()
            self.assertEqual(output.read_bytes(), saved)

    def test_fresh_cli_supports_external_raw_dir_and_saves_complete_bundle(self):
        from scripts import refresh_ifind_us_inflation as inflation
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            raw_dir, output = Path(folder) / 'raw', Path(folder) / 'output.json'
            args = ['refresh_ifind_us_inflation.py', '--output', str(output), '--raw-dir', str(raw_dir)]
            with patch('sys.argv', args), patch.object(inflation, 'read_token', return_value=('redacted', Path('client.log'))), \
                    patch.object(inflation, 'fetch_all', return_value=synthetic_ifind()), \
                    patch.object(inflation, 'fetch_distribution', return_value=fixture()):
                inflation.main()
            result = json.loads(output.read_text(encoding='utf-8'))
            saved_bundle = json.loads(Path(result['rawSnapshots']['ifind']).read_text(encoding='utf-8'))
            self.assertEqual(saved_bundle['__pceDistribution'], fixture())
            self.assertEqual(result['actual']['pceDistribution'], self.module().build_distribution(fixture()))

    def test_cli_legacy_bundle_cannot_silently_remove_distribution(self):
        from scripts import refresh_ifind_us_inflation as inflation
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            source, output = Path(folder) / 'raw.json', Path(folder) / 'output.json'
            source.write_text(json.dumps(synthetic_ifind()), encoding='utf-8')
            output.write_bytes(b'previous valid distribution')
            with patch('sys.argv', ['refresh', '--input', str(source), '--output', str(output)]):
                with self.assertRaisesRegex(ValueError, '__pceDistribution'):
                    inflation.main()
            self.assertEqual(output.read_bytes(), b'previous valid distribution')

    def test_publication_backs_up_original_bytes_before_replace(self):
        from scripts import refresh_ifind_us_inflation as inflation
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            root = Path(folder)
            target, backups = root / 'data.json', root / 'backups'
            target.write_bytes(b'original bytes\r\n')
            inflation.write_dataset(target, {'value': 3}, backup_dir=backups)
            self.assertEqual([p.read_bytes() for p in backups.glob('*')], [b'original bytes\r\n'])
            self.assertEqual(json.loads(target.read_bytes()), {'value': 3})
            self.assertNotIn(b'\r\n', target.read_bytes())

    def test_atomic_publication_preserves_existing_json_on_replace_failure(self):
        from scripts import refresh_ifind_us_inflation as inflation
        self.assertTrue(hasattr(inflation, 'write_dataset'), 'Missing atomic validated dataset writer')
        with tempfile.TemporaryDirectory(dir=self.scratch) as folder:
            target = Path(folder) / 'data.json'
            target.write_bytes(b'original')
            with patch('os.replace', side_effect=OSError('disk error')), self.assertRaises(OSError):
                inflation.write_dataset(target, {'value': 3})
            self.assertEqual(target.read_bytes(), b'original')
            self.assertEqual([p.name for p in Path(folder).iterdir()], ['data.json'])
            with self.assertRaises(ValueError):
                inflation.write_dataset(target, {'value': float('nan')})
            self.assertEqual(target.read_bytes(), b'original')
            inflation.write_dataset(target, {'value': 3})
            self.assertEqual(json.loads(target.read_bytes()), {'value': 3})


def synthetic_ifind():
    from scripts.refresh_ifind_us_inflation import SERIES_SPEC
    dates = [f'{year}{month:02d}28' for year in [2025, 2026] for month in range(1, 13)]
    return {key: {'code': 1, 'data': {'tables': [{'displayid': spec[0], 'time': dates, 'value': [3.0] * len(dates)}]}}
            for key, spec in SERIES_SPEC.items()}


if __name__ == '__main__':
    unittest.main()
