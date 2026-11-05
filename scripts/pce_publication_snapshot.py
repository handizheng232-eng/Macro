"""Exact public 528f3da fixture for the superseded macro publication contract."""
import ast
from collections import Counter
from contextlib import contextmanager
import hashlib
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from macro_publication_snapshot import flatten

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = 'release/snapshots/macro-pce-baseline-528f3da.zip'
SNAPSHOT_SHA = '230432210c1d01bd8eba9c37de7b2955fb4b4d5de99e85f53da26b0ed62a7cd1'
PREVIOUS_RECEIPT = 'release/macro-refresh-publication-01.json'
PREVIOUS_MODULE = 'test_verify_macro_refresh_publish'


def safe(name):
    path = Path(name)
    if (not name or name.startswith('/') or path.is_absolute() or '..' in path.parts or ':' in name or '\\' in name
            or name.startswith(('data/raw/', '.hermes/', '.env'))):
        raise ValueError('Unsafe or private archive member: ' + name)
    return path


def snapshot_files(root=ROOT):
    raw = (root / SNAPSHOT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SNAPSHOT_SHA:
        raise ValueError('Immutable preceding macro snapshot differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate public snapshot paths')
        return {safe(name).as_posix(): archive.read(name) for name in names}


@contextmanager
def previous_root(root=ROOT):
    files = snapshot_files(root)
    with tempfile.TemporaryDirectory(prefix='pce-previous-macro-') as directory:
        target = Path(directory)
        for name, data in files.items():
            dest = target / safe(name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        yield target


def previous_case_ids(root=ROOT):
    source = snapshot_files(root)['scripts/' + PREVIOUS_MODULE + '.py'].decode('utf-8')
    return {f'{PREVIOUS_MODULE}.{cls.name}.{method.name}'
            for cls in ast.parse(source).body if isinstance(cls, ast.ClassDef)
            for method in cls.body if isinstance(method, ast.FunctionDef) and method.name.startswith('test_')}


def split_previous_tests(suite):
    current, previous = [], []
    for case in flatten(suite):
        destination = previous if case.__class__.__module__.split('.')[-1] == PREVIOUS_MODULE else current
        destination.append(case)
    return unittest.TestSuite(current), previous


def run_previous_tests(root=ROOT):
    name = 'scripts/' + PREVIOUS_MODULE + '.py'
    if (root / name).read_bytes().replace(b'\r\n', b'\n') != snapshot_files(root)[name]:
        raise ValueError('Preceding publication test changed without a new contract')
    with previous_root(root) as previous:
        result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts',
                                 '-p', PREVIOUS_MODULE + '.py', '-v'], cwd=previous,
                                capture_output=True, text=True, encoding='utf-8', errors='replace')
    output = result.stdout + '\n' + result.stderr
    print(output, flush=True)
    if result.returncode:
        raise RuntimeError('Preceding macro publication assertions failed')
    seen = []
    for method, identity in re.findall(r'^(test_\w+) \(([\w.]+)\)', output, re.MULTILINE):
        seen.append(identity if identity.endswith('.' + method) else identity + '.' + method)
    if Counter(seen) != Counter(previous_case_ids(root)) or re.search(r'\bskipped=|\.\.\. skipped', output):
        raise ValueError('Preceding macro test discovery/execution mismatch')
    return {'run': len(seen), 'ids': sorted(seen), 'skipped': 0}
