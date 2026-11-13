"""Restore exact a2069bd public approval using an existing archive plus a thin delta."""
import ast
from collections import Counter
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile
import unittest
import tempfile
from macro_publication_snapshot import HISTORICAL_MODULES, flatten
from pce_publication_snapshot import safe

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = 'release/snapshots/macro-refresh-base-a2069bd.delta.zip'
SNAPSHOT_SHA = '19f9587fd9267dd20e9c26a87f76ed4c8597c86a9ad7161aac99faaa16d1a7c0'
BASE_COMMIT = 'a2069bdd9aaaa8366944a1e7d5e34c58dc47fa15'
HISTORY_MODULES = set(HISTORICAL_MODULES) | {'test_verify_macro_refresh_publish',
    'test_verify_pce_distribution_publish', 'test_verify_editorial_openings_publish'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def members(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        # ZipInfo normalizes Windows separators; validate the original central
        # directory name too, before that normalization can hide an unsafe path.
        if any(info.orig_filename != info.filename or safe(info.orig_filename).as_posix() != info.orig_filename for info in archive.infolist()):
            raise ValueError('Unsafe raw archive path')
        if len(names) != len(set(names)) or any(safe(n).as_posix() != n for n in names):
            raise ValueError('Unsafe, noncanonical or duplicate archive paths')
        return {n: archive.read(n) for n in names}


def snapshot_files(root=ROOT):
    raw = (root / SNAPSHOT).read_bytes()
    if sha(raw) != SNAPSHOT_SHA:
        raise ValueError('Immutable refresh snapshot differs')
    delta = members(raw)
    manifest = json.loads(delta['__manifest__.json'])
    if manifest['baselineCommit'] != BASE_COMMIT:
        raise ValueError('Editorial baseline identity differs')
    expected_delta = {'__manifest__.json'} | {'files/' + n for n in manifest['overlayFiles']}
    if set(delta) != expected_delta:
        raise ValueError('Thin delta coverage differs')
    base_raw = (root / safe(manifest['baseArchive'])).read_bytes()
    if sha(base_raw) != manifest['baseArchiveSHA256']:
        raise ValueError('Immutable preceding archive differs')
    files = members(base_raw)
    for name in manifest['overlayFiles']:
        safe(name)
        files[name] = delta['files/' + name]
    for name, expected in manifest['externalFiles'].items():
        data = (root / safe(name)).read_bytes()
        if sha(data) != expected:
            raise ValueError('Referenced immutable archive differs: ' + name)
        files[name] = data
    pins = manifest['filePins']
    if set(files) != set(pins) or any(sha(files[n]) != expected for n, expected in pins.items()):
        raise ValueError('Restored editorial public scope or bytes differ')
    return files


def history_ids(root=ROOT):
    files = snapshot_files(root)
    return {f'{name}.{cls.name}.{method.name}' for name in HISTORY_MODULES
            for cls in ast.parse(files['scripts/' + name + '.py'].decode('utf-8')).body
            if isinstance(cls, ast.ClassDef)
            for method in cls.body if isinstance(method, ast.FunctionDef) and method.name.startswith('test_')}


def split_history(suite, root=ROOT):
    current, historical = [], []
    for case in flatten(suite):
        (historical if case.__class__.__module__.split('.')[-1] in HISTORY_MODULES else current).append(case)
    if Counter(case.id() for case in historical) != Counter(history_ids(root)):
        raise ValueError('Current discovery differs from exact historical case IDs')
    files = snapshot_files(root)
    for name in HISTORY_MODULES:
        path = 'scripts/' + name + '.py'
        if (root / path).read_bytes().replace(b'\r\n', b'\n') != files[path]:
            raise ValueError('Historical assertions changed: ' + path)
    return unittest.TestSuite(current), historical


@contextmanager
def previous_root(root=ROOT):
    with tempfile.TemporaryDirectory(prefix='refresh-v2-approved-editorial-') as folder:
        target = Path(folder)
        for name, raw in snapshot_files(root).items():
            dest = target / safe(name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        yield target


def run_history(root=ROOT):
    """Replay the editorial six and its preceding 48 original cases exactly once."""
    expected = history_ids(root)
    with previous_root(root) as previous:
        source = (root / 'node_modules').resolve()
        if not (source / 'vite/bin/vite.js').is_file():
            raise ValueError('Install locked node dependencies before historical replay')
        link = previous / 'node_modules'
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(source)], check=True, stdout=subprocess.DEVNULL)
        else:
            link.symlink_to(source, target_is_directory=True)
        transcripts = []
        try:
            for command in [
                ['node', str(source / 'vite/bin/vite.js'), 'build'],
                [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_verify_editorial_openings_publish.py', '-v'],
                [sys.executable, '-B', 'scripts/verify_editorial_openings_publish.py', '--legacy-tests', '--dist', 'dist'],
            ]:
                result = subprocess.run(command, cwd=previous, capture_output=True, text=True, encoding='utf-8', errors='replace')
                text = result.stdout + '\n' + result.stderr
                print(text, flush=True)
                transcripts.append(text)
                if result.returncode:
                    raise RuntimeError('Exact editorial/predecessor replay failed: ' + repr(command))
        finally:
            if os.name == 'nt':
                os.rmdir(link)
            else:
                link.unlink()
    output = '\n'.join(transcripts)
    seen = [identity if identity.endswith('.' + method) else identity + '.' + method
            for method, identity in re.findall(r'^(test_\w+) \(([\w.]+)\)', output, re.MULTILINE)]
    if Counter(seen) != Counter(expected) or re.search(r'\bskipped=|\.\.\. skipped|_FailedTest', output):
        raise ValueError('Inherited discovery/execution differs or a case was skipped')
    return {'run': len(seen), 'ids': sorted(seen), 'skipped': 0, 'discoveryErrors': []}
