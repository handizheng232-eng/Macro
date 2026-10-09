"""Offline parent-ledger contracts, exercising real accepted archives only."""
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '美国宏观复盘/降息起步后的双向政策时代/2026-01_2026-08'
MODULE = Path(__file__).with_name('replay_parent_sources.py')

class ParentSourcesTests(unittest.TestCase):
    def module(self):
        self.assertTrue(MODULE.exists(), 'Parent path/SHA allowlist adapter is not implemented')
        spec = importlib.util.spec_from_file_location('parent_sources', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_clean_parent_verified_star_source_is_adapted_without_private_body(self):
        module = self.module()
        reports, audits = module.load_parent_sources(STAGE, ROOT, [module.DEFAULT_SOURCES[0]])
        self.assertEqual(len(reports), 16)
        self.assertEqual(reports[0]['channel'], '知识星球')
        self.assertEqual(reports[0]['sha256'], '0aceaea71a54799cf91c1516e85d12c31caa1599442a06d49015cb19815a416c')
        self.assertTrue(all(r['sourceQuality']['parentLedgerVerified'] and r['sourceQuality']['originalBodyVerified'] for r in reports))
        self.assertTrue(all(not r['historicalAsOfEligible'] and r['firstAvailableDate'] is None for r in reports))
        self.assertTrue(all(not Path(r['path']).is_absolute() for r in reports))
        serialized = json.dumps(reports, ensure_ascii=False)
        for private in ('fullPage', 'pypdfText', 'researchScopeEvidence', '@', 'E:\\\\', 'privateSourceScreenshot'):
            self.assertNotIn(private, serialized)
        self.assertTrue(all(not a['searchExhaustive'] for a in audits))

    def test_all_current_parent_sources_exclude_reprints_and_legacy_scope(self):
        from collections import Counter
        module = self.module()
        reports, _ = module.load_parent_sources(STAGE, ROOT)
        self.assertEqual(Counter(r['channel'] for r in reports), {'知识星球': 138, 'Wind': 80, '微信': 41})
        ids = {r['id'] for r in reports}
        self.assertNotIn('wechat-min5-5302914972ca2ce3', ids)
        self.assertNotIn('wechat-min5-6a6eb65592ba166e', ids)
        self.assertEqual(len(ids), 259)
        self.assertTrue(all(r['sourceQuality']['parentLedgerVerified'] for r in reports))
        self.assertTrue(all(r['firstAvailableDate'] is None and not r['historicalAsOfEligible'] for r in reports))
        self.assertEqual(Counter(r['date'][:7] for r in reports if r['channel'] == 'Wind'), {f'2026-{m:02}': 10 for m in range(1, 9)})
        self.assertNotIn('pypdfText', json.dumps(reports))
        self.assertNotIn('@', json.dumps(reports))

    def test_new_continuous_transcripts_require_pinned_parent_review(self):
        from collections import Counter
        module = self.module()
        manifest = json.loads((STAGE / '研究/parent-sources-20261009-zsxq-completion03.json').read_text(encoding='utf-8'))
        reports, _ = module.load_parent_sources(STAGE, ROOT, manifest['sources'])
        self.assertEqual(len(reports), 22)
        self.assertEqual(Counter(r['date'][:7] for r in reports), {'2026-01': 14, '2026-02': 8})
        self.assertEqual(sum(r['pageCount'] for r in reports), 313)
        self.assertTrue(all(r['sourceQuality']['originalBodyVerified'] for r in reports))
        self.assertTrue(all(r['sourceQuality']['versionType'] == 'platform_original_continuous_transcript' for r in reports))
        self.assertTrue(all(r['publicationDate'] is None and not r['historicalAsOfEligible'] for r in reports))
        self.assertNotIn('pymupdfText', json.dumps(reports))

    def test_parent_verified_increment_completes_all_monthly_channel_quotas(self):
        from replay_monthly_coverage import build_monthly_coverage
        module = self.module()
        manifest = json.loads((STAGE / '研究/parent-sources-20261009-zsxq-completion03.json').read_text(encoding='utf-8'))
        reports, audits = module.load_parent_sources(STAGE, ROOT, module.DEFAULT_SOURCES + manifest['sources'])
        coverage = build_monthly_coverage('2026-01-01', '2026-08-31', reports, ROOT, STAGE, {'rows': audits})
        self.assertEqual(coverage['acceptedCells'], 24)
        self.assertTrue(coverage['complete'])
        self.assertTrue(all(row['channels']['知识星球']['bodyCount'] == 20 for row in coverage['rows']))
        self.assertTrue(all(not cell['searchExhaustive'] for row in coverage['rows'] for cell in row['channels'].values()))

    def test_agent_true_flags_cannot_bypass_parent_book_and_ledger_sha(self):
        module = self.module()
        descriptor = {**module.DEFAULT_SOURCES[0], 'sourceSHA256': '0' * 64, 'parentVerified': True}
        with self.assertRaisesRegex(ValueError, 'SHA'):
            module.load_parent_sources(STAGE, ROOT, [descriptor])
        descriptor = {**module.DEFAULT_SOURCES[0], 'parentLedgers': [
            {**module.DEFAULT_SOURCES[0]['parentLedgers'][0], 'sha256': '0' * 64}]}
        with self.assertRaisesRegex(ValueError, 'SHA'):
            module.load_parent_sources(STAGE, ROOT, [descriptor])

if __name__ == '__main__':
    unittest.main()
