"""Comments-only successor: exact inverse, immutable CPI/research chain, current asset scan."""
import argparse
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'release/comments-publication-01.json'
INVERSE = 'release/snapshots/comments-inverse-01.zip'
# Bound after creating the reviewed release contract, never old research receipts.
INVERSE_SHA = 'a69fee3842b247f3c0ae4d66170e2fa1c42812dcd87a03a62683500c8a764e88'
SCOPE = 'history/inflation-qt-repricing/rate-liftoff-qt-guidance'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def safe(name):
    require(isinstance(name, str) and name and not name.startswith('/') and ':' not in name and '\\' not in name, 'unsafe path')
    p = PurePosixPath(name)
    require('..' not in p.parts and '.' not in p.parts and str(p) == name, 'unsafe path')
    require(not any(x in p.parts for x in ('.git', 'node_modules', '.wrangler', '__pycache__')) and not p.name.startswith('.env'), 'private path')
    return Path(name)

def contract(root=ROOT):
    raw = (root / INVERSE).read_bytes()
    require(sha(raw) == INVERSE_SHA, 'inverse binding differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        require(len(names) == len(set(names)), 'duplicate archive members')
        for name in names:
            safe(name)
        manifest = json.loads(z.read('__manifest__.json'))
        require(set(names) == {'__manifest__.json'} | {'files/' + n for n in manifest['replaced']}, 'inverse member scope differs')
        originals = {n: z.read('files/' + n) for n in manifest['replaced']}
    return manifest, originals

def verify(root=ROOT, dist=None):
    m, originals = contract(root)
    r = json.loads((root / RECEIPT).read_bytes())
    require(r.get('publicationAuthorized') is True, 'publication authorization absent')
    require(r.get('scope') == SCOPE and r.get('historicalResearchAuthorizationExpanded') is False, 'scope differs')
    require(r.get('inverseSHA256') == INVERSE_SHA, 'receipt inverse differs')
    require(set(r['sourcePins']) == set(m['allowedChanges']), 'source pin scope differs')
    # Approved current file hashes are independently bound inside the inverse archive.
    for name, expected in m['approvedPins'].items():
        require(sha((root / safe(name)).read_bytes()) == expected, 'approved source differs: ' + name)
    for name, expected in r['sourcePins'].items():
        require(sha((root / safe(name)).read_bytes()) == expected, 'source pin differs: ' + name)
    for name, expected in m['baselinePins'].items():
        raw = originals[name] if name in originals else (root / safe(name)).read_bytes()
        require(sha(raw) == expected, 'immutable baseline differs: ' + name)
    allowed = set(m['baselinePins']) | set(m['allowedChanges']) | {RECEIPT, INVERSE}
    for directory in ('src', 'scripts', 'docs', 'public', 'release', '.github', 'comments-worker'):
        for p in (root / directory).rglob('*'):
            if not p.is_file() or any(x in p.parts for x in ('node_modules', '__pycache__', '.wrangler')) or p.suffix == '.pyc':
                continue
            require(p.resolve().is_relative_to(root.resolve()) and p.relative_to(root).as_posix() in allowed, 'unapproved public file')
    app = (root / 'src/App.tsx').read_text(encoding='utf-8')
    require(app.count("commentRoute={historyReplay === 'rate-liftoff-qt-guidance' ? '" + SCOPE + "' : undefined}") == 1, 'route opt-in differs')
    worker = json.loads((root / 'comments-worker/wrangler.jsonc').read_bytes())
    require(worker['vars']['ENVIRONMENT'] == 'production', 'local CORS must not ship')
    workflow = (root / '.github/workflows/deploy.yml').read_text()
    require('VITE_CUSTOM_COMMENTS_ENABLED: "true"' in workflow and 'VITE_COMMENTS_API: https://macro-replay-comments.handizheng232.workers.dev' in workflow, 'production build flags absent')
    result = {'status': 'PASS_COMMENTS_SCOPE_01', 'scope': SCOPE, 'baselineFiles': len(m['baselinePins']), 'researchAuthorizationExpanded': False}
    if dist is not None:
        actual = {p.relative_to(dist).as_posix() for p in dist.rglob('*') if p.is_file()}
        require(actual == set(r['distPins']), 'asset scope differs')
        for name, expected in r['distPins'].items():
            raw = (dist / safe(name)).read_bytes()
            require(sha(raw) == expected, 'asset bytes differ: ' + name)
            require(Path(name).suffix in ('.js', '.css', '.html', '.svg'), 'private filetype')
            require(not re.search(r'(?<![A-Za-z0-9])[A-Z]:[\\\\/]|unicodeStart|rawLiteral|rawHorizon|typedSupport', raw.decode()), 'private path/support in dist')
            if name.endswith('.svg'):
                require(raw == (root / 'public' / safe(name)).read_bytes(), 'chart source bytes differ')
        html = (dist / 'index.html').read_text(encoding='utf-8')
        linked = {n.removeprefix('/Macro/') for n in re.findall(r'(?:src|href)="(/Macro/assets/[^"]+)"', html)}
        assets = {n for n in actual if n.startswith('assets/')}
        # Preserve HTML asset coverage, explicitly admitting only the lazy fallback chunk.
        lazy = assets - linked
        require(len(lazy) == 1 and all(re.fullmatch(r'assets/giscus-[A-Za-z0-9_-]+\.js', n) for n in lazy), 'lazy asset scope differs')
        require(linked <= assets and len(linked) == 2, 'HTML asset set differs')
        entry = next(n for n in linked if n.endswith('.js'))
        require(all(('./' + Path(n).name).encode() in (dist / entry).read_bytes() for n in lazy), 'lazy chunk reference absent')
        result['distFilesScanned'] = len(actual)
        js = b'\n'.join(p.read_bytes() for p in dist.rglob('*.js'))
        require(b'https://macro-replay-comments.handizheng232.workers.dev' in js, 'production API origin absent from build')
    return result

@contextmanager
def previous_root(root=ROOT):
    m, originals = contract(root)
    with tempfile.TemporaryDirectory(prefix='comments-exact-cpi-') as folder:
        target = Path(folder)
        for name, expected in m['baselinePins'].items():
            raw = originals[name] if name in originals else (root / safe(name)).read_bytes()
            require(sha(raw) == expected, 'inverse baseline differs: ' + name)
            dest = target / safe(name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        yield target

def public_commands(workflow):
    """Replay every original Verify step, not the private research runner.

    The workflow bytes come from the digest-bound inverse. Frontend lint/test
    and current build run separately in CI; historical gates get their exact
    original source and their own build. Nested legacy gates remain unchanged.
    """
    import shlex
    commands = []
    selected = False
    collecting = False
    for line in workflow.splitlines():
        if line.startswith('      - name:'):
            selected = line.strip().startswith('- name: Verify ')
            collecting = False
        elif selected and line.startswith('        run: '):
            value = line.split('run: ', 1)[1]
            collecting = value == '|'
            if not collecting:
                commands.append(shlex.split(value))
        elif selected and collecting and line.startswith('          '):
            commands.append(shlex.split(line.strip()))
    require(commands and all(c and c[0] in ('node', 'python') for c in commands), 'original public commands absent or unsupported')
    require(not any('scripts/run_data_tests.py' in c for c in commands), 'private research runner is not a public gate')
    return commands


def legacy(root=ROOT):
    # Preserve all original public workflow assertions and nested legacy gates.
    # The separate archive-backed research suite is not this UI release gate.
    with previous_root(root) as prior:
        link = prior / 'node_modules'
        source = (root / 'node_modules').resolve()
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(source)], check=True, stdout=subprocess.DEVNULL)
        else:
            link.symlink_to(source, target_is_directory=True)
        env = dict(os.environ)
        env.pop('VITE_CUSTOM_COMMENTS_ENABLED', None)
        env.pop('VITE_COMMENTS_API', None)
        commands = [['node', str(source / 'vite/bin/vite.js'), 'build']]
        for command in public_commands((prior / '.github/workflows/deploy.yml').read_text()):
            commands.append(([sys.executable] + command[1:]) if command[0] == 'python' else command)
        try:
            for command in commands:
                print('INHERITED COMMAND ' + json.dumps(command), flush=True)
                subprocess.run(command, cwd=prior, env=env, check=True)
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
