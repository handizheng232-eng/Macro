"""Publish a validated five-file macro vintage without rebinding historical research.

Current data and built assets receive a new receipt. Every historical research
file and its unchanged gate are checked against a frozen public-only snapshot.
"""
import argparse
import hashlib
import json
from pathlib import Path
from macro_publication_snapshot import baseline_root, BASE_RECEIPT, SNAPSHOT_SHA, run_legacy_tests
from verify_rate_liftoff_publish_03 import verify as verify_previous
from verify_rate_liftoff_publish import verify_assets
from verify_renewed_easing_publish import require

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'release/macro-refresh-publication-01.json'
DATA_FILES = {'src/data/' + name for name in (
    'usGdpData.json', 'usEmploymentData.json', 'usInflationData.json',
    'usConsumptionData.json', 'usLateModulesData.json',
)}
INFRASTRUCTURE = {
    '.github/workflows/deploy.yml', '.gitattributes', 'scripts/run_data_tests.py',
    'scripts/refresh_ifind_us_gdp.py', 'scripts/refresh_ifind_us_employment.py',
    'scripts/refresh_ifind_us_inflation.py', 'scripts/refresh_ifind_us_consumption.py',
    'scripts/refresh_ifind_us_late_modules.py',
    'scripts/test_refresh_ifind_us_gdp.py',
    'src/historyReplay.testHelpers.tsx', 'src/historyReplayRouting.test.tsx',
    'src/historyReplayRenewedRouting.test.tsx', 'src/taperCitation.test.tsx', 'src/taperPriority.test.tsx',
    'src/historyReplayTestHelpers.test.tsx',
}
IMPLEMENTATION = {
    'scripts/macro_publication_snapshot.py', 'scripts/verify_macro_refresh_publish.py',
    'scripts/test_macro_publication_snapshot.py', 'scripts/test_verify_macro_refresh_publish.py',
    'scripts/test_macro_precision_contracts.py', 'docs/macro-refresh-publication.md',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def make_receipt(root=ROOT, *, authorized=False, qa_complete=False):
    with baseline_root(root) as previous:
        old = json.loads((previous / BASE_RECEIPT).read_bytes())
        baseline_pins = {**old['publicFilePins'], BASE_RECEIPT: sha((previous / BASE_RECEIPT).read_bytes())}
        changed = {}
        for name, expected in baseline_pins.items():
            if name in DATA_FILES:
                continue
            actual = sha((root / name).read_bytes())
            if actual != expected:
                require(name in INFRASTRUCTURE, 'outside authorized infrastructure scope: ' + name)
                changed[name] = actual
    dist = root / 'dist'
    return {
        'schemaVersion': 'macro-refresh-publication-01',
        'scope': 'us-nine-modules-five-macro-snapshots',
        'publicationAuthorized': authorized, 'pageQAComplete': qa_complete,
        'snapshotSHA256': SNAPSHOT_SHA,
        'dataPins': {n: sha((root / n).read_bytes()) for n in sorted(DATA_FILES)},
        'infrastructurePins': changed,
        'implementationPins': {n: sha((root / n).read_bytes()) for n in sorted(IMPLEMENTATION)},
        'distPins': {p.relative_to(dist).as_posix(): sha(p.read_bytes().replace(b'\r\n', b'\n') if p.name == 'index.html' else p.read_bytes()) for p in sorted(dist.rglob('*')) if p.is_file()},
        'vintages': {n: json.loads((root / n).read_bytes())['generatedAt'] for n in sorted(DATA_FILES)},
    }


def verify(receipt, root=ROOT, dist=None):
    require(receipt.get('schemaVersion') == 'macro-refresh-publication-01', 'wrong macro release contract')
    require(receipt.get('scope') == 'us-nine-modules-five-macro-snapshots', 'macro release scope differs')
    require(receipt.get('publicationAuthorized') is True and receipt.get('pageQAComplete') is True, 'authorization or QA absent')
    require(receipt.get('snapshotSHA256') == SNAPSHOT_SHA, 'frozen snapshot binding differs')
    require(set(receipt['dataPins']) == DATA_FILES, 'five-file data scope differs')
    require(set(receipt['infrastructurePins']) <= INFRASTRUCTURE, 'infrastructure cannot authorize research changes')
    require(set(receipt['implementationPins']) == IMPLEMENTATION, 'implementation coverage differs')
    for name, expected in {**receipt['dataPins'], **receipt['implementationPins'], **receipt['infrastructurePins']}.items():
        require(sha((root / name).read_bytes()) == expected, 'current approved file changed: ' + name)
    with baseline_root(root) as previous:
        old = json.loads((previous / BASE_RECEIPT).read_bytes())
        old_pins = {**old['publicFilePins'], BASE_RECEIPT: sha((previous / BASE_RECEIPT).read_bytes())}
        for name, expected in old_pins.items():
            if name not in DATA_FILES and name not in receipt['infrastructurePins']:
                require(sha((root / name).read_bytes()) == expected, 'immutable research/source changed: ' + name)
        result = verify_previous(old, root=previous)
    for name in DATA_FILES:
        doc = json.loads((root / name).read_bytes())
        require(doc['generatedAt'] == receipt['vintages'][name], 'vintage binding differs')
    output = {'status': 'PASS_VALIDATED_MACRO_REFRESH_01', 'macroFiles': len(DATA_FILES),
              'legacyGateReplayed': True, 'previousGate': result}
    if dist is not None:
        output['distFilesScanned'] = verify_assets(dist, receipt, root)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path)
    parser.add_argument('--legacy-tests', action='store_true')
    args = parser.parse_args()
    result = verify(json.loads((ROOT / RECEIPT).read_bytes()), dist=args.dist)
    if args.legacy_tests:
        result['legacyTests'] = run_legacy_tests()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
