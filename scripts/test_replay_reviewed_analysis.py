"""Test-only prose fixtures; no synthetic macro observations are emitted."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from replay_reviewed_analysis import reviewed_analysis, BODY_FIELDS

class ReviewedAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.stage = Path(self.temp.name)
        self.study = self.stage / '研究'
        self.study.mkdir()
        self.original = {'asOf': '2026-08-31', 'conclusion': 'TEST ORIGINAL', 'sections': [
            {'id': 'test-theme', 'sourceIds': ['test-source'], 'reportIds': ['test-report'],
             **{field: 'TEST ONLY' for field in BODY_FIELDS}}], 'references': [{'id': 'test-source'}]}
        self.raw = self.study / 'market-analysis.json'
        self.raw.write_text(json.dumps(self.original), encoding='utf-8')
        self.sha = hashlib.sha256(self.raw.read_bytes()).hexdigest()

    def put(self, analysis, sha=None):
        (self.study / 'market-analysis-reviewed.json').write_text(
            json.dumps({'sourceSha256': sha or self.sha, 'analysis': analysis}), encoding='utf-8')

    def test_no_overlay_leaves_original_evidence_unmodified(self):
        self.assertEqual(reviewed_analysis(self.stage, self.original), self.original)

    def test_valid_review_keeps_citations_and_raw_file(self):
        reviewed = copy.deepcopy(self.original)
        reviewed['conclusion'] = 'TEST CONCISE'
        self.put(reviewed)
        self.assertEqual(reviewed_analysis(self.stage, self.original)['conclusion'], 'TEST CONCISE')
        self.assertEqual(hashlib.sha256(self.raw.read_bytes()).hexdigest(), self.sha)

    def test_stale_source_hash_fails_before_using_review(self):
        self.put(self.original, '0' * 64)
        with self.assertRaisesRegex(ValueError, 'SHA'):
            reviewed_analysis(self.stage, self.original)

    def test_conditional_source_and_theme_order_cannot_disappear(self):
        reviewed = copy.deepcopy(self.original)
        reviewed['sections'][0]['sourceIds'] = []
        self.put(reviewed)
        with self.assertRaisesRegex(ValueError, 'citation'):
            reviewed_analysis(self.stage, self.original)

    def test_cutoff_and_registry_cannot_be_changed(self):
        reviewed = copy.deepcopy(self.original)
        reviewed['asOf'] = '2026-10-02'
        self.put(reviewed)
        with self.assertRaisesRegex(ValueError, 'cutoff'):
            reviewed_analysis(self.stage, self.original)
        reviewed = copy.deepcopy(self.original)
        reviewed['references'] = []
        self.put(reviewed)
        with self.assertRaisesRegex(ValueError, 'registry'):
            reviewed_analysis(self.stage, self.original)

    def test_empty_conclusion_is_not_a_finished_review(self):
        reviewed = copy.deepcopy(self.original)
        reviewed['conclusion'] = ''
        self.put(reviewed)
        with self.assertRaisesRegex(ValueError, 'conclusion'):
            reviewed_analysis(self.stage, self.original)

if __name__ == '__main__':
    unittest.main()
