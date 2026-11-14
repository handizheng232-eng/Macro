"""Explicit CPI source correction, then rolling five-JSON admission against its fixed reference."""
import argparse
import copy
import gzip
import importlib.util
import io
import json
from pathlib import Path
import re
from cpi_correction_snapshot import ROOT, SNAPSHOT, SNAPSHOT_SHA, BASE_COMMIT, sha, snapshot_files, replay_previous_gate, run_history
from verify_rate_liftoff_publish import verify_assets
from pce_publication_snapshot import safe
from verify_renewed_easing_publish import require
from macro_refresh_v2_quality import validate_documents
from cpi_seasonality import CONTRACT, NSA_EXCEPTIONS, source_metadata

DATA_FILES = {f'src/data/us{name}Data.json' for name in ('Gdp', 'Employment', 'Inflation', 'Consumption', 'LateModules')}

RECEIPT = 'release/cpi-correction-publication-01.json'
SCOPE = 'cpi-sa-correction-and-five-macro-snapshots-v1'
EVIDENCE_KEYS = {'sourceAudit', 'frontend', 'data', 'browser'}
INFRASTRUCTURE = {'scripts/run_data_tests.py', '.github/workflows/deploy.yml', '.github/workflows/verify-macro-candidate.yml'}
IMPLEMENTATION = {SNAPSHOT, 'scripts/cpi_correction_snapshot.py', 'scripts/test_cpi_correction_snapshot.py',
                  'scripts/verify_cpi_correction_publish.py', 'scripts/test_verify_cpi_correction_publish.py',
                  'docs/cpi-correction-publication-v1.md'}
INFLATION = 'src/data/usInflationData.json'
AUTHORIZATION = 'release/cpi-seasonality-authorization-01.json'
CORRECTED_REFERENCE = 'release/snapshots/cpi-seasonality-corrected-inflation-01.json.gz'
# Exact reviewed source approval; never rebound for ordinary future data refreshes.
AUTHORIZATION_SHA256 = 'a5742e1a83f00982431249095af67de6204e2a5e0c19a43b7d7d801f7cc68f2b'
REQUIRED_SOURCE_FILES = {'scripts/refresh_ifind_us_inflation.py', 'src/usInflation.tsx', 'scripts/cpi_seasonality.py',
                         'scripts/fixtures/cpi_sa_contract.json'}
REVIEWED_SOURCE_FILES = REQUIRED_SOURCE_FILES | {
    'scripts/test_cpi_seasonality.py', 'scripts/test_refresh_ifind_us_inflation.py',
    'scripts/test_heatmap_history.py', 'scripts/test_pce_distribution.py', 'src/cpiSeasonality.test.tsx', 'scripts/fixtures/cpi_sa_bls_2026.json'}
CPI_BRANCHES = {'cpiHeatmap', 'cpiDetail', 'cpiTrend', 'goodsServices', 'shelterLag', 'underlying',
                'cpiPceGap', 'januaryEffect', 'cpiPceWeights', 'specialComponents', 'coreSplit',
                'cpiContributions', 'supercoreMom', 'cycleStructure', 'cpiSeasonality', 'releaseStatus'}


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def at(document, path):
    value = document
    for key in path:
        value = value[key]
    return value


def source_files_checked(names):
    names = list(names)
    require(len(names) == len(set(names)) and REQUIRED_SOURCE_FILES <= set(names) <= REVIEWED_SOURCE_FILES,
            'Source files exceed the reviewed named correction allowlist')
    return sorted(names)


def check_correction_boundary(document, baseline, paths):
    """One-time diff allowance only; all undeclared/non-CPI objects remain byte-semantic equal."""
    current, old = copy.deepcopy(document), copy.deepcopy(baseline)
    require(paths and len({tuple(p) for p in paths}) == len(paths), 'Correction paths absent or duplicated')
    for path in paths:
        require(isinstance(path, list) and path and all(type(k) in (str, int) for k in path), 'Invalid correction path')
        allowed = path[0] in {'generatedAt', 'dataQuality', 'rawSnapshots'} or (
            len(path) >= 2 and path[0] == 'actual' and path[1] in CPI_BRANCHES)
        require(allowed, 'Non-CPI correction path is not authorized')
        for target in (current, old):
            try:
                parent = at(target, path[:-1])
                if isinstance(parent, dict):
                    parent.pop(path[-1], None)
                else:
                    parent[path[-1]] = None
            except (KeyError, IndexError, TypeError):
                raise ValueError('Correction path parent differs') from None
    require(current == old, 'Unapproved non-CPI inflation content changed')


