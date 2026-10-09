"""Parent research admission: real archived research, never mock large libraries."""
import hashlib
import importlib
import json
import unittest
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '美国宏观复盘/降息起步后的双向政策时代/2026-01_2026-08'

def review_fixture(stage, report=None):
    """Private fixtures are never written to src/data or used for real research."""
    import replay_research_integration as module
    def section(identifier):
        return {'id': identifier, 'title': identifier, **{k: 'Fixture pending evidence' for k in module.BODY_FIELDS},
            'sourceIds': ['fixture-official'], 'reportIds': [report['id']] if report else []}
    source_path = stage / 'official.txt'
    source_path.write_text('Fixture official release text, not real research.', encoding='utf-8')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    opinions = []
    if report:
        import pymupdf
        with pymupdf.open(stage/'fixture.pdf') as pdf:
            quote = pdf[0].get_text('text').strip()
        opinions.append({'id': 'fixture-opinion', 'sourceId': report['id'], 'sourceSHA256': report['sha256'],
            'channel': 'Wind', 'publicationDate': report['publicationDate'], 'dateBasis': 'printed_publication_date',
            'actor': 'Fixture author', 'claim': 'Fixture conditional outlook', 'scope': 'Fixture US',
            'physicalPage': 1, 'paragraphId': None, 'quote': quote, 'locator': {'start': 0},
            'horizon': {'literalResearchWindow': '2026-12', 'deadlineMonth': '2026-12'},
            'conditions': ['Fixture condition'], 'limitations': ['Fixture only'], 'title': report['title'],
            'claimType': 'institutional_forecast',
            'realizationPair': {'note': 'Fixture ongoing', 'status': 'ongoing', 'realitySourceIds': [], 'factIds': []}})
    study = {'asOf': '2026-10-09', 'marketAnalysis': {'title': 'Fixture analysis', 'conclusion': 'Fixture conclusion',
        'limitations': ['Not real research'], 'sections': [section(s) for s in module.THEME_IDS]},
        'months': [{**section('fixture-'+m), 'month': m, 'opinionIds': [o['id'] for o in opinions],
            'factIds': [], 'marketPath': None, 'dynamicConvergence': 'Fixture evidence pending'} for m in ('2026-09','2026-10')],
        'revisionChains': [{'id': 'fixture-chain', 'label': 'Fixture chain', 'description': 'Fixture only',
                            'opinionIds': [o['id'] for o in opinions]}] if opinions else [],
        'sources': [{'id': 'fixture-official', 'title': 'Fixture source', 'publisher': 'Fixture publisher',
                     'url': 'https://www.federalreserve.gov/fixture', 'publicationDate': '2026-10-08',
                     'sha256': sha(source_path)}], 'officialFacts': [],
        'sourceAliases': [{'sourceId': report['id'], 'sha256': report['sha256'], 'aliasReason': 'Fixture same original'}] if report else [],
        'marketStatistics': {}}
    def save(name, value):
        p=stage/name; p.write_text(json.dumps(value), encoding='utf-8'); return sha(p)
    pins = {'study.json': save('study.json', study), 'opinions.json': save('opinions.json', {'opinions': opinions}),
            'official.txt': sha(source_path)}
    receipt = {'inputPins': pins, 'opinions': [{'opinionId': o['id'], 'accepted': True} for o in opinions],
               'semanticReview': {'facts': []}}
    accepted = module.reviewed_projection(study, {'opinions': opinions})
    manifest = {'schemaVersion': 'parent-reviewed-research-manifest-1',
        'stageStart': '2026-09-01', 'stageEnd': '2026-10-09', 'researchPath': 'study.json', 'opinionsPath': 'opinions.json',
        'inputPins': pins, 'acceptedOpinionIds': [o['id'] for o in opinions], 'acceptedFactIds': [],
        'verification': {'path': 'verification.json', 'sha256': save('verification.json', receipt)},
        'accepted': {'path': 'accepted.json', 'sha256': save('accepted.json', accepted)}}
    save('review.json', manifest)
    return stage/'review.json', manifest

