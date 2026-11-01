"""Replay publication tests against their immutable public release versions.

Only the explicitly enumerated versioned suites are sharded; every discovered
case must appear exactly once in the inherited gate's real unittest output.
"""
import ast
from collections import Counter
from contextlib import contextmanager
import hashlib
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = 'release/snapshots/macro-research-baseline-1a0231d.zip'
SNAPSHOT_SHA = '3324f23b14e8182e287fadc5926c1d94db21d2c89154cd08e36ff03b0555d048'
BASE_RECEIPT = 'release/rate-liftoff-publication-03.json'
HISTORICAL_MODULES = frozenset('test_verify_' + name + '_publish' + suffix for name, suffix in [
    ('economic_mechanisms', ''), ('heatmap', ''), ('inflation_overview', ''),
    ('pandemic_overview', ''), ('rate_liftoff', ''), ('rate_liftoff', '_02'),
    ('rate_liftoff', '_03'), ('replay_reading', ''), ('taper_priority', ''),
    ('taper_priority', '_02'),
])


def archive_bytes(root=ROOT):
    raw = (root / SNAPSHOT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SNAPSHOT_SHA:
        raise ValueError('Frozen public research snapshot changed')
    return raw


@contextmanager
def baseline_root(root=ROOT):
    with zipfile.ZipFile(io.BytesIO(archive_bytes(root))) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive paths')
        with tempfile.TemporaryDirectory(prefix='macro-frozen-research-') as directory:
            target = Path(directory)
            for name in names:
                p = Path(name)
                if p.is_absolute() or '..' in p.parts or ':' in name or '\\' in name:
                    raise ValueError('Unsafe archive path')
                dest = target / p
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.read(name))
            yield target


def legacy_case_ids(root=ROOT):
    ids = set()
    with zipfile.ZipFile(io.BytesIO(archive_bytes(root))) as archive:
        for module in HISTORICAL_MODULES:
            source = archive.read('scripts/' + module + '.py').decode('utf-8')
            for cls in ast.parse(source).body:
                if isinstance(cls, ast.ClassDef):
                    for method in cls.body:
                        if isinstance(method, ast.FunctionDef) and method.name.startswith('test_'):
                            ids.add(f'{module}.{cls.name}.{method.name}')
    return ids


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def split_suite(suite):
    current, historical = [], []
    for test in flatten(suite):
        module = test.__class__.__module__.split('.')[-1]
        (historical if module in HISTORICAL_MODULES else current).append(test)
    return unittest.TestSuite(current), historical


def run_legacy_tests(root=ROOT):
    expected = legacy_case_ids(root)
    # A newly changed historical test may not disappear into an older fixture.
    with zipfile.ZipFile(io.BytesIO(archive_bytes(root))) as archive:
        for module in HISTORICAL_MODULES:
            name = 'scripts/' + module + '.py'
            if (root / name).read_bytes().replace(b'\r\n', b'\n') != archive.read(name):
                raise ValueError('Historical test changed without versioned admission: ' + name)
    with baseline_root(root) as previous:
        link = previous / 'node_modules'
        source = (root / 'node_modules').resolve()
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(source)], check=True, stdout=subprocess.DEVNULL)
        else:
            link.symlink_to(source, target_is_directory=True)
        try:
            commands = [
                ['node', str(source / 'vite/bin/vite.js'), 'build'],
                [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_verify_rate_liftoff_publish_03.py', '-v'],
                [sys.executable, '-B', 'scripts/verify_rate_liftoff_publish_03.py', '--legacy-tests', '--dist', 'dist'],
            ]
            transcripts = []
            for command in commands:
                result = subprocess.run(command, cwd=previous, capture_output=True, text=True, encoding='utf-8', errors='replace')
                text = result.stdout + '\n' + result.stderr
                transcripts.append(text)
                print(text, flush=True)
                if result.returncode:
                    raise RuntimeError('Frozen release test/build failed: ' + ' '.join(command))
        finally:
            if os.name == 'nt':
                os.rmdir(link)
            else:
                link.unlink()
    output = '\n'.join(transcripts)
    seen = []
    for method, identity in re.findall(r'^(test_\w+) \(([\w.]+)\)', output, re.MULTILINE):
        seen.append(identity if identity.endswith('.' + method) else identity + '.' + method)
    if Counter(seen) != Counter(expected) or re.search(r'\bskipped=|\.\.\. skipped', output):
        raise ValueError('Legacy execution/discovery mismatch or skipped tests: ' + repr(sorted(Counter(seen).items())))
    return {'run': len(seen), 'ids': sorted(seen), 'skipped': 0}
