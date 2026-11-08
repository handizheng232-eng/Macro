"""Promote only user-approved opening text; replay every preceding release gate."""
import argparse
from collections import Counter
from contextlib import contextmanager
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile
from pce_publication_snapshot import safe
from verify_pce_distribution_publish import verify as verify_previous
from verify_rate_liftoff_publish import verify_assets
from verify_renewed_easing_publish import require

ROOT = Path(__file__).resolve().parents[1]
AUTH = 'release/editorial-openings-authorization-01.json'
AUTH_SHA = '679dfeb456b0623c5dc87e67dea41f3ca4f544a2e86d9f3864703251f6ca7069'
SNAPSHOT = 'release/snapshots/editorial-baseline-2e4d735.zip'
INVERSE = 'release/editorial-openings-inverse-01.json'
RECEIPT = 'release/editorial-openings-publication-01.json'
PREVIOUS = 'release/pce-distribution-publication-01.json'
MATRIX = 'src/test/replayEditorialOpenings.json'
DATA = {'A': 'src/data/historyReplayTaper.json', 'B': 'src/data/historyReplayRateLiftoffQtGuidance.json'}
SCOPE = 'two-approved-replay-openings-and-project-writing-reading-templates'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def authorization(root=ROOT):
    raw = (root / AUTH).read_bytes()
    require(sha(raw) == AUTH_SHA, 'editorial authorization anchor differs')
    auth = json.loads(raw)
    require(auth['publicationAuthorized'] is True and auth['scope'] == SCOPE, 'authorization absent')
    require(auth['fullStageReady'] is False and auth['researchAuthorizationExpanded'] is False, 'research authorization expanded')
    return auth

def snapshot_files(root=ROOT):
    auth = authorization(root)
    raw = (root / SNAPSHOT).read_bytes()
    require(sha(raw) == auth['snapshotSHA256'], 'preceding snapshot changed')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'duplicate archive members')
        files = {safe(n).as_posix(): archive.read(n) for n in names}
    require({n: sha(b) for n, b in files.items()} == auth['baselinePins'], 'baseline member scope differs')
    return files

def resolve(data, pointer):
    for key in pointer[1:].split('/'):
        data = data[int(key)] if isinstance(data, list) else data[key]
    return data

def put(data, pointer, value):
    keys = pointer[1:].split('/')
    for key in keys[:-1]:
        data = data[int(key)] if isinstance(data, list) else data[key]
    key = int(keys[-1]) if isinstance(data, list) else keys[-1]
    data[key] = value

def inverse_contract(root=ROOT):
    raw = (root / INVERSE).read_bytes()
    require(sha(raw) == authorization(root)['inverseSHA256'], 'inverse anchor differs')
    inv = json.loads(raw)
    require(set(inv) == set(DATA.values()), 'inverse file scope differs')
    return inv

def check_semantics(current, baseline, changes, rows):
    restored = copy.deepcopy(current)
    for change in changes:
        require(resolve(restored, change['pointer']) == change['after'], 'approved opening/reference differs: ' + change['pointer'])
        put(restored, change['pointer'], change['before'])
    require(restored == baseline, 'out-of-scope economics/date/eligibility/market change')
    for row in rows:
        require(resolve(current, row['pointer']) == resolve(current, row['mirrorPointer']) == row['after'], 'opening mirror differs')
        require(resolve(baseline, row['pointer']) == row['before'], 'opening baseline differs')
    require(current['localReview']['fullStageReady'] is False, 'research readiness upgraded')
    ids = {s['id'] for s in current['sources'] + current['reports']}
    for section in current['marketAnalysis']['sections']:
        require(all(ref['sourceId'] in ids for ref in section['periodSummary']['paragraphSources'][0]), 'summary source missing')
        for aspect in section['aspectSummaries'].values():
            require(set(aspect['sourceIds']) <= ids, 'aspect source missing')

def restore(name, root=ROOT):
    contract = inverse_contract(root)[name]
    raw = (root / name).read_bytes()
    require(sha(raw) == contract['currentSHA256'], 'inverse input differs')
    lines = raw.decode('utf-8').splitlines(keepends=True)
    end = 0
    for op in contract['operations']:
        require(0 <= end <= op['start'] <= op['end'] <= len(lines), 'inverse span differs')
        require(sha(''.join(lines[op['start']:op['end']]).encode()) == op['currentSHA256'], 'inverse block differs')
        end = op['end']
    for op in reversed(contract['operations']):
        lines[op['start']:op['end']] = [op['baselineText']]
    restored = ''.join(lines).encode('utf-8')
    require(sha(restored) == contract['baselineSHA256'] == authorization(root)['baselinePins'][name], 'exact baseline bytes differ')
    return restored

