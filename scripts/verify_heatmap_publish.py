"""Versioned additive heatmap release; replay unchanged research gates exactly."""
import argparse
import copy
import hashlib
import json
import math
import tempfile
from contextlib import contextmanager
from pathlib import Path
from verify_economic_mechanisms_publish import verify_economic, RECEIPT as ECONOMIC, READING, RESEARCH
from verify_renewed_easing_publish import require
from verify_renewed_limited_publish import verify_assets

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'release/heatmap-history-publication-01.json'
MACRO_FILES = {'src/data/usEmploymentData.json', 'src/data/usInflationData.json'}
FEATURE_FILES = {
    'src/usEmployment.tsx', 'src/usInflation.tsx', 'src/styles.css',
    'src/heatmapTimeRange.ts', 'src/macroTimeRange.ts',
    'scripts/employment_sector_structure.py', 'scripts/refresh_ifind_us_employment.py',
    'scripts/refresh_ifind_us_inflation.py',
}


def sha(raw):
    return hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()


def tables(doc, name):
    if name.endswith('usInflationData.json'):
        return [doc['actual']['cpiHeatmap']]
    return [doc['sections']['officialSurveys']['sectorMonitor'], doc['sections']['wages']['wageSectorMonitor']]


def restore_macro(name, doc, expected):
    require(name in MACRO_FILES, 'unapproved macro path')
    restored = copy.deepcopy(doc)
    for table in tables(restored, name):
        require('history' in table, 'missing additive history')
        del table['history']
    raw = json.dumps(restored, ensure_ascii=False, indent=2).encode('utf-8')
    require(sha(raw) == expected, 'preceding macro bytes changed outside additive history')
    return raw


def validate_history(table):
    h = table['history']
    periods = h['periods']
    require(len(periods) > 12 and bool(h['note']), 'history absent')
    require(all(isinstance(p, str) and len(p) == 6 and p.isdigit() and 1 <= int(p[4:]) <= 12 for p in periods), 'invalid calendar month')
    ordinals = [int(p[:4]) * 12 + int(p[4:]) for p in periods]
    require(all(a - b == 1 for a, b in zip(ordinals, ordinals[1:])), 'non-contiguous history axis')
    require([r['id'] for r in h['rows']] == [r['id'] for r in table['rows']], 'history row identities differ')
    for old, row in zip(table['rows'], h['rows']):
        for field in ('values', 'yoy', 'mom'):
            if field not in old:
                continue
            values = row[field]
            require(len(values) == len(periods), 'history cell count differs')
            require(all(v is None or isinstance(v, (int, float)) and math.isfinite(v) for v in values), 'nonfinite history cell')
            require(all(p in periods for p in table['periods']), 'legacy month missing')
            require([values[periods.index(p)] for p in table['periods']] == old[field], 'legacy month values changed')
    if 'reconciliation' in h:
        require([c['id'] for c in h['reconciliation']['checks']] == [c['id'] for c in table['reconciliation']['checks']], 'reconciliation identity differs')
        for c in h['reconciliation']['checks']:
            require(len(c['values']) == len(periods), 'reconciliation axis differs')
            require(all(v is None or isinstance(v, (int, float)) and math.isfinite(v) for v in c['values']), 'nonfinite reconciliation')


@contextmanager
def previous_root(root=ROOT):
    """Strip exactly three history objects; bind all restored bytes to old pins."""
    economic = json.loads((root / ECONOMIC).read_bytes())
    names = set(economic['publicFilePins']) | {ECONOMIC, READING, RESEARCH}
    for relative in (READING, RESEARCH):
        names.update(json.loads((root / relative).read_bytes())['publicFilePins'])
    with tempfile.TemporaryDirectory(prefix='heatmap-prior-release-') as directory:
        target = Path(directory)
        for relative in names:
            p = Path(relative)
            require(not p.is_absolute() and '..' not in p.parts and ':' not in relative and '\\' not in relative, 'unsafe projection path')
            raw = (root / p).read_bytes()
            if relative in MACRO_FILES:
                raw = restore_macro(relative, json.loads(raw), economic['publicFilePins'][relative])
            dest = target / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        yield target


def verify_heatmap(receipt, root=ROOT, dist=None):
    require(receipt.get('schemaVersion') == 'heatmap-history-publication-01', 'wrong heatmap contract')
    require(receipt.get('scope') == 'three-heatmap-histories-and-range-controls', 'heatmap scope differs')
    require(receipt.get('publicationAuthorized') is True and receipt.get('pageQAComplete') is True, 'authorization/QA absent')
    require(receipt.get('pinEncoding') == 'git-lf', 'unknown pin encoding')
    legacy = (root / ECONOMIC).read_bytes()
    require(sha(legacy) == receipt['legacyReceiptSHA256'], 'immutable economic receipt changed')
    economic = json.loads(legacy)
    required = set(economic['publicFilePins']) | FEATURE_FILES | {ECONOMIC}
    require(set(receipt['publicFilePins']) == required, 'heatmap pin coverage differs')
    for name, expected in receipt['publicFilePins'].items():
        require(sha((root / name).read_bytes()) == expected, 'public file changed: ' + name)
    count = 0
    for name in MACRO_FILES:
        doc = json.loads((root / name).read_bytes())
        restore_macro(name, doc, economic['publicFilePins'][name])
        for table in tables(doc, name):
            validate_history(table)
            count += 1
    with previous_root(root) as previous:
        result = verify_economic(economic, root=previous)
    if dist is not None:
        result['distFilesScanned'] = verify_assets(dist, receipt)
    result.update(status='PASS_AUTHORIZED_HEATMAP_HISTORY_01', heatmapTables=count,
                  originalMacroFieldsUnchanged=True, legacyGateReplayed=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dist', type=Path)
    args = p.parse_args()
    try:
        print(json.dumps(verify_heatmap(json.loads((ROOT / RECEIPT).read_bytes()), dist=args.dist), ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'status': 'INVALID_HEATMAP_PUBLICATION_01', 'reason': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
