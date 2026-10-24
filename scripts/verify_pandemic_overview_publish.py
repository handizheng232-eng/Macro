"""Six approved overview cards only; replay the immutable publication chain."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from verify_inflation_overview_publish import verify_overview, RECEIPT as PREVIOUS
from verify_renewed_easing_publish import require
from verify_renewed_limited_publish import verify_assets

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'release/pandemic-overview-publication-01.json'
INVERSE = 'release/pandemic-overview-inverse-01.json'
CHANGED = {'src/App.tsx', '.github/workflows/deploy.yml'}
ADDED = {'src/pandemicOverview.ts', 'src/pandemicOverview.test.tsx', INVERSE,
         'scripts/verify_pandemic_overview_publish.py',
         'scripts/test_verify_pandemic_overview_publish.py', PREVIOUS}
APPROVED = '89090c04874a1f7c5f7a929b9ad90561d54b635a1655b051ef9f09f4b6146274'
PREVIOUS_SHA = '1e856e30cdd295fd8af746a4d2f7b6592e25215b3207c5fe60d606c9514c9e9c'
APP_SHA = '2551223e862092f623f8cb9778ad4c839103e57081faaebcfbe9241c8d36737a'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def restore(name, root):
    inverse = json.loads((root / INVERSE).read_bytes())
    require(set(inverse) == CHANGED, 'inverse scope differs')
    record = inverse[name]
    raw = (root / name).read_bytes()
    require(sha(raw) == record['currentSHA256'], 'inverse input differs')
    lines = raw.decode('utf-8').splitlines(keepends=True)
    end = 0
    for op in record['operations']:
        require(0 <= end <= op['start'] <= op['end'] <= len(lines), 'inverse span differs')
        require(sha(''.join(lines[op['start']:op['end']]).encode()) == op['currentSHA256'], 'inverse block differs')
        end = op['end']
    for op in reversed(record['operations']):
        lines[op['start']:op['end']] = [op['baselineText']]
    restored = ''.join(lines).encode()
    prior = json.loads((root / PREVIOUS).read_bytes())
    require(sha(restored) == record['baselineSHA256'] == prior['publicFilePins'][name], 'inverse baseline differs')
    return restored


@contextmanager
def previous_root(root=ROOT):
    prior = json.loads((root / PREVIOUS).read_bytes())
    names = set(prior['publicFilePins']) | {PREVIOUS}
    # Include the explicitly pinned dependencies of every preceding receipt.
    pending = list(names)
    while pending:
        name = pending.pop()
        if name.startswith('release/') and name.endswith('.json'):
            value = json.loads((root / name).read_bytes())
            if isinstance(value, dict):
                for dependency in value.get('publicFilePins', {}):
                    if dependency not in names:
                        names.add(dependency)
                        pending.append(dependency)
    with tempfile.TemporaryDirectory(prefix='pandemic-overview-prior-') as directory:
        target = Path(directory)
        for name in names:
            p = Path(name)
            require(not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name, 'unsafe projection path')
            dest = target / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(restore(name, root) if name in CHANGED else (root / p).read_bytes())
        yield target


def verify_pandemic(receipt, root=ROOT, dist=None):
    require(receipt.get('schemaVersion') == 'pandemic-overview-publication-01', 'wrong overview contract')
    require(receipt.get('scope') == 'approved-six-period-overview-only', 'overview scope differs')
    require(receipt.get('publicationAuthorized') is True and receipt.get('pageQAComplete') is True, 'authorization/QA absent')
    require(receipt.get('fullResearchComplete') is False and receipt.get('pinEncoding') == 'git-lf', 'research or encoding upgrade')
    require(sha((root / PREVIOUS).read_bytes()) == receipt['legacyReceiptSHA256'] == PREVIOUS_SHA, 'immutable overview receipt changed')
    prior = json.loads((root / PREVIOUS).read_bytes())
    require(set(receipt['publicFilePins']) == set(prior['publicFilePins']) | ADDED, 'overview pin coverage differs')
    for name, expected in receipt['publicFilePins'].items():
        require(sha((root / name).read_bytes()) == expected, 'public file changed: ' + name)
    require(receipt['approvedOverviewSHA256'] == APPROVED == sha((root / 'src/pandemicOverview.ts').read_bytes()), 'approved content differs')
    require(sha((root / 'src/App.tsx').read_bytes()) == APP_SHA, 'approved UI differs')
    with previous_root(root) as previous:
        result = verify_overview(prior, root=previous)
    if dist is not None:
        result['distFilesScanned'] = verify_assets(dist, receipt)
    result.update(status='PASS_AUTHORIZED_PANDEMIC_OVERVIEW_01', previousOverviewPeriods=8,
                  overviewPeriods=6, fullResearchComplete=False, legacyGateReplayed=True)
    return result


def legacy_tests(root=ROOT):
    with previous_root(root) as previous:
        for source in (root / 'scripts').glob('*.py'):
            dest = previous / 'scripts' / source.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        for pattern in ('test_verify_inflation_overview_publish.py',):
            subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', pattern, '-v'], cwd=previous, check=True)
        subprocess.run([sys.executable, '-B', 'scripts/verify_inflation_overview_publish.py', '--legacy-tests'], cwd=previous, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path)
    parser.add_argument('--legacy-tests', action='store_true')
    args = parser.parse_args()
    try:
        result = verify_pandemic(json.loads((ROOT / RECEIPT).read_bytes()), dist=args.dist)
        if args.legacy_tests:
            legacy_tests()
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        print(json.dumps({'status': 'INVALID_PANDEMIC_OVERVIEW_01', 'reason': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
