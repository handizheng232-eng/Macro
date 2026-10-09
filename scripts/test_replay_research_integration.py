"""Parent research admission: real archived research, never mock large libraries."""
import hashlib
import importlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '美国宏观复盘/降息起步后的双向政策时代/2026-01_2026-08'

class ParentResearchTests(unittest.TestCase):
    def test_independent_verifier_reads_every_original_and_exact_anchor(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('replay_research_integration'),
                             'Independent original-reader implementation missing')
        module = importlib.import_module('replay_research_integration')
        result = module.verify_originals(STAGE, ROOT)
        self.assertEqual(result['counts']['selectedSources'], 35)
        self.assertEqual(result['counts']['opinionsChecked'], 39)
        self.assertEqual(result['counts']['opinionsAccepted'], 39)
        self.assertEqual(result['counts']['months'], 8)
        self.assertEqual(result['counts']['revisionChains'], 4)
        self.assertEqual(result['counts']['officialFactsChecked'], 46)
        self.assertEqual(result['failures'], [])
        self.assertGreater(result['counts']['physicalPages'], 100)
        self.assertEqual(result['counts']['originalOfficialFiles'], 40)
        self.assertEqual(result['counts']['newOfficialSnapshots'], 3)
        wind=[s for s in result['sources'] if s['channel']=='Wind']
        self.assertEqual(len(wind),11)
        self.assertTrue(all(s.get('printedDateAnchors') for s in wind),'Parent dates were not independently located on actual PDF pages')

    def test_official_values_are_reparsed_in_their_actual_release_vintage(self):
        module = importlib.import_module('replay_research_integration')
        self.assertTrue(hasattr(module, 'verify_fact_semantics'), 'Numeric/chronology fact reader missing')
        result = module.verify_fact_semantics(STAGE, ROOT)
        self.assertEqual(len(result['facts']), 46)
        self.assertEqual(result['failures'], [])
        q2 = next(f for f in result['facts'] if f['factId'] == 'release-bea-gdp-advance-estimate-2nd-quarter-2026')
        self.assertEqual(q2['reparsed']['realGDPSAAR'], 1.5)
        self.assertEqual(q2['reparsed']['privateDomesticFinalPurchasesSAAR'], 3.9)
        self.assertTrue(all(f['semanticSpans'] for f in result['facts']))

    def test_parent_reviewed_projection_is_short_public_and_retrospective(self):
        module = importlib.import_module('replay_research_integration')
        self.assertTrue(hasattr(module, 'reviewed_projection'), 'Public reviewed research projection missing')
        document = json.loads((STAGE/'研究/monthly-expectation-reality-20261009.json').read_text(encoding='utf-8'))
        private = json.loads((STAGE/'研究/channel-verified-opinions-20261009.json').read_text(encoding='utf-8'))
        output = module.reviewed_projection(document, private)
        self.assertEqual(len(output['opinions']),39)
        self.assertEqual(len(output['monthlyReplay']),8)
        self.assertEqual(len(output['revisionChains']),4)
        self.assertEqual([s['id'] for s in output['marketAnalysis']['sections']], module.THEME_IDS)
        by_source = {}
        for opinion in output['opinions']:
            by_source.setdefault(opinion['reportId'],0)
            by_source[opinion['reportId']] += len(opinion['evidenceExcerpt'] or '')
            self.assertFalse(opinion['historicalAsOfEligible'])
            self.assertIsNone(opinion['firstAvailableDate'])
            self.assertFalse(opinion['isMarketConsensus'])
            if opinion['forecastHorizon'].get('deadlineMonth','') > document['asOf'][:7]:
                self.assertEqual(opinion['status'],'ongoing')
        self.assertLessEqual(max(by_source.values()),100)
        serialized=json.dumps(output,ensure_ascii=False)
        for denied in ('documentPath','containerText','contextSHA256','contacts','@spdbi','FCCNN88','E:\\\\'):
            self.assertNotIn(denied,serialized)

    def test_all_52_official_market_sources_and_32_treasury_points_are_independent(self):
        module = importlib.import_module('replay_research_integration')
        result = module.verify_originals(STAGE, ROOT)
        self.assertEqual(result.get('allResearchSourceHashCount'),52,'Market metadata/H10 archives were not independently read')
        self.assertEqual(result.get('treasuryFredComparisons'),32)
        self.assertEqual(result.get('maximumTreasuryDifferenceBp'),0)
        self.assertEqual(result.get('intervalRecomputed',{}).get('twoYearChangeBp'),87)
        self.assertEqual(result.get('intervalRecomputed',{}).get('tenYearChangeBp'),56)
        self.assertEqual(result.get('intervalRecomputed',{}).get('spreadChangeBp'),-31)
        self.assertEqual(result.get('h10PublicationBoundaryVerified'),True)

    def test_explicit_pin_rejects_modified_input_without_touching_originals(self):
        import copy
        import tempfile
        module = importlib.import_module('replay_research_integration')
        manifest=json.loads((STAGE/'研究/parent-reviewed-research-20261009-manifest.json').read_text(encoding='utf-8'))
        # A copied manifest is the only altered file; real source archives stay
        # intact. Names containing "verified" cannot override a stale digest.
        manifest=copy.deepcopy(manifest)
        manifest['accepted']['sha256']='0'*64
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'verified-manifest.json'
            path.write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'accepted SHA is stale'):
                module.load_reviewed(path,STAGE,ROOT)

    def test_cli_review_admission_parameter_is_explicit(self):
        import subprocess
        import sys
        result=subprocess.run([sys.executable,str(ROOT/'scripts/build_hawkish_replay.py'),'--help'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0)
        self.assertIn('--reviewed-research-manifest',result.stdout)

if __name__ == '__main__':
    unittest.main()
