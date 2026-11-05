"""Scoped PCE addition; frozen research and prior macro receipts stay unchanged."""
import argparse
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
from pce_distribution import build_distribution
from pce_publication_snapshot import (ROOT, SNAPSHOT, SNAPSHOT_SHA, PREVIOUS_RECEIPT,
                                      previous_root, snapshot_files, run_previous_tests)
from macro_publication_snapshot import run_legacy_tests
from verify_macro_refresh_publish import verify as verify_previous
from verify_rate_liftoff_publish import verify_assets
from verify_renewed_easing_publish import require

RECEIPT = 'release/pce-distribution-publication-01.json'
AUTH = 'release/pce-distribution-authorization-01.json'
AUTH_SHA = '0c9b432dd4e9f663df1ec21a7def1a2f967ef13a7724738ae9ba5f0c5b85af8e'
DATA = 'src/data/usInflationData.json'
FIXTURE = 'scripts/fixtures/pce_distribution_20261105.json'
SCOPE = 'us-inflation-pce-weighted-distribution-addition'
ALLOWED_CHANGES = frozenset({
    DATA, 'src/usInflation.tsx', 'src/styles.css',
    'scripts/refresh_ifind_us_inflation.py', 'scripts/test_refresh_ifind_us_inflation.py',
    'scripts/run_data_tests.py', '.github/workflows/deploy.yml', '.gitattributes',
    'src/App.test.tsx', 'src/historyReplay.test.tsx', 'src/historyReplay.testHelpers.tsx',
    'src/historyReplayTestHelpers.test.tsx', 'src/historyReplayRouting.test.tsx',
    'src/historyReplayRenewedRouting.test.tsx',
})
ADDITIONS = frozenset({
    AUTH, SNAPSHOT, FIXTURE, 'scripts/pce_distribution.py', 'scripts/test_pce_distribution.py',
    'scripts/pce_publication_snapshot.py', 'scripts/test_pce_publication_snapshot.py',
    'scripts/verify_pce_distribution_publish.py', 'scripts/test_verify_pce_distribution_publish.py',
    'src/pceDistribution.tsx', 'src/pceDistribution.test.tsx', 'src/pceDistributionIntegration.test.tsx',
    'docs/pce-price-distribution.md',
})


def sha(data):
    return hashlib.sha256(data).hexdigest()


