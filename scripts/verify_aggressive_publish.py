"""rr04 scoped publication; immutable preceding public gate in exact inverse tree."""
import argparse
from contextlib import contextmanager
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

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'release/aggressive-publication-01.json'
INVERSE = 'release/snapshots/aggressive-inverse-01.zip'
INVERSE_SHA = '734e60877909744b96556cb1ae01753cb631691aa91080bbf54f2a82d32c7ac8'
DATA = 'src/data/historyReplayAggressiveHikesQt.json'
REVIEW_SHA = 'ac527c88a43dc24e67c35e88692bdf6edcfbac62ff1adf22692255a1a314d667'
SCOPE = 'history/inflation-qt-repricing/aggressive-hikes-qt'
CHANGES = {'.gitattributes', '.github/workflows/deploy.yml', 'src/App.tsx', 'src/historyReplay.tsx', 'src/inflationOverview.test.tsx', 'src/inflationOverview.ts', 'src/replayComments.tsx', 'src/replayOutline.tsx', 'src/aggressiveReview.test.tsx', 'src/reviewMissingDetails.test.tsx', 'src/templateParity.test.tsx', 'src/data/aggressiveReviewExpected.fixture.json', DATA, 'scripts/verify_aggressive_publish.py', 'scripts/test_verify_aggressive_publish.py'}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def need(ok, message):
    if not ok:
        raise ValueError(message)

def safe(name):
    from verify_comments_publish import safe as prior_safe
    return prior_safe(name)