def source_identity(source, role):
    require(isinstance(source, dict), 'CPI source metadata absent')
    key = {'headline:cpi': 'cpi_mom', 'headline:core': 'core_cpi_mom'}.get(role)
    if key is None and role.startswith('row:'):
        key = role[4:].removesuffix('_yoy') + '_mom'
    require(key in CONTRACT, 'Unregistered CPI source role')
    expected = source_metadata(key)
    name, code = source.get('name'), source.get('code')
    require(isinstance(code, str) and re.fullmatch(r'[GLMS]\d{9}', code) is not None, 'Invalid CPI source code')
    require(code not in {'G002600387', 'G002600388'}, 'Ordinary CPI mom cannot be authorized as SA')
    if key in NSA_EXCEPTIONS:
        require(all(source.get(k) == v for k, v in expected.items()), 'Registered NSA role/code/original-name/basis identity differs')
    else:
        require(source.get('seasonalAdjustment') == 'SA', 'Explicit SA source metadata required')
        require(isinstance(name, str) and ('季调' in name or 'seasonally adjusted' in name.lower())
                and not any(word in name.lower() for word in ('非季调', '未季调', 'not seasonally', 'unadjusted')), 'Original metadata does not explicitly establish SA')
        require(all(source.get(k) == v for k, v in expected.items()), 'Strict SA role/code/original-name identity differs')
    fields = {'code', 'name', 'seasonalAdjustment', 'provider', 'institution', 'unit', 'rawUnit', 'frequency', 'adjustmentBasis', 'entityAlias', 'blsSeries'}
    identity = {k: v for k, v in source.items() if k in fields}
    require(identity == expected, 'CPI classification identity contains unregistered fields')
    return identity


def bind_sources(document, bindings):
    table = document['actual']['cpiHeatmap']
    rows, historical = table['rows'], table['history']['rows']
    require(len(rows) == len(historical) == 23 and [r['id'] for r in rows] == [r['id'] for r in historical], 'All 23 CPI rows require source review')
    expected = {'row:' + r['id'] for r in rows} | {'headline:cpi', 'headline:core'}
    require(len(bindings) == len(expected) and {b['role'] for b in bindings} == expected, 'SA binding role coverage differs')
    bound = []
    for binding in bindings:
        role, paths = binding['role'], binding['paths']
        require(paths and len({tuple(p) for p in paths}) == len(paths), 'SA metadata paths duplicated or absent')
        if role.startswith('row:'):
            index = [r['id'] for r in rows].index(role[4:])
            prefixes = [['actual', 'cpiHeatmap', 'rows', index], ['actual', 'cpiHeatmap', 'history', 'rows', index]]
            require(len(paths) == 2 and all(any(p[:len(prefix)] == prefix and len(p) > len(prefix) for p in paths) for prefix in prefixes), 'SA metadata must belong to each recent/history row')
        identities = [source_identity(at(document, path), role) for path in paths]
        require(all(value == identities[0] for value in identities), 'Recent/history SA source identities differ')
        if role in {'headline:cpi', 'headline:core'}:
            require(identities[0]['code'] == {'headline:cpi': 'G005464034', 'headline:core': 'G005464040'}[role], 'Headline CPI/core SA code differs')
        bound.append({'role': role, 'paths': paths, 'identity': identities[0]})
    rows_bound = [b for b in bound if b['role'].startswith('row:')]
    require(sum(b['identity']['seasonalAdjustment'] == 'SA' for b in rows_bound) == 21
            and sum(b['identity']['seasonalAdjustment'] == 'NSA' for b in rows_bound) == 2, 'CPI 21 SA / 2 NSA row classification differs')
    return sorted(bound, key=lambda b: b['role'])


def make_authorization(root=ROOT, *, source_files, sa_bindings, inflation_change_paths,
                       source_audit_sha256, correction_authorized=False, source_review_complete=False):
    """Return approval + gzip bytes; does not write or approve anything by default."""
    names = source_files_checked(source_files)
    require(isinstance(source_audit_sha256, str) and re.fullmatch(r'[0-9a-f]{64}', source_audit_sha256) is not None, 'Source audit hash invalid')
    document = json.loads((root / INFLATION).read_bytes())
    check_correction_boundary(document, json.loads(snapshot_files(root)[INFLATION]), inflation_change_paths)
    bindings = bind_sources(document, sa_bindings)
    stream = io.BytesIO()
    with gzip.GzipFile(filename='', fileobj=stream, mode='wb', compresslevel=9, mtime=0) as archive:
        archive.write(canonical(document))
    raw = stream.getvalue()
    return {'schemaVersion': 'cpi-seasonality-authorization-01', 'baselineCommit': BASE_COMMIT,
            'snapshotSHA256': SNAPSHOT_SHA, 'correctionAuthorized': correction_authorized,
            'sourceReviewComplete': source_review_complete, 'historicalResearchAuthorizationExpanded': False,
            'sourcePins': {n: sha((root / n).read_bytes()) for n in names},
            'inflationChangePaths': inflation_change_paths, 'saBindings': bindings,
            'sourceAuditSHA256': source_audit_sha256, 'correctedReferenceSHA256': sha(raw),
            'correctedDocumentSHA256': sha(canonical(document))}, raw


