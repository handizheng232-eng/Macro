"""Regression checks for integration of actual audit outputs, not invented fixtures."""
import importlib.util
import unittest
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('replay_build', ROOT / 'scripts/build_history_replay.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReplayIntegrationTests(unittest.TestCase):
    def test_explicit_parent_pin_preserves_real_market_baseline_without_legacy_views(self):
        import hashlib
        market_path=module.STAGE/'研究/market-paths.json'
        with tempfile.TemporaryDirectory(dir=module.STAGE/'核验/模板整改20261009/Code') as tmp:
            source_path=Path(tmp)/'sources.json'
            source_path.write_text(json.dumps({'schemaVersion':'parent-source-manifest-1',
                'stageStart':'2026-09-01','stageEnd':'2026-10-09','sources':[],
                'marketPaths':{'path':str(market_path),'sha256':hashlib.sha256(market_path.read_bytes()).hexdigest()}}),encoding='utf-8')
            data=module.build(as_of='2026-10-09',parent_source_manifest=source_path)
            self.assertEqual(len(data.get('marketPaths',{}).get('series',[])),3)
            self.assertEqual(data['marketPaths']['series'],module.load(market_path)['series'])
            self.assertEqual(data['researchEvidence'],[])
            self.assertEqual(data['monthlyCoverage']['acceptedCells'],0)

    def test_cli_explicit_check_is_reproducible_and_quota_failure_writes_nothing(self):
        import subprocess
        import sys
        from test_replay_parent_sources import wind_fixture
        from test_replay_research_integration import review_fixture
        help_result = subprocess.run([sys.executable, str(ROOT/'scripts/build_history_replay.py'), '--help'],
            capture_output=True, text=True)
        for flag in ('--as-of', '--parent-source-manifest', '--reviewed-research-manifest', '--check-only'):
            self.assertIn(flag, help_result.stdout)
        with tempfile.TemporaryDirectory(dir=module.STAGE/'核验/模板整改20261009/Code') as tmp:
            stage = Path(tmp)
            descriptor, record = wind_fixture(stage)
            review_path, _ = review_fixture(stage, record)
            source_path=stage/'sources.json'
            source_path.write_text(json.dumps({'schemaVersion': 'parent-source-manifest-1',
                'stageStart': '2026-09-01', 'stageEnd': '2026-10-09', 'sources': [descriptor]}), encoding='utf-8')
            command=[sys.executable, str(ROOT/'scripts/build_history_replay.py'), '--stage', str(stage),
                '--as-of', '2026-10-09', '--parent-source-manifest', str(source_path),
                '--reviewed-research-manifest', str(review_path), '--check-only']
            a=subprocess.run(command,capture_output=True,text=True)
            b=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(a.returncode,0,a.stderr)
            self.assertEqual(a.stdout,b.stdout)
            result=json.loads(a.stdout)
            self.assertEqual(result['monthlyRequiredCells'],6)
            self.assertEqual(result['monthlyAcceptedCells'],0)
            self.assertEqual(result['months'],2)
            output=stage/'never-write.json'
            blocked=subprocess.run(command+['--require-monthly-complete','--output',str(output)],capture_output=True,text=True)
            self.assertNotEqual(blocked.returncode,0)
            self.assertFalse(output.exists())

    def test_explicit_pinned_official_local_baseline_drops_legacy_channel_references(self):
        import hashlib
        baseline = module.build()
        local = baseline['reports'][0]
        local['id'] = 'local-baseline-fixture'
        public = module.load(module.STAGE / '资料/公开来源/public-evidence.json')
        official = next(s for s in public['sources'] if s['source_id'] == 2)
        official_path = module.STAGE / '资料/公开来源' / official['archive']
        local_path = ROOT / local['path']
        binding = lambda p: {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        with tempfile.TemporaryDirectory(dir=module.STAGE / '核验/模板整改20261009/Code') as tmp:
            basepath = Path(tmp)/'baseline.json'
            basepath.write_text(json.dumps(baseline), encoding='utf-8')
            receipt = {**binding(basepath), 'sourceIds': ['public-2','changjiang-1'],
                'reportIds': [local['id']],
                'sourceArtifacts': {'public-2': binding(official_path), 'changjiang-1': binding(local_path)}}
            manifest = Path(tmp)/'sources.json'
            manifest.write_text(json.dumps({'schemaVersion': 'parent-source-manifest-1',
                'stageStart': '2026-09-01', 'stageEnd': '2026-10-09', 'sources': [], 'baseline': receipt}), encoding='utf-8')
            data = module.build(as_of='2026-10-09', parent_source_manifest=manifest)
            self.assertEqual({s['id'] for s in data['sources']}, {'public-2','changjiang-1'})
            self.assertEqual([r['id'] for r in data['reports']], [local['id']])
            event = next(e for e in data['events'] if e['id'] == 'fomc-statement')
            self.assertEqual(event['expectationSourceIds'], [])
            self.assertNotIn('高盛', event['expectation'])
            self.assertEqual(event['realitySourceIds'], ['public-2'])
            self.assertEqual(data['researchEvidence'], [])
            self.assertEqual(data['monthlyCoverage']['acceptedCells'], 0)

    def test_explicit_window_does_not_import_legacy_or_second_chapter_sources(self):
        with tempfile.TemporaryDirectory(dir=module.STAGE / '核验/模板整改20261009/Code') as tmp:
            stage = Path(tmp)
            manifest = stage / 'parent-sources.json'
            manifest.write_text(json.dumps({'schemaVersion': 'parent-source-manifest-1',
                'stageStart': '2026-09-01', 'stageEnd': '2026-10-09', 'sources': []}), encoding='utf-8')
            data = module.build(stage=stage, root=ROOT, as_of='2026-10-09', parent_source_manifest=manifest)
            self.assertEqual(data['asOf'], '2026-10-09')
            self.assertEqual(data['reports'], [])
            for field in ('researchEvidence', 'windResearchEvidence', 'wechatResearchEvidence'):
                self.assertEqual(data[field], [])
            self.assertNotIn('marketAnalysis', data)
            self.assertEqual([r['month'] for r in data['monthlyCoverage']['rows']], ['2026-09', '2026-10'])
            self.assertEqual(data['monthlyCoverage']['requiredCells'], 6)
            self.assertEqual(data['monthlyCoverage']['acceptedCells'], 0)

    def test_public_report_catalog_does_not_expose_absolute_archive_paths(self):
        data = module.build()
        for report in data['reports']:
            path = report.get('path', '')
            if path:
                self.assertFalse(Path(path).is_absolute() or (len(path) > 1 and path[1] == ':'), report.get('title'))

    def test_wind_verified_topics_and_geography_are_not_replaced_by_keyword_hits(self):
        manifest = module.load(module.STAGE / '报告/Wind/manifest.json')
        data = module.build()
        reports = {r['id']: r for r in data['reports'] if r.get('id', '').startswith('wind-pdf-')}
        for source in manifest['reports']:
            report = reports['wind-pdf-' + source['sha256'][:16]]
            self.assertTrue(set(source['themes_verified']) <= set(report['topics']))
            if source['date_precision'] == 'day':
                self.assertIn(source['scope'], report['scope'])
        channel = next(c for c in data['acquisition'] if c['provider'] == 'Wind')
        for theme in manifest['themes']:
            self.assertIn(f'{theme["keyword"]}：正文实质样本{theme["substantive_verified_pdf_count"]}', channel['detail'])

    def test_wind_audited_opinions_are_integrated_without_future_policy_results(self):
        data = module.build()
        audit = module.load(module.STAGE / '研究/wind-expectation-evidence.json')
        views = data.get('windResearchEvidence', [])
        self.assertEqual(views, audit['items'])
        self.assertEqual(len(views), 5)
        reports = {r['id']: r for r in data['reports'] if r.get('id', '').startswith('wind-pdf-')}
        for view in views:
            report = reports[view['reportId']]
            self.assertEqual(view['localPath'], report['path'])
            self.assertEqual(view['expressedAt'], report['date'])
            self.assertGreater(view['expressedAt'], '2026-09-16')
            self.assertTrue(view['pages'] and view['limitations'])
            if view['eventDate']:
                self.assertGreater(view['eventDate'], view['expressedAt'])
            else:
                self.assertIsNone(view['reality'])
        self.assertEqual(sum(v['reality'] is None for v in views), 2)

    def test_wind_partial_download_is_not_reported_as_six_theme_completion(self):
        manifest = module.load(module.STAGE / '报告/Wind/manifest.json')
        channel = next(c for c in module.build()['acquisition'] if c['provider'] == 'Wind')
        self.assertIn('部分', channel['status'])
        self.assertIn(str(manifest['unique_saved_pdf_count']) + '个PDF', channel['detail'])
        self.assertIn('非全量', channel['detail'])
        for theme in manifest['themes']:
            self.assertIn(f'{theme["keyword"]}：候选{theme["candidate_count"]} / 直存{theme["direct_saved_pdf_count"]}', channel['detail'])

    def test_wind_pdf_manifest_is_normalized_to_public_library_contract(self):
        manifest = module.load(module.STAGE / '报告/Wind/manifest.json')
        records = [r for r in module.build()['reports'] if r.get('id', '').startswith('wind-pdf-')]
        self.assertEqual(len(records), len(manifest['reports']))
        for record, source in zip(records, manifest['reports']):
            self.assertEqual(record['provider'], source['institution'] + ' · Wind')
            self.assertEqual(record['id'], 'wind-pdf-' + source['sha256'][:16])
            self.assertEqual(record['date'], source['verified_publication_date'] if source['date_precision'] == 'day' else None)
            self.assertTrue(record['scope'])
            self.assertTrue(record['dateBasis'])
            self.assertTrue((ROOT / record['path']).is_file())
            self.assertNotIn('first_page_preview', record)
            self.assertNotIn('per_page_text_path', record)

    def test_cpi_disinflation_interpretation_is_limited_to_core(self):
        event = next(e for e in module.build()['events'] if e['id'] == 'august-cpi')
        self.assertIn('核心同比放缓', event['interpretation'])
        self.assertIn('总同比持平', event['interpretation'])

    def test_final_transcript_is_not_backfilled_into_speech_day_information_set(self):
        data = module.build()
        source = next(s for s in data['sources'] if s['id'] == 'public-4')
        self.assertIs(source.get('historicalAsOfEligible'), False)
        self.assertIn('FINAL', source['dateBasis'])
        self.assertIn('9月24日', source['note'])

    def test_star_dates_use_filename_priority_and_keep_unconfirmed_body_dates(self):
        data = module.build()
        records = [r for r in data['reports'] if r.get('id', '').startswith('zsxq-')]
        self.assertEqual(len(records), 121)
        by_id = {r['id']: r for r in records}
        self.assertEqual(by_id['zsxq-048']['date'], '2026-09-19')
        self.assertEqual(by_id['zsxq-048']['postDate'], '2026-09-20')
        self.assertIs(by_id['zsxq-048']['dateConflict'], True)
        self.assertEqual(by_id['zsxq-121']['date'], '2026-08-31')
        self.assertTrue(by_id['zsxq-121']['scope'].startswith('区间前背景'))
        self.assertIn('filename_date_user_preferred', by_id['zsxq-048']['dateBasis'])
        self.assertTrue(all(r['publicationDate'] is None for r in records))
        self.assertEqual(sum(r['filenameDate'] is not None for r in records), 117)
        self.assertEqual(sum(r['dateConflict'] for r in records), 8)
        self.assertIsNone(by_id['zsxq-025']['date'])
        self.assertIsNone(by_id['zsxq-080']['date'])
        self.assertTrue(all(r.get('postDate') and r.get('dateBasis') for r in records))
        self.assertTrue(all((ROOT / r['path']).is_file() for r in records))
        view = next(v for v in data['researchEvidence'] if v['reportId'] == 'zsxq-048')
        self.assertEqual(view['expressedAt'], '2026-09-19')
        self.assertEqual(view['platformExpressedAt'], '2026-09-20')
        self.assertIn('文件名', view['dateBasis'])
        self.assertNotIn('不能把后者当正文日期', next(v for v in data['researchEvidence'] if v['reportId'] == 'zsxq-121')['limitations'])

    def test_audited_views_have_exact_report_and_reality_trace(self):
        data = module.build()
        evidence = data.get('researchEvidence', [])
        self.assertEqual(len(evidence), 12)
        self.assertTrue(all(e['reportTitle'] and e['localPath'] and e['pages'] for e in evidence))
        self.assertTrue(all(e['reality'] and e['status'] for e in evidence))
        self.assertTrue(all(e['dateBasis'] for e in evidence))

    def test_verified_market_paths_preserve_missing_values_and_publication_limits(self):
        data = module.build()
        paths = data.get('marketPaths', {})
        self.assertEqual(len(paths.get('series', [])), 3)
        self.assertEqual([sum(o['value'] is not None for o in s['observations']) for s in paths['series']], [21, 21, 18])
        self.assertTrue(all(o['historicalAsOfEligible'] is False for s in paths['series'][:2] for o in s['observations']))
        self.assertEqual(paths['cmeHistoricalImpliedPath']['observations'], [])

    def test_market_analysis_integrates_channels_with_resolvable_evidence(self):
        data = module.build()
        analysis = data.get('marketAnalysis')
        self.assertIsNotNone(analysis)
        self.assertGreaterEqual(len(analysis['sections']), 5)
        source_ids = {s['id'] for s in data['sources']}
        report_ids = {r.get('id') for r in data['reports']}
        cited_reports, cited_sources = set(), set()
        for section in analysis['sections']:
            for field in ('title', 'judgement', 'expectation', 'reality', 'mechanism', 'divergence', 'implication', 'validation'):
                self.assertTrue(section[field].strip(), (section['id'], field))
            self.assertTrue(set(section['sourceIds']) <= source_ids)
            self.assertTrue(set(section['reportIds']) <= report_ids)
            cited_reports.update(section['reportIds'])
            cited_sources.update(section['sourceIds'])
        self.assertTrue(any(r.startswith('zsxq-') for r in cited_reports))
        self.assertTrue(any(r.startswith('wind-pdf-') for r in cited_reports))
        self.assertTrue(any(s.startswith('changjiang-') for s in cited_sources))
        self.assertIn('不是市场共识', ''.join(analysis['limitations']))

    def test_wechat_original_and_expanded_bodies_are_integrated_without_replacing_old_views(self):
        data = module.build()
        raw = module.load(module.STAGE / '研究/wechat-expectation-evidence.json')['items']
        expanded = module.load(module.STAGE / '研究/wechat-expanded-expectation-evidence.json')['items']
        views = data.get('wechatResearchEvidence', [])
        self.assertEqual(views, raw + expanded)
        self.assertEqual(len(views), 22)
        records = {r.get('id'): r for r in data['reports'] if r.get('id', '').startswith('wechat-')}
        self.assertEqual(len(records), 13)
        books = module.load(module.STAGE / '研究/wechat-bibliography.json')['items']
        books += module.load(module.STAGE / '研究/wechat-expanded-bibliography.json')['items']
        self.assertEqual(set(records), {b['id'] for b in books})
        for view in views:
            report = records[view['reportId']]
            self.assertEqual(view['expressedAt'], report['date'])
            self.assertEqual(view['localPath'], report['path'])
            self.assertIs(report['historicalAsOfEligible'], False)
            self.assertTrue(all(str(p).startswith('p') for p in view['pages']))
        self.assertEqual(sum(v['reality'] is None for v in views), 19)
        channel = next(c for c in data['acquisition'] if c['provider'] == '微信公众号')
        self.assertIn('13篇', channel['detail'])
        self.assertIn('22条', channel['detail'])
        self.assertNotIn('正文保存0篇', channel['detail'])
        citations = set(r for s in data['marketAnalysis']['sections'] for r in s['reportIds'])
        self.assertTrue({b['id'] for b in module.load(module.STAGE / '研究/wechat-bibliography.json')['items']} <= citations)
        self.assertRegex(''.join(data['marketAnalysis']['limitations']), r'同(?:一)?机构同篇跨渠道不重复计票')

    def test_wechat_coverage_counts_actual_accounts_not_requested_names_or_forum_origins(self):
        data = module.build()
        coverage = data.get('wechatCoverage', {})
        self.assertEqual(coverage.get('totalArticles'), 13)
        self.assertEqual(coverage.get('totalOpinions'), 22)
        actual = {r['accountActual']: r['articleCount'] for r in coverage['actualAccounts']}
        self.assertEqual(actual, {'长江宏观经济研究': 5, '郭磊宏观茶座': 2, '中金点睛': 3,
                                  '泽平宏观': 1, '首席经济学家论坛': 2})
        audit = module.load(module.STAGE / '核验/微信公众号/扩展来源检索.json')['items']
        self.assertEqual([r['accountRequested'] for r in coverage['requestedAccounts']],
                         [r['accountRequested'] for r in audit])
        self.assertEqual(len(coverage['requestedAccounts']), 10)
        requested = {r['accountRequested']: r for r in coverage['requestedAccounts']}
        self.assertEqual(requested['中金宏观']['bodyObtainedCount'], 0)
        self.assertIn('中金点睛', requested['中金宏观']['status'])
        self.assertIn('非独立研究机构', ''.join(coverage['limitations']))
        for source in data['reports']:
            if source.get('accountActual') == '首席经济学家论坛':
                self.assertIn(source['researchOrigin'], ('华创证券', '华福证券'))
                self.assertIn('distributionType', source)

    def test_multi_account_synthesis_preserves_disagreements_conditions_and_prediction_horizons(self):
        data = module.build()
        topics = {s['id']: s for s in data['marketAnalysis']['sections']}
        expanded = module.load(module.STAGE / '研究/wechat-expanded-bibliography.json')['items']
        cited = {r for section in topics.values() for r in section['reportIds']}
        self.assertTrue({r['id'] for r in expanded} <= cited)
        self.assertIn('95美元', topics['policy-path']['divergence'])
        self.assertIn('2027年上半年', topics['inflation-vintages']['divergence'])
        self.assertIn('华创', topics['demand-supply']['divergence'])
        self.assertIn('华福', topics['demand-supply']['divergence'])
        self.assertIn('4.8%—5%', topics['treasury-curve']['divergence'])
        self.assertIn('年底', topics['treasury-curve']['divergence'])
        self.assertIn('不能', topics['treasury-curve']['divergence'])
        self.assertIn('96—98', topics['dollar-relative']['expectation'])
        self.assertIn('96—99', topics['dollar-relative']['expectation'])
        self.assertIn('日元', topics['dollar-relative']['divergence'])
        self.assertTrue(all(v['reality'] is None for v in data['wechatResearchEvidence'][6:]))

    def test_market_analysis_curve_numbers_match_the_archived_series(self):
        data = module.build()
        by_series = {s['id']: {o['date']: o['value'] for o in s['observations']} for s in data['marketPaths']['series']}
        short = by_series['treasury_cmt_2y']
        long = by_series['treasury_cmt_10y']
        analysis = next(s for s in data['marketAnalysis']['sections'] if s['id'] == 'treasury-curve')
        short_change = round((short['2026-09-30'] - short['2026-09-01']) * 100)
        long_change = round((long['2026-09-30'] - long['2026-09-01']) * 100)
        spread_start = round((long['2026-09-01'] - short['2026-09-01']) * 100)
        spread_end = round((long['2026-09-30'] - short['2026-09-30']) * 100)
        self.assertIn(f'{short_change}bp', analysis['reality'])
        self.assertIn(f'{long_change}bp', analysis['reality'])
        self.assertIn(f"{short['2026-09-01']:.2f}%→{short['2026-09-30']:.2f}%", analysis['reality'])
        self.assertIn(f"{long['2026-09-01']:.2f}%→{long['2026-09-30']:.2f}%", analysis['reality'])
        self.assertRegex(analysis['reality'], rf'{spread_start}bp(?:→|至){spread_end}bp')
        dollar = by_series['fed_nominal_broad_usd_JRXWTFB_N.B']
        change = (dollar['2026-09-25'] / dollar['2026-09-01'] - 1) * 100
        dollar_analysis = next(s for s in data['marketAnalysis']['sections'] if s['id'] == 'dollar-relative')
        self.assertIn(f'{change:.2f}%', dollar_analysis['reality'])

    def test_relevant_local_background_articles_are_not_omitted(self):
        data = module.build()
        local = [r for r in data['reports'] if '/长江宏观/' in r['path'].replace('\\', '/')]
        self.assertEqual(len(local), 16)  # 15 in-window + one previous-period background
        self.assertEqual(sum(r['scope'].startswith('区间内') for r in local), 15)


if __name__ == '__main__':
    unittest.main()
