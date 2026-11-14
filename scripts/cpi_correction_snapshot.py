"""Restore baseline48 exactly: immutable a2069 snapshot plus a thin public delta."""
import ast
from collections import Counter
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from macro_publication_snapshot import flatten
from macro_refresh_v2_snapshot import HISTORY_MODULES as OLD_HISTORY_MODULES

HISTORY_MODULES = set(OLD_HISTORY_MODULES) | {'test_verify_macro_refresh_v2_publish'}
from macro_refresh_v2_snapshot import ROOT, sha, members, snapshot_files as preceding_files
from macro_refresh_v2_snapshot import SNAPSHOT_SHA as PRECEDING_SHA
from pce_publication_snapshot import safe

BASE_COMMIT = '48acc06192cc9c5907acecd640e97328a988a9cc'
SNAPSHOT = 'release/snapshots/cpi-correction-base-48acc06.delta.zip'
SNAPSHOT_SHA = 'f479442e124c608213ed618d53455cc4975634664fedda4b555ff87f72d26e50'


def snapshot_files(root=ROOT):
    raw = (root / SNAPSHOT).read_bytes()
    if sha(raw) != SNAPSHOT_SHA:
        raise ValueError('Immutable baseline48 snapshot differs')
    delta = members(raw)
    manifest = json.loads(delta['__manifest__.json'])
    if manifest['baselineCommit'] != BASE_COMMIT or manifest['baseSnapshotSHA256'] != PRECEDING_SHA:
        raise ValueError('Baseline48 predecessor identity differs')
    if set(delta) != {'__manifest__.json'} | {'files/' + n for n in manifest['overlayFiles']}:
        raise ValueError('Baseline48 thin overlay coverage differs')
    files = preceding_files(root)
    for name in manifest['overlayFiles']:
        safe(name)
        if name.endswith('.zip'):
            raise ValueError('Nested immutable archives must be external references')
        files[name] = delta['files/' + name]
    for name, expected in manifest['externalFiles'].items():
        raw = (root / safe(name)).read_bytes()
        if sha(raw) != expected:
            raise ValueError('Referenced immutable archive differs: ' + name)
        files[name] = raw
    pins = manifest['filePins']
    if set(files) != set(pins) or any(sha(files[n]) != expected for n, expected in pins.items()):
        raise ValueError('Exact baseline48 public scope or bytes differ')
    return files


def history_ids(root=ROOT):
    files = snapshot_files(root)
    return [f'{name}.{cls.name}.{method.name}' for name in sorted(HISTORY_MODULES)
            for cls in ast.parse(files['scripts/' + name + '.py'].decode('utf-8')).body
            if isinstance(cls, ast.ClassDef)
            for method in cls.body if isinstance(method, ast.FunctionDef) and method.name.startswith('test_')]


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
    with tempfile.TemporaryDirectory(prefix='cpi-correction-baseline48-') as folder:
        target = Path(folder)
        for name, raw in snapshot_files(root).items():
            dest = target / safe(name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        yield target


def execution_report(output, expected):
    seen = [identity if identity.endswith('.' + method) else identity + '.' + method
            for method, identity in re.findall(r'^(test_\w+) \(([\w.]+)\)', output, re.MULTILINE)]
    if Counter(seen) != Counter(expected) or re.search(r'\bskipped=|\.\.\. skipped|_FailedTest|expected failure|unexpected success|^FAILED', output, re.MULTILINE):
        raise ValueError('Inherited discovery/execution differs or a case was skipped/failed')
    return {'run': len(seen), 'ids': sorted(seen), 'skipped': 0, 'discoveryErrors': []}


def replay_previous_gate(root=ROOT):
    """Execute the original v2 verifier and its unchanged on-disk receipt."""
    with previous_root(root) as previous:
        result = subprocess.run([sys.executable, '-S', '-B', 'scripts/verify_macro_refresh_v2_publish.py'],
                                cwd=previous, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode:
            raise ValueError('Exact baseline48 actual gate failed: ' + result.stdout + result.stderr)
        return json.loads(result.stdout)


def run_history(root=ROOT):
    """Original v2 actual gate, its five cases, and all 54 predecessor cases."""
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
                [sys.executable, '-S', '-B', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_verify_macro_refresh_v2_publish.py', '-v'],
                [sys.executable, '-S', '-B', 'scripts/verify_macro_refresh_v2_publish.py', '--legacy-tests', '--dist', 'dist'],
            ]:
                result = subprocess.run(command, cwd=previous, capture_output=True, text=True, encoding='utf-8', errors='replace')
                text = result.stdout + '\n' + result.stderr
                print(text, flush=True)
                transcripts.append(text)
                if result.returncode:
                    raise RuntimeError('Exact baseline48/predecessor replay failed: ' + repr(command))
        finally:
            if os.name == 'nt':
                os.rmdir(link)
            else:
                link.unlink()
    return execution_report('\n'.join(transcripts), expected)