def semantic_sha(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def authorization(root):
    raw = (root / AUTH).read_bytes()
    require(sha(raw) == AUTH_SHA, 'PCE authorization anchor differs')
    auth = json.loads(raw)
    require(auth['publicationAuthorized'] is True and auth['scope'] == SCOPE,
            'PCE authorization scope absent')
    require(auth['historicalResearchAuthorizationExpanded'] is False
            and auth['otherMacroDataRefreshAuthorized'] is False, 'authorization expanded')
    require(sha((root / FIXTURE).read_bytes()) == auth['sourceFixtureSHA256'], 'official source fixture differs')
    return auth


def check_semantics(current, previous, root=ROOT):
    """Independently replay public official source bytes, not a private API claim."""
    candidate = copy.deepcopy(current)
    distribution = candidate['actual'].pop('pceDistribution')
    require(candidate['source'] == 'iFinD EDB；PCE分项涨幅分布来自Dallas Fed官方', 'mixed provider label differs')
    require(candidate['sourceProviders'] == ['iFinD EDB', 'Federal Reserve Bank of Dallas'], 'providers differ')
    for field in ('source', 'sourceProviders'):
        candidate[field] = previous[field]
    require(candidate == previous, 'existing iFinD observations, metadata or vintage changed')
    expected = build_distribution(json.loads((root / FIXTURE).read_bytes()))
    require(set(distribution) == set(expected), 'distribution schema differs')
    for field in expected:
        if field != 'source':
            require(distribution[field] == expected[field], 'official distribution mismatch: ' + field)
    source, reference = distribution['source'], expected['source']
    require(set(source) == set(reference), 'source metadata schema differs')
    for field in reference:
        if field not in ('fetchedAt', 'resources'):
            require(source[field] == reference[field], 'source metadata differs: ' + field)
    require(set(source['resources']) == set(reference['resources']), 'source resource scope differs')
    times = []
    for key, resource in source['resources'].items():
        require(set(resource) == {'url', 'sha256', 'fetchedAt'}, 'resource schema differs')
        for field in ('url', 'sha256'):
            require(resource[field] == reference['resources'][key][field], 'source-byte identity differs')
        time = datetime.fromisoformat(resource['fetchedAt'])
        require(time.tzinfo is not None, 'source timestamp has no timezone')
        times.append(time)
    require((max(times) - min(times)).total_seconds() <= 3600, 'mixed capture batches')
    require(datetime.fromisoformat(source['fetchedAt']) == max(times), 'aggregate capture time differs')
    require(source['latestObservation'] <= max(times).strftime('%Y%m'), 'future observation')
    return distribution


def make_receipt(root=ROOT, *, authorized=False, qa_complete=False):
    base = snapshot_files(root)
    auth = authorization(root)
    changed = {name: sha((root / name).read_bytes()) for name, raw in base.items()
               if (root / name).read_bytes() != raw}
    require(set(changed) <= ALLOWED_CHANGES, 'outside PCE release scope: ' + repr(sorted(set(changed) - ALLOWED_CHANGES)))
    data = json.loads((root / DATA).read_bytes())
    require(semantic_sha(data) == auth['reviewedDatasetSemanticSHA256'], 'reviewed data changed')
    check_semantics(data, json.loads(base[DATA]), root)
    dist = root / 'dist'
    return {
        'schemaVersion': 'pce-distribution-publication-01', 'scope': SCOPE,
        'publicationAuthorized': authorized, 'pageQAComplete': qa_complete,
        'authorizationSHA256': AUTH_SHA, 'snapshotSHA256': SNAPSHOT_SHA,
        'baselineReceiptSHA256': sha(base[PREVIOUS_RECEIPT]),
        'changedPins': changed,
        'publicFilePins': {n: sha((root / n).read_bytes()) for n in sorted(set(base) | ADDITIONS)},
        'distPins': {p.relative_to(dist).as_posix(): sha(p.read_bytes().replace(b'\r\n', b'\n') if p.name == 'index.html' else p.read_bytes())
                     for p in sorted(dist.rglob('*')) if p.is_file()},
        'ifindGeneratedAt': data['generatedAt'],
        'distributionFetchedAt': data['actual']['pceDistribution']['source']['fetchedAt'],
    }


def verify(receipt, root=ROOT, dist=None):
    require(receipt.get('schemaVersion') == 'pce-distribution-publication-01' and receipt.get('scope') == SCOPE,
            'incorrect PCE release contract')
    require(receipt.get('publicationAuthorized') is True and receipt.get('pageQAComplete') is True,
            'PCE authorization or QA absent')
    require(receipt.get('authorizationSHA256') == AUTH_SHA and receipt.get('snapshotSHA256') == SNAPSHOT_SHA,
            'authorization/snapshot binding differs')
    auth = authorization(root)
    base = snapshot_files(root)
    require(receipt.get('baselineReceiptSHA256') == sha(base[PREVIOUS_RECEIPT]), 'previous receipt binding differs')
    require(set(receipt['publicFilePins']) == set(base) | ADDITIONS, 'public file scope differs')
    require(set(receipt['changedPins']) <= ALLOWED_CHANGES, 'unauthorized change scope')
    actual_changes = set()
    for name, expected in receipt['publicFilePins'].items():
        raw = (root / name).read_bytes()
        require(sha(raw) == expected, 'approved public file changed: ' + name)
        if name in base and raw != base[name]:
            actual_changes.add(name)
            require(name in ALLOWED_CHANGES and receipt['changedPins'].get(name) == expected,
                    'immutable previous research/source changed: ' + name)
    require(actual_changes == set(receipt['changedPins']), 'declared change list differs')
    data = json.loads((root / DATA).read_bytes())
    require(semantic_sha(data) == auth['reviewedDatasetSemanticSHA256'], 'reviewed data changed')
    distribution = check_semantics(data, json.loads(base[DATA]), root)
    require(receipt['ifindGeneratedAt'] == data['generatedAt'] and
            receipt['distributionFetchedAt'] == distribution['source']['fetchedAt'], 'vintage binding differs')
    with previous_root(root) as previous:
        old = json.loads((previous / PREVIOUS_RECEIPT).read_bytes())
        result = verify_previous(old, root=previous)
    output = {'status': 'PASS_PCE_DISTRIBUTION_PUBLICATION_01', 'legacyGateReplayed': True,
              'previousGate': result, 'distributionMonths': len(distribution['periods']),
              'latestComponentCount': distribution['quality']['latestComponentCount']}
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
        result['previousMacroTests'] = run_previous_tests()
        result['originalResearchTests'] = run_legacy_tests()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