def load_authorization(root=ROOT):
    raw = (root / AUTHORIZATION).read_bytes()
    require(isinstance(AUTHORIZATION_SHA256, str) and sha(raw) == AUTHORIZATION_SHA256, 'Correction authorization binding absent or differs')
    approval = json.loads(raw)
    require(approval.get('correctionAuthorized') is True and approval.get('sourceReviewComplete') is True, 'Correction authorization/source review incomplete')
    require(approval.get('schemaVersion') == 'cpi-seasonality-authorization-01'
            and approval.get('baselineCommit') == BASE_COMMIT and approval.get('snapshotSHA256') == SNAPSHOT_SHA,
            'Correction approval baseline/schema differs')
    require(approval.get('historicalResearchAuthorizationExpanded') is False, 'Research authorization cannot expand')
    require(isinstance(approval.get('sourceAuditSHA256'), str) and re.fullmatch(r'[0-9a-f]{64}', approval['sourceAuditSHA256']) is not None, 'Source audit hash invalid')
    for name in source_files_checked(approval['sourcePins']):
        require(sha((root / safe(name)).read_bytes()) == approval['sourcePins'][name], 'Reviewed source changed: ' + name)
    reference_raw = (root / CORRECTED_REFERENCE).read_bytes()
    require(sha(reference_raw) == approval.get('correctedReferenceSHA256'), 'Immutable corrected reference changed')
    document = json.loads(gzip.decompress(reference_raw))
    require(sha(canonical(document)) == approval.get('correctedDocumentSHA256'), 'Corrected document binding differs')
    check_correction_boundary(document, json.loads(snapshot_files(root)[INFLATION]), approval['inflationChangePaths'])
    require(bind_sources(document, approval['saBindings']) == approval['saBindings'], 'Reviewed SA metadata binding differs')
    return approval, document


