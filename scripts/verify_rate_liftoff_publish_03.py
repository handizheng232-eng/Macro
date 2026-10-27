"""Label-only successor; restore exact Publication02 before replaying its full gate."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from verify_rate_liftoff_publish_02 import verify as previous_verify, RECEIPT as PREVIOUS
from verify_rate_liftoff_publish import verify_assets, sha, safe, require
ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'release/rate-liftoff-publication-03.json'
AUTH = 'release/rate-liftoff-authorization-03.json'
INVERSE = 'release/rate-liftoff-inverse-03.json'
AUTH_SHA = 'd6ec02d80c9057217444c2f32ead0aac4b64fdb53d354478fb8bf2773c9e0d20'
DATA = 'src/data/historyReplayRateLiftoffQtGuidance.json'
DATA_SHA = '998af1c27a1baa032d25137c4e6d3b0d3f115d22dbed8e63ec7651a879c27abb'

def authorization(root):
    raw = (root / AUTH).read_bytes()
    require(sha(raw) == AUTH_SHA, 'authorization differs')
    a = json.loads(raw)
    require(a['publicationAuthorized'] is True and a['fullStageReady'] is False, 'authorization scope differs')
    require(set(a['replacedExistingFiles']) == {'src/historyReplay.tsx', '.github/workflows/deploy.yml'}, 'replacement scope differs')
    return a

def restore(name, root, a):
    raw = (root / INVERSE).read_bytes()
    require(sha(raw) == a['inverseSHA256'], 'inverse contract differs')
    inv = json.loads(raw)
    require(set(inv) == set(a['replacedExistingFiles']), 'inverse scope differs')
    r = inv[name]
    raw = (root / name).read_bytes()
    require(sha(raw) == r['currentSHA256'], 'inverse input differs')
    lines = raw.decode().splitlines(keepends=True)
    end = 0
    for op in r['operations']:
        require(0 <= end <= op['start'] <= op['end'] <= len(lines), 'inverse span differs')
        require(sha(''.join(lines[op['start']:op['end']]).encode()) == op['currentSHA256'], 'inverse block differs')
        end = op['end']
    for op in reversed(r['operations']):
        lines[op['start']:op['end']] = [op['baselineText']]
    raw = ''.join(lines).encode()
    require(sha(raw) == r['baselineSHA256'] == a['baselinePins'][name], 'inverse baseline differs')
    return raw

@contextmanager
def previous_root(root=ROOT):
    a = authorization(root)
    with tempfile.TemporaryDirectory(prefix='rate-label-prior-') as folder:
        target = Path(folder)
        for n, h in a['baselinePins'].items():
            raw = restore(n, root, a) if n in a['replacedExistingFiles'] else (root / safe(n)).read_bytes()
            require(sha(raw) == h, 'immutable baseline changed: ' + n)
            p = target / safe(n)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
        yield target

def verify(receipt, root=ROOT, dist=None):
    a = authorization(root)
    require(receipt.get('schemaVersion') == 'rate-liftoff-publication-03' and receipt.get('publicationAuthorized') is True, 'publication authorization absent')
    require(receipt.get('scope') == a['scope'] and receipt.get('fullStageReady') is False, 'release scope changed')
    require(receipt.get('authorizationSHA256') == AUTH_SHA, 'authorization binding differs')
    require(sha((root / DATA).read_bytes()) == DATA_SHA, 'research payload changed')
    require(set(receipt['publicFilePins']) == set(a['baselinePins']) | set(a['allowedChanges']), 'pin coverage differs')
    for n, h in receipt['publicFilePins'].items():
        require(sha((root / safe(n)).read_bytes()) == h, 'public file changed: ' + n)
    for n, h in a['approvedChangedPins'].items():
        require(sha((root / safe(n)).read_bytes()) == h, 'approved change differs: ' + n)
    with previous_root(root) as prior:
        previous = previous_verify(json.loads((prior / PREVIOUS).read_bytes()), root=prior)
    result = dict(status='PASS_RATE_LIFTOFF_LABEL_03', previousGate=previous, legacyGateReplayed=True, fullStageReady=False, publicationAuthorized=True, publishedSHA256=DATA_SHA)
    if dist is not None:
        result['distFilesScanned'] = verify_assets(dist, receipt, root)
    return result

def legacy_tests(root=ROOT):
    # Build the exact inverse-restored predecessor, never re-pin its receipt or feed
    # current JS under an old filename. Tests below run unchanged in that fixture.
    with previous_root(root) as prior:
        link = prior / 'node_modules'
        source = (root / 'node_modules').resolve()
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(source)], check=True, stdout=subprocess.DEVNULL)
        else:
            link.symlink_to(source, target_is_directory=True)
        try:
            subprocess.run(['node', str(source / 'vite/bin/vite.js'), 'build'], cwd=prior, check=True)
            previous_verify(json.loads((prior / PREVIOUS).read_bytes()), root=prior, dist=prior / 'dist')
            subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_verify_rate_liftoff_publish_02.py', '-v'], cwd=prior, check=True)
            subprocess.run([sys.executable, '-B', 'scripts/verify_rate_liftoff_publish_02.py', '--legacy-tests', '--dist', 'dist'], cwd=prior, check=True)
        finally:
            if os.name == 'nt':
                os.rmdir(link)
            else:
                link.unlink()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dist', type=Path)
    p.add_argument('--legacy-tests', action='store_true')
    args = p.parse_args()
    result = verify(json.loads((ROOT / RECEIPT).read_bytes()), dist=args.dist)
    if args.legacy_tests:
        legacy_tests()
    print(json.dumps(result, ensure_ascii=False))
if __name__ == '__main__':
    main()