def contract(root):
    raw = (root / INVERSE).read_bytes()
    need(sha(raw) == INVERSE_SHA, 'inverse binding differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        need(len(names) == len(set(names)), 'duplicate inverse members')
        for name in names:
            safe(name)
        m = json.loads(z.read('__manifest__.json'))
        need(set(names) == {'__manifest__.json', 'reviewed.json'} | {'files/' + n for n in m['replaced']}, 'inverse member scope')
        originals = {n: z.read('files/' + n) for n in m['replaced']}
        reviewed = z.read('reviewed.json')
        need(sha(reviewed) == REVIEW_SHA, 'reviewed data binding differs')
    return m, originals, reviewed

def verify(root=ROOT, dist=None):
    m, originals, reviewed = contract(root)
    r = json.loads((root / RECEIPT).read_bytes())
    need(r.get('publicationAuthorized') is True and r.get('scope') == SCOPE, 'publication authorization/scope')
    need(r.get('historicalResearchAuthorizationExpanded') is False, 'research authorization expanded')
    need(r.get('inverseSHA256') == INVERSE_SHA, 'receipt inverse binding')
    need(set(r['sourcePins']) == CHANGES, 'source pin scope')
    for n, h in r['sourcePins'].items():
        need(sha((root / safe(n)).read_bytes()) == h, 'source pin differs: ' + n)
    for n, h in m['baselinePins'].items():
        raw = originals[n] if n in originals else (root / safe(n)).read_bytes()
        need(sha(raw) == h, 'baseline differs: ' + n)
    expected = set(m['baselinePins']) | CHANGES | {RECEIPT, INVERSE}
    for directory in ('src', 'scripts', 'docs', 'public', 'release', '.github', 'comments-worker', 'buildPlugins'):
        for p in (root / directory).rglob('*'):
            if p.is_file() and not any(x in p.parts for x in ('node_modules', '__pycache__', '.wrangler')) and p.suffix != '.pyc':
                need(p.relative_to(root).as_posix() in expected, 'unapproved public file')
    old = json.loads(reviewed)
    data = json.loads((root / DATA).read_bytes())
    need(data['localReview']['publicReleaseAllowed'] is True and data['reviewProjection']['publicationAuthorized'] is True, 'current authorization absent')
    need(data['localReview']['notice'] == '本篇已获阶段性公网发布授权。父方已核限定研究稿；不等于全部严格历史证据认证。Wind原数量门槛12篇/月，用户已接受本篇现有数量例外；公众号门槛15篇/月；知识星球历史可得待确认。已停止补采，整阶段未完成。', 'notice differs')
    need(data['reviewProjection']['statusOverlay'] == '本篇已获阶段性公网发布授权；父方限定准入，不提升严格历史资格或整阶段完成状态。', 'status overlay differs')
    for parent, key in [('localReview', 'notice'), ('localReview', 'publicReleaseAllowed'), ('reviewProjection', 'statusOverlay'), ('reviewProjection', 'publicationAuthorized')]:
        data[parent][key] = old[parent][key]
    need(data == old, 'economic text/data/qualification differs from reviewed candidate')
    need(data['localReview']['fullStageReady'] is False and data['localReview']['strictHistoricalEligible'] is False and data['reviewProjection']['fullStageReady'] is False, 'research flags upgraded')
    need(len(data['sources']) == 109 and len(data['marketPaths']['series']) == 13, 'research counts differ')
    for n in (DATA, 'src/data/aggressiveReviewExpected.fixture.json'):
        text = (root / n).read_text(encoding='utf-8')
        need(not re.search(r'(?<![A-Za-z0-9])[A-Z]:[\\/]|unicodeStart|rawLiteral|rawHorizon|typedSupport|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', text), 'private support/contact in public data')
    result = {'status': 'PASS_AGGRESSIVE_PUBLICATION_01', 'scope': SCOPE, 'researchUnchangedExceptFourStatusPaths': True, 'baselineFiles': len(m['baselinePins'])}
    if dist is not None:
        files = {p.relative_to(dist).as_posix(): p for p in dist.rglob('*') if p.is_file()}
        need(set(files) == set(r['distPins']), 'dist scope differs')
        for n, p in files.items():
            raw = p.read_bytes()
            need(sha(raw) == r['distPins'][n], 'dist pin differs: ' + n)
            need(p.suffix in ('.html', '.js', '.css', '.svg'), 'private asset type')
            need(not re.search(r'(?<![A-Za-z0-9])[A-Z]:[\\/]|unicodeStart|rawLiteral|rawHorizon|typedSupport', raw.decode()), 'private support in dist')
            if p.suffix == '.svg':
                need(raw == (root / 'public' / n).read_bytes(), 'chart bytes differ')
        html = (dist / 'index.html').read_text(encoding='utf-8')
        linked = {n.removeprefix('/Macro/') for n in re.findall(r'(?:src|href)="(/Macro/assets/[^"]+)"', html)}
        need(len(linked) == 2 and linked <= set(files), 'HTML asset coverage differs')
        result['distFilesScanned'] = len(files)
    return result

@contextmanager
def previous_root(root=ROOT):
    m, originals, _ = contract(root)
    with tempfile.TemporaryDirectory(prefix='aggressive-exact-comments-') as folder:
        target = Path(folder)
        for n, h in m['baselinePins'].items():
            raw = originals[n] if n in originals else (root / safe(n)).read_bytes()
            need(sha(raw) == h, 'inverse baseline differs: ' + n)
            dest = target / safe(n)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        yield target

def legacy(root=ROOT):
    from verify_comments_publish import public_commands
    with previous_root(root) as prior:
        source = (root / 'node_modules').resolve()
        link = prior / 'node_modules'
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(source)], check=True, stdout=subprocess.DEVNULL)
        else:
            link.symlink_to(source, target_is_directory=True)
        env = dict(os.environ, VITE_CUSTOM_COMMENTS_ENABLED='true', VITE_COMMENTS_API='https://macro-replay-comments.handizheng232.workers.dev')
        try:
            subprocess.run(['node', str(source / 'vite/bin/vite.js'), 'build'], cwd=prior, env=env, check=True)
            for cmd in public_commands((prior / '.github/workflows/deploy.yml').read_text()):
                if cmd[0] == 'python':
                    cmd[0] = sys.executable
                print('INHERITED COMMAND ' + json.dumps(cmd), flush=True)
                subprocess.run(cmd, cwd=prior, check=True)
        finally:
            if os.name == 'nt':
                os.rmdir(link)
            else:
                link.unlink()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path)
    parser.add_argument('--legacy-tests', action='store_true')
    args = parser.parse_args()
    result = verify(dist=args.dist)
    if args.legacy_tests:
        legacy()
        result['completePredecessorGateReplayed'] = True
    print(json.dumps(result))
