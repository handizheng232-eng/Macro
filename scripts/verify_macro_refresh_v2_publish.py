"""Authorize one verified five-JSON vintage without expanding frozen research approval."""
import argparse
import json
from pathlib import Path
import re
from macro_refresh_v2_snapshot import ROOT, SNAPSHOT, SNAPSHOT_SHA, sha, snapshot_files, previous_root, run_history
from pce_publication_snapshot import safe
from macro_refresh_v2_quality import validate_documents
from verify_editorial_openings_publish import verify as verify_editorial
from verify_rate_liftoff_publish import verify_assets
from verify_renewed_easing_publish import require

RECEIPT = 'release/macro-refresh-publication-02.json'
PREVIOUS_RECEIPT = 'release/editorial-openings-publication-01.json'
DATA_FILES = {f'src/data/us{name}Data.json' for name in ('Gdp', 'Employment', 'Inflation', 'Consumption', 'LateModules')}
INFRASTRUCTURE = {'scripts/run_data_tests.py', '.github/workflows/deploy.yml',
                  'src/historyReplayRouting.test.tsx', 'src/historyReplayRenewedRouting.test.tsx'}
IMPLEMENTATION = {SNAPSHOT, 'scripts/macro_refresh_v2_snapshot.py', 'scripts/test_macro_refresh_v2_snapshot.py',
                  'scripts/verify_macro_refresh_v2_publish.py', 'scripts/test_verify_macro_refresh_v2_publish.py',
                  'scripts/macro_refresh_v2_quality.py', 'docs/macro-refresh-publication-v2.md',
                  '.github/workflows/verify-macro-candidate.yml'}
EVIDENCE_KEYS = {'sourceAudit', 'frontend', 'data', 'browser'}
SCOPE = 'us-nine-modules-five-macro-snapshots-v2'


def make_receipt(root=ROOT, *, publication_authorized=False, qa_complete=False, evidence_hashes=None):
    dist = root / 'dist'
    return {'schemaVersion': 'macro-refresh-publication-02', 'scope': SCOPE,
            'publicationAuthorized': publication_authorized, 'pageQAComplete': qa_complete,
            'historicalResearchAuthorizationExpanded': False, 'snapshotSHA256': SNAPSHOT_SHA,
            'dataPins': {n: sha((root / n).read_bytes()) for n in sorted(DATA_FILES)},
            'infrastructurePins': {n: sha((root / n).read_bytes()) for n in sorted(INFRASTRUCTURE)},
            'implementationPins': {n: sha((root / n).read_bytes()) for n in sorted(IMPLEMENTATION)},
            'vintages': {n: json.loads((root / n).read_bytes())['generatedAt'] for n in sorted(DATA_FILES)},
            'qualityEvidenceHashes': evidence_hashes or {},
            'distPins': {p.relative_to(dist).as_posix(): sha(p.read_bytes().replace(b'\r\n', b'\n') if p.name == 'index.html' else p.read_bytes())
                         for p in sorted(dist.rglob('*')) if p.is_file()}}


def verify(receipt, root=ROOT, dist=None):
    require(receipt.get('schemaVersion') == 'macro-refresh-publication-02' and receipt.get('scope') == SCOPE, 'refresh scope differs')
    require(receipt.get('publicationAuthorized') is True and receipt.get('pageQAComplete') is True, 'authorization or QA absent')
    require(receipt.get('historicalResearchAuthorizationExpanded') is False, 'research authorization cannot expand')
    require(receipt.get('snapshotSHA256') == SNAPSHOT_SHA, 'snapshot binding differs')
    for key, expected in [('dataPins', DATA_FILES), ('vintages', DATA_FILES), ('infrastructurePins', INFRASTRUCTURE), ('implementationPins', IMPLEMENTATION), ('qualityEvidenceHashes', EVIDENCE_KEYS)]:
        require(set(receipt.get(key, {})) == expected, key + ' coverage differs')
    require(all(isinstance(v, str) and re.fullmatch('[0-9a-f]{64}', v) for v in receipt['qualityEvidenceHashes'].values()), 'quality evidence hashes invalid')
    base = snapshot_files(root)
    old_workflow = (
        b"          python -B -m unittest discover -s scripts -p 'test_verify_editorial_openings_publish.py' -v\n"
        b"          python -B scripts/verify_editorial_openings_publish.py --legacy-tests --dist dist\n")
    new_workflow = (
        b"          python -B -m unittest discover -s scripts -p 'test_macro_refresh_v2_snapshot.py' -v\n"
        b"          python -B -m unittest discover -s scripts -p 'test_verify_macro_refresh_v2_publish.py' -v\n"
        b"          python -B scripts/verify_macro_refresh_v2_publish.py --legacy-tests --dist dist\n")
    workflow = '.github/workflows/deploy.yml'
    require(base[workflow].count(old_workflow) == 1 and (root / workflow).read_bytes() == base[workflow].replace(old_workflow, new_workflow), 'workflow exceeds the reviewed gate-only replacement')
    quality = validate_documents({n: json.loads((root / n).read_bytes()) for n in DATA_FILES},
                                 {n: json.loads(base[n]) for n in DATA_FILES})
    for name, raw in base.items():
        if name not in DATA_FILES | INFRASTRUCTURE:
            require((root / safe(name)).read_bytes() == raw, 'immutable research/source changed: ' + name)
    for key in ('dataPins', 'infrastructurePins', 'implementationPins'):
        for name, expected in receipt[key].items():
            require(sha((root / safe(name)).read_bytes()) == expected, 'approved file changed: ' + name)
    for name in DATA_FILES:
        require(json.loads((root / name).read_bytes())['generatedAt'] == receipt['vintages'][name], 'vintage binding differs')
    with previous_root(root) as previous:
        old = verify_editorial(json.loads((previous / PREVIOUS_RECEIPT).read_bytes()), root=previous)
    result = {'status': 'PASS_VALIDATED_MACRO_REFRESH_02', 'macroFiles': len(DATA_FILES),
              'legacyGateReplayed': True, 'previousGate': old, 'historicalResearchAuthorizationExpanded': False,
              'privateOriginalReadbackPerformed': False, 'currentDataQuality': quality}
    if dist is not None:
        result['distFilesScanned'] = verify_assets(dist, receipt, root)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path)
    parser.add_argument('--legacy-tests', action='store_true')
    args = parser.parse_args()
    result = verify(json.loads((ROOT / RECEIPT).read_bytes()), dist=args.dist)
    if args.legacy_tests:
        result['inheritedTests'] = run_history()
    print(json.dumps(result, ensure_ascii=False))