class ExplicitResearchWindowTests(unittest.TestCase):
    def test_official_catalog_sha_must_correspond_to_an_actual_input_pin(self):
        from replay_research_integration import load_reviewed, reviewed_projection
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp);path,manifest=review_fixture(stage)
            study=json.loads((stage/'study.json').read_text(encoding='utf-8'))
            study['sources'][0]['sha256']='0'*64
            (stage/'study.json').write_text(json.dumps(study),encoding='utf-8')
            manifest['inputPins']['study.json']=hashlib.sha256((stage/'study.json').read_bytes()).hexdigest()
            receipt=json.loads((stage/'verification.json').read_text(encoding='utf-8'))
            receipt['inputPins']=manifest['inputPins']
            (stage/'verification.json').write_text(json.dumps(receipt),encoding='utf-8')
            manifest['verification']['sha256']=hashlib.sha256((stage/'verification.json').read_bytes()).hexdigest()
            accepted=reviewed_projection(study,{'opinions':[]})
            (stage/'accepted.json').write_text(json.dumps(accepted),encoding='utf-8')
            manifest['accepted']['sha256']=hashlib.sha256((stage/'accepted.json').read_bytes()).hexdigest()
            path.write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'source.*SHA'):
                load_reviewed(path,stage,stage,start='2026-09-01',end='2026-10-09')

    def test_pinned_review_cannot_admit_future_official_fact(self):
        from replay_research_integration import load_reviewed, reviewed_projection
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp);path,manifest=review_fixture(stage)
            study=json.loads((stage/'study.json').read_text(encoding='utf-8'))
            fact={'id':'fixture-future-fact','date':'2026-10-12','claim':'Fixture future release',
                  'sourceIds':['fixture-official'],'observationPeriod':'2026-09','value':{}}
            study['officialFacts']=[fact]
            (stage/'study.json').write_text(json.dumps(study),encoding='utf-8')
            manifest['inputPins']['study.json']=hashlib.sha256((stage/'study.json').read_bytes()).hexdigest()
            receipt=json.loads((stage/'verification.json').read_text(encoding='utf-8'))
            receipt.update(inputPins=manifest['inputPins'],semanticReview={'facts':[{'factId':fact['id'],'accepted':True}]})
            (stage/'verification.json').write_text(json.dumps(receipt),encoding='utf-8')
            manifest['verification']['sha256']=hashlib.sha256((stage/'verification.json').read_bytes()).hexdigest()
            manifest['acceptedFactIds']=[fact['id']]
            accepted=reviewed_projection(study,{'opinions':[]})
            (stage/'accepted.json').write_text(json.dumps(accepted),encoding='utf-8')
            manifest['accepted']['sha256']=hashlib.sha256((stage/'accepted.json').read_bytes()).hexdigest()
            path.write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'future'):
                load_reviewed(path,stage,stage,start='2026-09-01',end='2026-10-09')

    def test_new_cutoff_future_target_note_uses_actual_deadline_month(self):
        from test_replay_parent_sources import wind_fixture
        from replay_research_integration import reviewed_projection
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp);_,record=wind_fixture(stage)
            review_fixture(stage,record)
            projection=reviewed_projection(json.loads((stage/'study.json').read_text(encoding='utf-8')),
                json.loads((stage/'opinions.json').read_text(encoding='utf-8')))
            pair=projection['opinions'][0]['realizationPair']
            self.assertEqual(pair['status'],'ongoing')
            self.assertIn('2026-12',pair['note'])
            self.assertNotIn('9月目标',pair['note'])

    def test_review_projection_cannot_invent_quote_from_admitted_pdf(self):
        from test_replay_parent_sources import wind_fixture
        from replay_research_integration import integrate_reviewed, reviewed_projection
        from replay_parent_sources import load_parent_sources
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp);descriptor,record=wind_fixture(stage)
            reports,_=load_parent_sources(stage,stage,[descriptor],start='2026-09-01',end='2026-10-09')
            path,manifest=review_fixture(stage,record)
            private=json.loads((stage/'opinions.json').read_text(encoding='utf-8'))
            private['opinions'][0]['quote']='Invented fixture quote not on actual physical page'
            (stage/'opinions.json').write_text(json.dumps(private),encoding='utf-8')
            manifest['inputPins']['opinions.json']=hashlib.sha256((stage/'opinions.json').read_bytes()).hexdigest()
            receipt=json.loads((stage/'verification.json').read_text(encoding='utf-8'))
            receipt['inputPins']=manifest['inputPins']
            (stage/'verification.json').write_text(json.dumps(receipt),encoding='utf-8')
            manifest['verification']['sha256']=hashlib.sha256((stage/'verification.json').read_bytes()).hexdigest()
            accepted=reviewed_projection(json.loads((stage/'study.json').read_text(encoding='utf-8')),private)
            (stage/'accepted.json').write_text(json.dumps(accepted),encoding='utf-8')
            manifest['accepted']['sha256']=hashlib.sha256((stage/'accepted.json').read_bytes()).hexdigest()
            path.write_text(json.dumps(manifest),encoding='utf-8')
            data={'startDate':'2026-09-01','asOf':'2026-10-09','reports':reports,'sources':[],
                  'events':[],'reportIdAliases':{}}
            with self.assertRaisesRegex(ValueError,'excerpt'):
                integrate_reviewed(data,path,stage,stage,explicit_window=True)

    def test_explicit_two_month_pinned_review_integrates_only_admitted_sources(self):
        from test_replay_parent_sources import wind_fixture
        import build_history_replay as builder
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            descriptor, report = wind_fixture(stage)
            source_manifest = stage/'sources.json'
            source_manifest.write_text(json.dumps({'schemaVersion': 'parent-source-manifest-1',
                'stageStart': '2026-09-01', 'stageEnd': '2026-10-09', 'sources': [descriptor]}), encoding='utf-8')
            review_path, _ = review_fixture(stage, report)
            data = builder.build(stage=stage, root=stage, as_of='2026-10-09',
                parent_source_manifest=source_manifest, reviewed_research_manifest=review_path)
            self.assertEqual([m['month'] for m in data['monthlyReplay']], ['2026-09', '2026-10'])
            self.assertEqual(len(data['revisionChains']), 1)
            self.assertEqual(len(data['windResearchEvidence']), 1)
            self.assertEqual(data['windResearchEvidence'][0]['reportId'], report['id'])
            self.assertFalse(data['monthlyCoverage']['complete'])
            self.assertTrue(all(not s['historicalAsOfEligible'] for s in data['sources']))
            (stage/'official.txt').write_text('Tampered fixture official release', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'SHA is stale'):
                builder.build(stage=stage, root=stage, as_of='2026-10-09',
                    parent_source_manifest=source_manifest, reviewed_research_manifest=review_path)


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
