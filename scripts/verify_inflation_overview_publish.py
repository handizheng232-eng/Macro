"""Approved overview UI only; replay the complete immutable heatmap gate."""
import argparse
import hashlib
import json
import tempfile

from contextlib import contextmanager
from pathlib import Path
from verify_heatmap_publish import verify_heatmap, RECEIPT as HEATMAP, sha, ECONOMIC, READING, RESEARCH
from verify_renewed_easing_publish import require
from verify_renewed_limited_publish import verify_assets

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'release/inflation-overview-publication-01.json'
INVERSE = 'release/inflation-overview-inverse-01.json'
UI = {'src/App.tsx', 'src/styles.css'}
ADDED = {'src/inflationOverview.ts', 'src/inflationOverview.test.tsx', INVERSE,
         'scripts/verify_inflation_overview_publish.py',
         'scripts/test_verify_inflation_overview_publish.py', '.github/workflows/deploy.yml'}
VERIFIERS = {'scripts/' + name for name in (
    'verify_heatmap_publish.py', 'verify_economic_mechanisms_publish.py',
    'verify_replay_reading_publish.py', 'verify_renewed_limited_publish.py',
    'verify_renewed_easing_publish.py', 'verify_replay_publish.mjs')}


def restore(name, root):
    inverse = json.loads((root / INVERSE).read_bytes())
    require(set(inverse) == UI, 'inverse scope differs')
    record = inverse[name]
    raw = (root / name).read_bytes().replace(b'\r\n', b'\n')
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
    prior = json.loads((root / HEATMAP).read_bytes())
    require(sha(restored) == record['baselineSHA256'] == prior['publicFilePins'][name], 'inverse baseline differs')
    return restored


@contextmanager
def previous_root(root=ROOT):
    names = {HEATMAP, ECONOMIC, READING, RESEARCH}
    for receipt in (HEATMAP, ECONOMIC, READING, RESEARCH):
        names.update(json.loads((root / receipt).read_bytes())['publicFilePins'])
    with tempfile.TemporaryDirectory(prefix='inflation-overview-prior-') as directory:
        target = Path(directory)
        for name in names:
            p = Path(name)
            require(not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name, 'unsafe projection path')
            dest = target / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(restore(name, root) if name in UI else (root / p).read_bytes())
        yield target


def verify_overview(receipt, root=ROOT, dist=None):
    require(receipt.get('schemaVersion') == 'inflation-overview-publication-01', 'wrong overview contract')
    require(receipt.get('scope') == 'approved-eight-period-overview-only', 'overview scope differs')
    require(receipt.get('publicationAuthorized') is True and receipt.get('pageQAComplete') is True, 'authorization/QA absent')
    require(receipt.get('fullResearchComplete') is False and receipt.get('pinEncoding') == 'git-lf', 'research or encoding upgrade')
    legacy = (root / HEATMAP).read_bytes()
    require(sha(legacy) == receipt['legacyReceiptSHA256'], 'immutable heatmap receipt changed')
    prior = json.loads(legacy)
    required = set(prior['publicFilePins']) | ADDED | VERIFIERS | {HEATMAP}
    require(set(receipt['publicFilePins']) == required, 'overview pin coverage differs')
    for name, expected in receipt['publicFilePins'].items():
        require(sha((root / name).read_bytes()) == expected, 'public file changed: ' + name)
    # Separate signed content approval from freely rehashed outer source pins.
    require(receipt['approvedOverviewSHA256'] == 'e5d495d80c84d44275cfcac5bb12ce555622559e226971b1d9b90c81c5e398fb', 'approved content anchor differs')
    require(sha((root / 'src/inflationOverview.ts').read_bytes()) == receipt['approvedOverviewSHA256'], 'approved overview content differs')
    with previous_root(root) as previous:
        result = verify_heatmap(prior, root=previous)
    if dist is not None:
        result['distFilesScanned'] = verify_assets(dist, receipt)
    result.update(status='PASS_AUTHORIZED_INFLATION_OVERVIEW_01', overviewPeriods=8, fullResearchComplete=False, legacyGateReplayed=True)
    return result


def legacy_tests():
    """Run unchanged legacy tests against the exact signed pre-overview tree."""
    import subprocess
    import sys
    import shutil
    with previous_root() as previous:
        # Execute unchanged tests in an isolated public fixture, with their real
        # __file__-derived roots. No patched assertions or mutated verifiers.
        for source in (ROOT / 'scripts').glob('*.py'):
            dest = previous / 'scripts' / source.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        for name in ('docs/macro-replay-template.md', 'docs/macro-replay-reading-template.md'):
            dest = previous / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        for pattern in ('test_verify_replay_reading_publish.py', 'test_verify_economic_mechanisms_publish.py', 'test_verify_heatmap_publish.py'):
            run = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', pattern, '-v'], cwd=previous)
            if run.returncode:
                return False
        return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dist', type=Path)
    p.add_argument('--legacy-tests', action='store_true')
    a = p.parse_args()
    try:
        result = verify_overview(json.loads((ROOT / RECEIPT).read_bytes()), dist=a.dist)
        if a.legacy_tests:
            require(legacy_tests(), 'legacy tests failed')
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({'status': 'INVALID_INFLATION_OVERVIEW_01', 'reason': str(error)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