@contextmanager
def previous_root(root=ROOT):
    auth = authorization(root)
    base = snapshot_files(root)
    with tempfile.TemporaryDirectory(prefix='editorial-previous-public-') as folder:
        target = Path(folder)
        for name, baseline in base.items():
            actual = (root / safe(name)).read_bytes()
            if name in DATA.values():
                actual = restore(name, root)
            elif name in auth['allowedChanges']:
                actual = baseline
            require(actual == baseline, 'immutable previous file differs: ' + name)
            dest = target / safe(name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(actual)
        yield target

def make_receipt(root=ROOT):
    auth = authorization(root)
    names = set(auth['baselinePins']) | set(auth['additions'])
    dist = root / 'dist'
    return {'schemaVersion': 'editorial-openings-publication-01', 'scope': SCOPE,
            'publicationAuthorized': True, 'fullStageReady': False, 'authorizationSHA256': AUTH_SHA,
            'publicFilePins': {n: sha((root / safe(n)).read_bytes()) for n in sorted(names)},
            'distPins': {p.relative_to(dist).as_posix(): sha(p.read_bytes()) for p in sorted(dist.rglob('*')) if p.is_file()}}

def verify(receipt, root=ROOT, dist=None):
    auth = authorization(root)
    require(receipt.get('schemaVersion') == 'editorial-openings-publication-01' and receipt.get('scope') == SCOPE, 'editorial scope differs')
    require(receipt.get('publicationAuthorized') is True and receipt.get('fullStageReady') is False, 'authorization/readiness differs')
    require(receipt.get('authorizationSHA256') == AUTH_SHA, 'authorization receipt binding differs')
    base = snapshot_files(root)
    inv = inverse_contract(root)
    rows_raw = (root / MATRIX).read_bytes()
    require(sha(rows_raw) == auth['publicFixtureSHA256'], 'reviewed fifty-cell fixture differs')
    rows = json.loads(rows_raw)
    require(len(rows) == len({(r['page'], r['section'], r['role']) for r in rows}) == 50, 'editorial cell scope differs')
    for key, name in DATA.items():
        require([c['pointer'] for c in inv[name]['semanticChanges']] == auth['semanticPointers'][name], 'semantic authorization pointers differ')
        raw = (root / name).read_bytes()
        check_semantics(json.loads(raw), json.loads(base[name]), inv[name]['semanticChanges'], [r for r in rows if r['page'] == key])
        require(sha(raw) == auth['reviewedDataPins'][name], 'approved final text bytes differ')
    require(set(receipt['publicFilePins']) == set(base) | set(auth['additions']), 'public pin coverage differs')
    for name, expected in receipt['publicFilePins'].items():
        actual = (root / safe(name)).read_bytes()
        require(sha(actual) == expected, 'public pin differs: ' + name)
        if name in base and name not in auth['allowedChanges']:
            require(actual == base[name], 'immutable preceding file changed: ' + name)
    with previous_root(root) as previous:
        result = verify_previous(json.loads((previous / PREVIOUS).read_bytes()), root=previous)
    output = {'status': 'PASS_APPROVED_EDITORIAL_OPENINGS_01', 'editorialCells': len(rows),
              'legacyGateReplayed': True, 'previousGate': result, 'fullStageReady': False,
              'dataSHA256': auth['reviewedDataPins'], 'privateOriginalReadbackPerformed': False}
    if dist is not None:
        output['distFilesScanned'] = verify_assets(dist, receipt, root)
    return output

def run_previous_tests(root=ROOT):
    """Run each unchanged preceding suite once, in its own exact public version."""
    with previous_root(root) as previous:
        source = (root / 'node_modules').resolve()
        link = previous / 'node_modules'
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(source)], check=True, stdout=subprocess.DEVNULL)
        else:
            link.symlink_to(source, target_is_directory=True)
        try:
            discovery = "import unittest,json,sys;sys.path.insert(0,'scripts');from macro_publication_snapshot import flatten,HISTORICAL_MODULES; l=unittest.TestLoader();s=l.discover('scripts',pattern='test_verify*publish*.py');assert not l.errors,l.errors;modules=set(HISTORICAL_MODULES)|{'test_verify_macro_refresh_publish','test_verify_pce_distribution_publish'};ids=[c.id() for c in flatten(s) if c.__class__.__module__ in modules];assert not any('_FailedTest' in i for i in ids);print(json.dumps(ids))"
            discovered = subprocess.run([sys.executable, '-B', '-c', discovery], cwd=previous, capture_output=True, text=True, check=True)
            expected = json.loads(discovered.stdout)
            transcripts = []
            for command in [
                ['node', str(source / 'vite/bin/vite.js'), 'build'],
                [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_verify_pce_distribution_publish.py', '-v'],
                [sys.executable, '-B', 'scripts/verify_pce_distribution_publish.py', '--legacy-tests', '--dist', 'dist'],
            ]:
                run = subprocess.run(command, cwd=previous, capture_output=True, text=True, encoding='utf-8', errors='replace')
                text = run.stdout + '\n' + run.stderr
                print(text, flush=True)
                transcripts.append(text)
                require(run.returncode == 0, 'preceding exact fixture command failed: ' + repr(command))
        finally:
            if os.name == 'nt':
                os.rmdir(link)
            else:
                link.unlink()
    output = '\n'.join(transcripts)
    seen = [identity if identity.endswith('.' + method) else identity + '.' + method
            for method, identity in re.findall(r'^(test_\w+) \(([\w.]+)\)', output, re.MULTILINE)]
    require(Counter(seen) == Counter(expected) and len(seen) == len(set(seen)), 'discovered/executed inherited case-ID multisets differ')
    require(not re.search(r'\bskipped=|\.\.\. skipped|_FailedTest', output), 'inherited skip or discovery failure')
    return {'run': len(seen), 'ids': sorted(seen), 'discoveryErrors': [], 'skipped': 0}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path)
    parser.add_argument('--legacy-tests', action='store_true')
    args = parser.parse_args()
    result = verify(json.loads((ROOT / RECEIPT).read_bytes()), dist=args.dist)
    if args.legacy_tests:
        result['inheritedTests'] = run_previous_tests()
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
