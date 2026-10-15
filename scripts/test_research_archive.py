"""Archive configuration regressions; temporary markers are NOT research evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent


class ArchiveConfigurationTests(unittest.TestCase):
    def test_explicit_archive_root_controls_both_builders_not_code_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp).resolve()
            env = dict(os.environ, REPLAY_RESEARCH_ROOT=str(archive))
            code = (
                'import json, build_history_replay as h, build_hawkish_replay as k; '
                'print(json.dumps([str(h.STAGE), str(k.STAGE)]))'
            )
            result = subprocess.run([sys.executable, '-c', code], cwd=SCRIPTS,
                                    env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            stages = [Path(p) for p in json.loads(result.stdout)]
            self.assertTrue(all(p.is_relative_to(archive) for p in stages),
                            'Both builders must use the explicitly configured archive, not the worktree')

    def test_external_archive_rejects_output_even_through_a_parent_segment(self):
        import research_archive as archive_config
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp).resolve()
            with patch.dict(os.environ, REPLAY_RESEARCH_ROOT=str(archive)):
                self.assertTrue(hasattr(archive_config, 'require_writable_output'),
                                'External archive writes need a guard')
                with self.assertRaisesRegex(ValueError, 'read-only'):
                    archive_config.require_writable_output(archive / 'child/../new.json')
                archive_config.require_writable_output(REPO / 'src/data/allowed.json')

    def test_invalid_explicit_root_does_not_fall_back_to_worktree(self):
        from research_archive import research_root
        from unittest.mock import patch
        for value in ('', 'relative/archive', str(REPO / 'does-not-exist')):
            with self.subTest(value=value), patch.dict(os.environ, REPLAY_RESEARCH_ROOT=value):
                with self.assertRaises(ValueError):
                    research_root()

    def test_working_manifests_are_separate_from_original_evidence_sandbox(self):
        import hashlib
        import inspect
        import build_history_replay as builder
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / 'originals'
            config = root / 'working'
            stage.mkdir(); config.mkdir()
            manifest = config / 'sources.json'
            manifest.write_text(json.dumps({'schemaVersion': 'parent-source-manifest-1',
                'stageStart': '2026-09-01', 'stageEnd': '2026-10-09', 'sources': []}), encoding='utf-8')
            self.assertIn('configuration_root', inspect.signature(builder.build).parameters,
                          'Generated manifests must not be written into the read-only originals')
            result = builder.build(stage=stage, root=root, as_of='2026-10-09',
                parent_source_manifest=manifest, configuration_root=config)
            self.assertEqual(result['reports'], [])
            # Configuration paths stay confined too; selecting a config root is
            # not permission to admit an original from that root.
            with self.assertRaisesRegex(ValueError, 'out-of-stage'):
                builder.build(stage=stage, root=root, as_of='2026-10-09',
                    parent_source_manifest=manifest, configuration_root=stage)
            payload = b'{}'
            outsider = config / 'outside-market.json'
            outsider.write_bytes(payload)
            value = json.loads(manifest.read_text(encoding='utf-8'))
            value['marketPaths'] = {'path': str(outsider), 'sha256': hashlib.sha256(payload).hexdigest()}
            manifest.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'out-of-stage'):
                builder.build(stage=stage, root=root, as_of='2026-10-09',
                    parent_source_manifest=manifest, configuration_root=config)

    def test_separate_baseline_configuration_still_requires_pins_and_confined_originals(self):
        import hashlib
        import build_history_replay as builder
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / 'originals'; stage.mkdir()
            config = root / 'working'; config.mkdir()
            raw = stage / 'source.txt'; raw.write_bytes(b'TEST ONLY original')
            baseline = config / 'baseline.json'
            baseline.write_text(json.dumps({'sources': [{'id': 'official-test', 'kind': '官方一手'}],
                                            'reports': [], 'events': []}), encoding='utf-8')
            pin = lambda p: {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
            binding = {**pin(baseline), 'sourceIds': ['official-test'], 'reportIds': [],
                       'sourceArtifacts': {'official-test': pin(raw)}}
            manifest = config / 'sources.json'
            config_data = {'schemaVersion': 'parent-source-manifest-1', 'stageStart': '2026-09-01',
                           'stageEnd': '2026-10-09', 'sources': [], 'baseline': binding}
            def run():
                manifest.write_text(json.dumps(config_data), encoding='utf-8')
                return builder.build(stage=stage, root=root, as_of='2026-10-09',
                    parent_source_manifest=manifest, configuration_root=config)
            self.assertEqual([s['id'] for s in run()['sources']], ['official-test'])
            binding['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'SHA'):
                run()
            binding.update(pin(baseline))
            outsider = config / 'not-original.txt'; outsider.write_bytes(raw.read_bytes())
            binding['sourceArtifacts']['official-test'] = pin(outsider)
            with self.assertRaisesRegex(ValueError, 'out-of-stage'):
                run()

    def test_runner_blocks_archive_mutation_but_allows_scratch(self):
        runner = SCRIPTS / 'run_data_tests.py'
        self.assertTrue(runner.is_file(), 'A reusable full-suite runner is required')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'originals'; archive.mkdir()
            original = archive / 'original.txt'; original.write_bytes(b'TEST ONLY')
            scratch = root / 'scratch'; scratch.mkdir()
            code = """
import sys
from pathlib import Path
from run_data_tests import protect_archive
archive, scratch = map(Path, sys.argv[1:])
protect_archive(archive)
original = archive / 'original.txt'
assert original.read_bytes() == b'TEST ONLY'
for action in (lambda: original.write_bytes(b'changed'),
               lambda: original.unlink(),
               lambda: (archive / 'child').mkdir(),
               lambda: original.rename(scratch / 'moved.txt')):
    try:
        action()
    except PermissionError:
        pass
    else:
        raise AssertionError('Archive mutation was allowed')
(scratch / 'allowed.txt').write_bytes(b'TEST ONLY')
"""
            result = subprocess.run([sys.executable, '-c', code, str(archive), str(scratch)],
                                    cwd=SCRIPTS, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(original.read_bytes(), b'TEST ONLY')
            self.assertTrue((scratch / 'allowed.txt').is_file())


if __name__ == '__main__':
    unittest.main()