def semantic_guard(document, root=ROOT):
    """Load the pinned current checker, never a historical data/UI substitute."""
    spec = importlib.util.spec_from_file_location('_approved_cpi_semantics', root / 'scripts/cpi_seasonality.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(callable(getattr(module, 'validate_dataset', None)), 'Current CPI validate_dataset checker is required')
    result = module.validate_dataset(document)
    require(result is not False, 'Current CPI semantic guard rejected dataset')
    return result


def check_public_scope(root, base, source_files):
    allowed = set(base) | set(source_files) | IMPLEMENTATION | INFRASTRUCTURE | {AUTHORIZATION, CORRECTED_REFERENCE, RECEIPT}
    for directory in ('src', 'scripts', 'docs', 'public', 'release', '.github'):
        for path in (root / directory).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            name = path.relative_to(root).as_posix()
            require(path.resolve().is_relative_to(root.resolve()) and name in allowed, 'Unapproved public file: ' + name)


def validate_current(documents, baseline, approval, root=ROOT):
    require(set(documents) == set(baseline) == DATA_FILES, 'Five-document coverage differs')
    require(bind_sources(documents[INFLATION], approval['saBindings']) == approval['saBindings'], 'Current SA source metadata differs from reviewed correction')
    # v2's identity, non-null history, gap, GDP, employment and PCE checks are
    # unchanged. Only the explicitly approved inflation reference is replaced.
    semantic_guard(documents[INFLATION], root)
    result = validate_documents(documents, baseline)
    bound = bind_sources(documents[INFLATION], approval['saBindings'])
    rows = [b for b in bound if b['role'].startswith('row:')]
    result['totalRows'] = len(rows)
    result['saRows'] = sum(b['identity']['seasonalAdjustment'] == 'SA' for b in rows)
    result['nsaRows'] = sum(b['identity']['seasonalAdjustment'] == 'NSA' for b in rows)
    independent = {b['identity']['code']: b['identity']['seasonalAdjustment'] for b in bound}
    result['independentMomSources'] = {'total': len(independent), **{a: sum(v == a for v in independent.values()) for a in ('SA', 'NSA')}}
    return result


def make_receipt(root=ROOT, *, publication_authorized=False, qa_complete=False, evidence_hashes=None):
    """A fresh per-run receipt; never rewrites the one-time source authorization."""
    dist = root / 'dist'
    return {'schemaVersion': 'cpi-correction-publication-01', 'scope': SCOPE,
            'publicationAuthorized': publication_authorized, 'pageQAComplete': qa_complete,
            'historicalResearchAuthorizationExpanded': False, 'snapshotSHA256': SNAPSHOT_SHA,
            **{key: {n: sha((root / n).read_bytes()) for n in sorted(names)} for key, names in (
                ('dataPins', DATA_FILES), ('infrastructurePins', INFRASTRUCTURE),
                ('implementationPins', IMPLEMENTATION), ('approvalPins', {AUTHORIZATION, CORRECTED_REFERENCE}))},
            'vintages': {n: json.loads((root / n).read_bytes())['generatedAt'] for n in sorted(DATA_FILES)},
            'qualityEvidenceHashes': evidence_hashes or {},
            'distPins': {p.relative_to(dist).as_posix(): sha(p.read_bytes().replace(b'\r\n', b'\n') if p.name == 'index.html' else p.read_bytes())
                         for p in sorted(dist.rglob('*')) if p.is_file()}}


def check_infrastructure(root, base):
    old_unit = b"          python -B -m unittest discover -s scripts -p 'test_verify_macro_refresh_v2_publish.py' -v\n"
    new_unit = (b"          python -S -B -m unittest discover -s scripts -p 'test_cpi_correction_snapshot.py' -v\n"
                b"          python -S -B -m unittest discover -s scripts -p 'test_verify_cpi_correction_publish.py' -v\n")
    for name in ('.github/workflows/deploy.yml', '.github/workflows/verify-macro-candidate.yml'):
        require(base[name].count(old_unit) == 1, 'Original workflow gate coverage differs')
        expected = base[name].replace(old_unit, new_unit)
        if name.endswith('/deploy.yml'):
            old_gate = b'python -B scripts/verify_macro_refresh_v2_publish.py --legacy-tests --dist dist'
            require(expected.count(old_gate) == 1, 'Original workflow actual gate differs')
            expected = expected.replace(old_gate, b'python -B scripts/verify_cpi_correction_publish.py --legacy-tests --dist dist')
        require((root / name).read_bytes() == expected, 'workflow exceeds reviewed gate-only replacement')
    runner = 'scripts/run_data_tests.py'
    before = b'from macro_refresh_v2_snapshot import split_history, run_history'
    after = b'from cpi_correction_snapshot import split_history, run_history'
    require(base[runner].count(before) == 1 and (root / runner).read_bytes() == base[runner].replace(before, after), 'runner exceeds reviewed historical-partition replacement')


def verify(receipt, root=ROOT, dist=None):
    require(receipt.get('schemaVersion') == 'cpi-correction-publication-01' and receipt.get('scope') == SCOPE, 'Correction publication scope differs')
    require(receipt.get('publicationAuthorized') is True and receipt.get('pageQAComplete') is True, 'Publication authorization or QA absent')
    require(receipt.get('historicalResearchAuthorizationExpanded') is False, 'Research authorization cannot expand')
    require(receipt.get('snapshotSHA256') == SNAPSHOT_SHA, 'Baseline48 binding differs')
    for key, expected in (('dataPins', DATA_FILES), ('vintages', DATA_FILES), ('infrastructurePins', INFRASTRUCTURE),
                          ('implementationPins', IMPLEMENTATION), ('approvalPins', {AUTHORIZATION, CORRECTED_REFERENCE}),
                          ('qualityEvidenceHashes', EVIDENCE_KEYS)):
        require(set(receipt.get(key, {})) == expected, key + ' coverage differs')
    require(all(isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v) for v in receipt['qualityEvidenceHashes'].values()), 'Quality evidence hashes invalid')
    base = snapshot_files(root)
    check_infrastructure(root, base)
    approval, corrected = load_authorization(root)
    check_public_scope(root, base, approval['sourcePins'])
    for name, raw in base.items():
        if name not in DATA_FILES | INFRASTRUCTURE | set(approval['sourcePins']):
            require((root / safe(name)).read_bytes() == raw, 'immutable research/source changed: ' + name)
    for key in ('dataPins', 'infrastructurePins', 'implementationPins', 'approvalPins'):
        for name, expected in receipt[key].items():
            require(sha((root / safe(name)).read_bytes()) == expected, 'Approved file changed: ' + name)
    documents = {n: json.loads((root / n).read_bytes()) for n in DATA_FILES}
    for name, document in documents.items():
        require(document['generatedAt'] == receipt['vintages'][name], 'Vintage binding differs')
    baseline = {n: json.loads(base[n]) for n in DATA_FILES}; baseline[INFLATION] = corrected
    quality = validate_current(documents, baseline, approval, root)
    old = replay_previous_gate(root)
    result = {'status': 'PASS_AUTHORIZED_CPI_CORRECTION_01', 'macroFiles': len(DATA_FILES),
              'legacyGateReplayed': True, 'previousGate': old, 'currentDataQuality': quality,
              'historicalResearchAuthorizationExpanded': False, 'privateOriginalReadbackPerformed': False}
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
