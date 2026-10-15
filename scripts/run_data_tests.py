"""Run ALL Python data tests with explicit interpreter/archive configuration.

Usage: python scripts/run_data_tests.py [--python /absolute/python]
Environment: DATA_TEST_PYTHON, REPLAY_RESEARCH_ROOT, TMPDIR (private scratch).
No download, archive copying, test selection, skips, or publication is performed.
"""
import argparse
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from research_archive import REPO_ROOT, research_root


def protect_archive(root):
    """Deny Python-level mutations of the external root, including resolved links.

    This is defense in depth, not an OS sandbox for arbitrary native extensions.
    The test subprocesses only use builders with their own output guards.
    """
    root = Path(root).resolve()
    mutations = {'os.remove': (0,), 'os.rmdir': (0,), 'os.mkdir': (0,),
                 'os.rename': (0, 1), 'os.chmod': (0,), 'os.utime': (0,),
                 'os.link': (0, 1), 'os.symlink': (1,), 'os.truncate': (0,)}

    def inside(value):
        if not isinstance(value, (str, bytes, os.PathLike)):
            return False
        return Path(os.fsdecode(value)).resolve().is_relative_to(root)

    def audit(event, args):
        if event == 'open':
            path, mode, flags = args
            writes = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if writes and inside(path):
                raise PermissionError('External research archive is read-only')
        elif event in mutations and any(inside(args[index]) for index in mutations[event]):
            raise PermissionError('External research archive is read-only')

    sys.addaudithook(audit)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', dest='python', default=os.environ.get('DATA_TEST_PYTHON'),
                        help='Explicit Python executable with scripts/requirements-data-tests.txt installed')
    args = parser.parse_args(argv)
    if args.python and Path(args.python).resolve() != Path(sys.executable).resolve():
        interpreter = Path(args.python)
        if not interpreter.is_absolute() or not interpreter.is_file():
            parser.error('--python / DATA_TEST_PYTHON must be an existing absolute executable')
        env = dict(os.environ)
        env.pop('DATA_TEST_PYTHON', None)
        env['PYTHONUTF8'] = '1'
        return subprocess.run([str(interpreter), str(Path(__file__).resolve())], env=env,
                              cwd=REPO_ROOT).returncode
    versions = {}
    missing = []
    for module, distribution in (('pymupdf', 'PyMuPDF'), ('pypdf', 'pypdf')):
        try:
            importlib.import_module(module)
            versions[distribution] = importlib.metadata.version(distribution)
        except ImportError:
            missing.append(distribution)
    if missing:
        print('Missing data-test dependencies: ' + ', '.join(missing), file=sys.stderr)
        print('Install scripts/requirements-data-tests.txt into the explicitly selected Python.', file=sys.stderr)
        return 2
    root = research_root()
    scratch = Path(tempfile.gettempdir()).resolve()
    if root != REPO_ROOT:
        if scratch.is_relative_to(root):
            parser.error('TMPDIR must be outside the read-only research archive')
        protect_archive(root)
    os.chdir(REPO_ROOT)
    # Script execution starts with scripts/ on sys.path; `python -m unittest`
    # also exposes the repository for tests importing the scripts namespace.
    sys.path.insert(0, str(REPO_ROOT))
    print(json.dumps({'python': sys.executable, 'dependencies': versions,
                      'externalArchiveReadOnly': root != REPO_ROOT,
                      'discovery': 'scripts/test_*.py'}, ensure_ascii=True), flush=True)
    suite = unittest.defaultTestLoader.discover(str(REPO_ROOT / 'scripts'), pattern='test_*.py')
    expected = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    success = result.wasSuccessful() and not result.skipped and result.testsRun == expected and expected > 0
    print(json.dumps({'discovered': expected, 'run': result.testsRun,
                      'failures': len(result.failures), 'errors': len(result.errors),
                      'skipped': len(result.skipped), 'passed': success}), flush=True)
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
