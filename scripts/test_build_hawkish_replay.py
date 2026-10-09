"""Contract tests for the new closed-stage replay assembler; no online facts mocked."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name('build_hawkish_replay.py')

def get_builder():
    if not SCRIPT.exists():
        return None
    spec = importlib.util.spec_from_file_location('hawk_builder', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class HawkishReplayTests(unittest.TestCase):
    def test_explicit_reviewed_research_replaces_only_second_article_current_analysis(self):
        import inspect
        builder=get_builder()
        self.assertIn('reviewed_research_manifest',inspect.signature(builder.build).parameters,
                      'Explicit reviewed research admission is not implemented')
        root=SCRIPT.parents[1]
        stage=root/'美国宏观复盘/降息起步后的双向政策时代/2026-01_2026-08'
        manifest=stage/'研究/parent-reviewed-research-20261009-manifest.json'
        new_sources=json.loads((stage/'研究/parent-sources-20261009-zsxq-completion03.json').read_text(encoding='utf-8'))
        descriptors=list(builder.DEFAULT_SOURCES)+new_sources['sources']
        first=root/'src/data/historyReplay.json'
        before=hashlib.sha256(first.read_bytes()).hexdigest()
        baseline=builder.build(stage,root,allow_partial=True,parent_sources=descriptors)
        data=builder.build(stage,root,allow_partial=True,parent_sources=descriptors,reviewed_research_manifest=manifest)
        self.assertEqual(data['monthlyCoverage']['acceptedCells'],24)
        self.assertTrue(data['monthlyCoverage']['complete'])
        self.assertEqual(len(data['monthlyReplay']),8)
        self.assertEqual(len(data['revisionChains']),4)
        self.assertEqual(sum(len(data[k]) for k in ('researchEvidence','windResearchEvidence','wechatResearchEvidence')),39)
        self.assertNotIn('待重新核验',data['marketAnalysis']['conclusion'])
        self.assertEqual(data['realityComparisons'],baseline['realityComparisons'])
        self.assertEqual(data['localResearchEvidence'],baseline['localResearchEvidence'])
        self.assertEqual(hashlib.sha256(first.read_bytes()).hexdigest(),before)
        ids={r['id'] for r in data['reports']}
        for m in data['monthlyReplay']+data['marketAnalysis']['sections']:
            self.assertLessEqual(set(m['reportIds']),ids)
        reviewed_ids=set(data['reviewedResearch']['opinionIds'])
        for chain in data['revisionChains']:
            self.assertLessEqual(set(chain['opinionIds']),reviewed_ids)
        public=builder.publication_snapshot(data,root)
        for k in ('researchEvidence','windResearchEvidence','wechatResearchEvidence'):
            self.assertTrue(all(not o['historicalAsOfEligible'] and o['firstAvailableDate'] is None for o in public[k]))
        serialized=json.dumps(public,ensure_ascii=False)
        for denied in ('documentPath','contextSHA256','parserVersions','inputPins','privateAuditOnly','FCCNN88','@spdbi.com','E:\\\\HermesProject'):
            self.assertNotIn(denied,serialized)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / 'stage'
        self.stage.mkdir()
        self.parent_sources = []
        self.builder = get_builder()
        self.assertIsNotNone(self.builder, 'New independent-stage assembler is not implemented')

    def put(self, name, value):
        path = self.stage / '研究' / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def put_parent(self, report, publication_date=None):
        """TEST ONLY genuine PDF plus explicit parent receipt; never legacy flags."""
        import pymupdf
        record = dict(report)
        path = Path(record.get('path') or self.stage / (record['id'] + '.pdf'))
        if not path.is_absolute():
            path = self.stage / path
        path.parent.mkdir(parents=True, exist_ok=True)
        pdf = pymupdf.open()
        page = pdf.new_page()
        page.insert_text((40, 40), 'TEST ONLY original body 00:00:00 ' + record['id'])
        path.write_bytes(pdf.tobytes())
        pdf.close()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        channel = record['channel']
        day = record.get('filenameDate') or record.get('publicationDate') or '2026-01-12'
        record.update(path=str(path), sha256=digest, bytes=path.stat().st_size, pageCount=1,
                      independentWorkId='test-work:' + digest, filenameDate=day,
                      publicationDate=day if channel == 'Wind' else publication_date,
                      title=record.get('title', 'TEST ONLY original PDF'), institution='TEST ONLY institution',
                      originalFilename=path.name, documentId=record['id'],
                      verifiedPublicationMonth=day[:7], publicationDatePrecision='day',
                      versionType='original_audio_transcript_pdf', encrypted=False,
                      countsTowardMonthlyMinimum=True)
        source = self.stage / (record['id'] + '-source.json')
        topic = 'https://wx.zsxq.com/group/28888112822211/topic/TEST-ONLY-' + record['id']
        source.write_text(json.dumps({'topicURL': topic, 'renderedTopic': {
            'text': '#调研纪要 TEST ONLY ' + path.name}}, ensure_ascii=False), encoding='utf-8')
        record.update(topicURL=topic, topicDOMEvidence=str(source))
        parent = {'path': str(path), 'sha256': digest, 'bytes': record['bytes'], 'pageCount': 1,
                  'independentTagAndOriginalVersionChecked': True, 'allDualParserPageShaMatch': True,
                  'accepted': True, 'allPageTextAndContentHashesMatch': True}
        if record['channel'] in ('微信', '微信公众号'):
            from html import escape
            day = report['publicationDate']
            record['publicationDate'] = day
            account = record.get('accountActual', 'TEST ACCOUNT')
            body = 'TEST ONLY original published article 美国美联储美元美债。' * 12
            body_path = self.stage / (record['id'] + '-body.txt')
            body_path.write_text(body, encoding='utf-8')
            digest = hashlib.sha256(body_path.read_bytes()).hexdigest()
            url = 'https://mp.weixin.qq.com/s/TEST-ONLY-' + record['id']
            year, month, date_day = map(int, day.split('-'))
            header = f'{year}年{month}月{date_day}日 12:00'
            html = (f'<meta property="og:url" content="{url}"><h1 id="activity-name">{escape(record["title"])}</h1>'
                    f'<b id="js_name">{escape(account)}</b><time id="publish_time">{header}</time>'
                    f'<div id="js_content">{escape(body)}</div>')
            raw = self.stage / (record['id'] + '.html')
            raw.write_text(html, encoding='utf-8')
            paragraphs = self.stage / (record['id'] + '-paragraphs.json')
            paragraphs.write_text(json.dumps([{'id': 'p1', 'text': body, 'sha256': digest}]), encoding='utf-8')
            record.update(path=None, sha256=None, bytes=body_path.stat().st_size, bodyPath=str(body_path), bodySHA256=digest, bodyBytes=body_path.stat().st_size,
                          account=account, rawHtmlPath=str(raw), rawHTMLSHA256=hashlib.sha256(raw.read_bytes()).hexdigest(),
                          rawHTMLBytes=raw.stat().st_size, paragraphsPath=str(paragraphs), paragraphCount=1,
                          canonicalOriginalUrl=url, downloadedThisRun=True)
            parent = {'bodyPath': str(body_path), 'bodySHA256': digest, 'normalizedBodySHA256': digest,
                      'account': account, 'date': day, 'allHeaderBodyAndParagraphChecksPassed': True}
            channel = '微信公众号'
        else:
            channel = record['channel']
            record.setdefault('downloadedThisRun', True)
        book_path = self.stage / '研究' / (record['id'] + '-parent-book.json')
        book_path.parent.mkdir(exist_ok=True)
        book_path.write_text(json.dumps({'articles': [record]}), encoding='utf-8')
        proof = self.stage / (record['id'] + '-parent-ledger.json')
        proof.write_text(json.dumps({'files': [parent]}), encoding='utf-8')
        self.parent_sources.append({'channel': channel, 'canonicalSourcePath': str(book_path),
            'sourceSHA256': hashlib.sha256(book_path.read_bytes()).hexdigest(),
            'searchExecuted': True, 'parentLedgers': [{'path': str(proof),
                'sha256': hashlib.sha256(proof.read_bytes()).hexdigest()}]})
        return record

    def build_fixture(self, allow_partial=True):
        return self.builder.build(self.stage, self.root, allow_partial=allow_partial,
                                  parent_sources=self.parent_sources or None)

    def test_missing_inputs_are_explicit_pending_not_real_evidence(self):
        data = self.build_fixture()
        self.assertEqual(data['startDate'], '2026-01-01')
        self.assertEqual(data['endDate'], '2026-08-31')
        self.assertEqual(data['asOf'], '2026-08-31')
        self.assertEqual(data['events'], [])
        self.assertEqual(data['reports'], [])
        self.assertTrue(all('待' in item['status'] for item in data['acquisition']))
        with self.assertRaises(ValueError):
            self.build_fixture(allow_partial=False)

    def test_sources_after_closed_stage_are_rejected(self):
        self.put('official-evidence.json', {'sources': [{'id': 'test-future', 'date': '2026-09-01'}], 'events': []})
        with self.assertRaisesRegex(ValueError, 'after cutoff'):
            self.build_fixture()

    def test_unknown_reality_is_not_filled_and_local_channel_is_distinct(self):
        self.put('local-bibliography.json', {'articles': [{'id': 'fixture', 'title': 'TEST ONLY', 'provider': 'test', 'path': '', 'publicationDate': None}]})
        self.put('local-expectation-evidence.json', {'items': [{'reportId': 'fixture', 'claim': 'TEST ONLY', 'reality': None, 'eventId': None}]})
        data = self.build_fixture()
        self.assertEqual(data['researchEvidence'], [])
        self.assertIsNone(data['localResearchEvidence'][0]['reality'])
        self.assertIsNone(data['localResearchEvidence'][0]['eventId'])
        self.assertFalse(data['localResearchEvidence'][0].get('historicalAsOfEligible', True))
        self.assertIsNone(data['localResearchEvidence'][0]['firstAvailableDate'])
        self.assertEqual(data['localResearchEvidence'][0]['sourceQuality'], {'status': 'unknown'})
        self.assertFalse(data['reports'][0]['historicalAsOfEligible'])

    def test_printed_date_without_first_availability_cannot_promote_historical_report(self):
        report = {'id': 'test-wind', 'channel': 'Wind', 'publicationDate': '2026-01-29',
                  'firstAvailableDate': None, 'historicalAsOfEligible': True}
        self.put('channel-monthly-bibliography.json', {'articles': [report]})
        self.put_parent(report)
        data = self.build_fixture()
        self.assertFalse(data['reports'][0]['historicalAsOfEligible'])
        self.assertFalse(next(s for s in data['sources'] if s['id'] == 'test-wind')['historicalAsOfEligible'])
        raw = json.loads((self.stage / '研究/channel-monthly-bibliography.json').read_text(encoding='utf-8'))
        self.assertTrue(raw['articles'][0]['historicalAsOfEligible'])

    def test_later_pdf_batch_is_additive_and_keeps_channel_dates_distinct(self):
        payload = b'%PDF-1.7\nTEST ONLY original archive for monthly integration.\n'
        records = []
        for channel, month, day in [('Wind', '02', '11'), ('知识星球', '05', '19'), ('知识星球', '07', '30')]:
            archive = self.stage / f'{channel}-{month}.pdf'
            archive.write_bytes(payload + month.encode())
            record = {'id': f'{channel}-{month}', 'channel': channel, 'path': str(archive),
                      'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                      'date': f'2026-{month}-{day}', 'publicationDate': f'2026-{month}-{day}' if channel == 'Wind' else None,
                      'filenameDate': f'2026-{month}-{day}' if channel == '知识星球' else None,
                      'historicalAsOfEligible': True, 'firstAvailableDate': None}
            records.append(record)
        self.put('channel-monthly-20261007-bibliography.json', {'articles': records})
        for record in records:
            self.put_parent(record)
        data = self.build_fixture()
        self.assertEqual({report['id'] for report in data['reports']}, {record['id'] for record in records})
        self.assertEqual(data['monthlyCoverage']['coveredCells'], 3)
        self.assertTrue(all(not report['historicalAsOfEligible'] for report in data['reports']))

    def test_wind_gui_incremental_archive_and_partial_receipt_are_both_integrated(self):
        archive = self.stage / '报告' / 'wind-march.pdf'
        archive.parent.mkdir()
        archive.write_bytes(b'%PDF-1.7\nTEST ONLY: Wind monthly archive fixture\n')
        old_archive = self.stage / '报告' / 'old-wind.pdf'
        old_archive.write_bytes(b'%PDF-1.7\nTEST ONLY: older Wind archive fixture\n')
        self.put('channel-monthly-bibliography.json', {'articles': [{
            'id': 'old-wind', 'channel': 'Wind', 'path': '报告/old-wind.pdf',
            'publicationDate': '2026-01-29', 'downloadedThisRun': True,
            'sha256': hashlib.sha256(old_archive.read_bytes()).hexdigest()}]})
        report = {'id': 'wind-march-gui', 'channel': 'Wind', 'path': '报告/wind-march.pdf',
                  'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'publicationDate': '2026-03-20', 'firstAvailableDate': None,
                  'historicalAsOfEligible': False}
        self.put('channel-monthly-20261007-wind-gui-incremental.json', {'articles': [report]})
        self.put_parent(report)
        folder = self.stage / '核验/逐月补采20261007-晚间'
        folder.mkdir(parents=True)
        (folder / 'wind-rpp-monthly-receipts-incremental.json').write_text(json.dumps({
            'normalGuiAcquisitionAfter': '2026-10-07T22:54:41+08:00', 'rows': [
            {'month': '2026-03', 'searchExecutedThisRun': True, 'searchComplete': False,
             'resultCountTitle': 20, 'resultCountFulltext': 264, 'gap': '仅审首屏'}]}), encoding='utf-8')
        (folder / 'gui-resume-checkpoint-test.json').write_text(json.dumps({
            'resumeAttempt': {'status': 'blocked_windows_lock', 'observedAt': '2026-10-07 17:38 +08:00',
                              'reason': 'TEST OLD LOCK'}}), encoding='utf-8')
        data = self.build_fixture()
        self.assertEqual(next(r['path'] for r in data['reports'] if r['id'] == 'wind-march-gui'),
                         'stage/报告/wind-march.pdf')
        cell = data['monthlyCoverage']['rows'][2]['channels']['Wind']
        self.assertEqual(cell['bodyCount'], 1)
        self.assertTrue(cell['searchExecuted'])
        self.assertFalse(cell['searchComplete'])
        self.assertFalse(cell['accepted'])
        self.assertIn('仅审首屏', cell['reason'])
        wind = next(entry for entry in data['acquisition'] if entry['provider'] == 'Wind')
        self.assertIn('新增下载1份', wind['detail'])
        self.assertNotIn('TEST OLD LOCK', wind['detail'])
        self.assertNotIn('受阻', wind['status'])

    def test_later_pdf_opinions_are_additive_without_promoting_unknown_availability(self):
        reports = [
            {'id': 'wind-feb', 'channel': 'Wind', 'publicationDate': '2026-02-11'},
            {'id': 'star-may', 'channel': '知识星球', 'filenameDate': '2026-05-19'},
            {'id': 'star-jul', 'channel': '知识星球', 'publicationDate': '2026-07-30'},
        ]
        self.put('channel-monthly-20261007-bibliography.json', {'articles': reports})
        for report in reports:
            self.put_parent(report)
        items = [{'id': f'view-{report["id"]}', 'reportId': report['id'],
                  'channel': report['channel'], 'expressedAt': report.get('publicationDate'),
                  'firstAvailableDate': None, 'historicalAsOfEligible': False,
                  'eventId': None, 'reality': None} for report in reports]
        self.put('channel-monthly-20261007-expectation-evidence.json', {'items': items})
        data = self.build_fixture()
        self.assertEqual([v['id'] for v in data['windResearchEvidence']], ['view-wind-feb'])
        self.assertEqual([v['id'] for v in data['researchEvidence']], ['view-star-may', 'view-star-jul'])
        self.assertTrue(all(not v['historicalAsOfEligible'] and v['reality'] is None
                            for v in data['windResearchEvidence'] + data['researchEvidence']))
        self.assertIsNone(data['researchEvidence'][0]['expressedAt'])

    def test_cdp_pdf_batches_add_verified_bodies_but_exclude_unrelated_guide(self):
        batches = [
            ('channel-monthly-20261008-zsxq-cdp-first-bibliography.json', 'cdp-june', '2026-06-08', True),
            ('channel-monthly-20261008-zsxq-cdp-batch02-bibliography.json', 'cdp-feb', '2026-02-01', True),
            ('channel-monthly-20261008-zsxq-cdp-parent03-bibliography.json', 'cdp-april', '2026-04-30', True),
        ]
        for filename, report_id, day, relevant in batches:
            archive = self.stage / (report_id + '.pdf')
            archive.write_bytes(b'%PDF-1.7\nTEST ONLY CDP integration fixture ' + report_id.encode())
            report = {'id': report_id, 'channel': '知识星球', 'title': 'TEST ONLY',
                      'path': str(archive), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                      'bytes': archive.stat().st_size, 'pageCount': 1, 'filenameDate': day,
                      'publicationDate': None, 'bodyTitleVerified': True,
                      'archiveBytesAndAllPagesVerified': True, 'usMacroRelevant': relevant,
                      'originalInstitutionalReportVerified': False, 'historicalAsOfEligible': True,
                      'firstAvailableDate': None, 'note': 'TEST ONLY transcript identity pending'}
            records = [report]
            if report_id == 'cdp-feb':
                records.append({**report, 'id': 'excluded-guide', 'filenameDate': '2026-01-29',
                                'usMacroRelevant': False, 'acceptedUsMacroReservation': False})
            self.put(filename, {'articles': records})
            self.put_parent(report)
        data = self.build_fixture()
        self.assertEqual({r['id'] for r in data['reports']}, {'cdp-june', 'cdp-feb', 'cdp-april'})
        self.assertTrue(all(r['downloadedThisRun'] for r in data['reports']))
        self.assertTrue(all(not r['historicalAsOfEligible'] for r in data['reports']))
        self.assertTrue(all(not r['sourceQuality']['institutionIdentityIndependentlyVerified'] for r in data['reports']))
        self.assertEqual(data['monthlyCoverage']['coveredCells'], 3)
        self.assertEqual(data['monthlyCoverage']['acceptedCells'], 0)
        self.assertEqual(data['monthlyCoverage']['rows'][0]['channels']['知识星球']['bodyCount'], 0)
        self.assertEqual(data['researchEvidence'], [])

    def test_latest_cdp_download_count_does_not_include_previous_batch_flags(self):
        old = self.stage / 'old.pdf'
        new = self.stage / 'new.pdf'
        old.write_bytes(b'%PDF-1.7\nTEST ONLY previous download')
        new.write_bytes(b'%PDF-1.7\nTEST ONLY current CDP download')
        self.put('channel-bibliography.json', {'articles': [{
            'id': 'old-star', 'channel': '知识星球', 'path': str(old),
            'sha256': hashlib.sha256(old.read_bytes()).hexdigest(),
            'filenameDate': '2026-05-19', 'downloadedThisRun': True}]})
        self.put('channel-monthly-20261008-zsxq-cdp-first-bibliography.json', {'articles': [{
            'id': 'new-star', 'channel': '知识星球', 'path': str(new),
            'sha256': hashlib.sha256(new.read_bytes()).hexdigest(), 'pageCount': 1,
            'filenameDate': '2026-06-08', 'bodyTitleVerified': True,
            'archiveBytesAndAllPagesVerified': True}]})
        receipt = self.stage / '核验/逐月补采20261008T180000-CDP/cdp-monthly-audit.json'
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({'rows': [{'month': '2026-06', 'channel': '知识星球',
            'searchExecuted': True, 'searchComplete': False, 'status': 'acquired_partial_cdp'}]}), encoding='utf-8')
        data = self.build_fixture()
        entry = next(a for a in data['acquisition'] if a['provider'] == '知识星球')
        # These agent-flag-only CDP candidates have no parent receipt.
        self.assertIn('新增下载0份', entry['detail'])
        self.assertEqual(data['reports'], [])
        self.assertEqual(data['monthlyCoverage']['acceptedCells'], 0)

    def test_wind_gui_verified_opinions_are_additive_but_not_historical(self):
        archive = self.stage / 'wind.pdf'
        archive.write_bytes(b'%PDF-1.7\nTEST ONLY: evidence integration fixture')
        self.put('channel-monthly-20261007-wind-gui-incremental.json', {'articles': [
            {'id': 'wind-gui', 'channel': 'Wind', 'path': str(archive),
             'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
             'publicationDate': '2026-03-20', 'firstAvailableDate': None}]})
        self.put_parent({'id': 'wind-gui', 'channel': 'Wind', 'path': str(archive), 'publicationDate': '2026-03-20'})
        self.put('channel-monthly-20261007-wind-gui-expectation-evidence.json', {'items': [
            {'id': 'wind-gui-forecast', 'reportId': 'wind-gui', 'channel': 'Wind',
             'claim': 'TEST ONLY conditional prediction', 'claimType': 'conditional_forecast',
             'firstAvailableDate': None, 'historicalAsOfEligible': False,
             'eventId': None, 'reality': None},
            {'id': 'wind-gui-pricing', 'reportId': 'wind-gui', 'channel': 'Wind',
             'claim': 'TEST ONLY market snapshot', 'claimType': 'market_pricing_snapshot',
             'firstAvailableDate': None, 'historicalAsOfEligible': False,
             'eventId': None, 'reality': None}]})
        data = self.build_fixture()
        self.assertEqual([item['id'] for item in data['windResearchEvidence']],
                         ['wind-gui-forecast', 'wind-gui-pricing'])
        self.assertTrue(all(not item['historicalAsOfEligible'] and item['reality'] is None
                            for item in data['windResearchEvidence']))
        self.assertEqual(data['researchEvidence'], [])

    def test_wind_gui_opinion_cannot_use_unlisted_or_reused_report(self):
        archive = self.stage / 'wind.pdf'
        archive.write_bytes(b'%PDF-1.7\nTEST ONLY')
        self.put('channel-monthly-20261007-wind-gui-incremental.json', {'articles': [
            {'id': 'wind-gui', 'channel': 'Wind', 'path': str(archive),
             'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
             'sameUnderlyingReportAs': '报告/origin.pdf'}]})
        origin = self.stage / '报告/origin.pdf'
        origin.parent.mkdir()
        origin.write_bytes(b'%PDF-1.7\nTEST ONLY origin')
        self.put('channel-monthly-20261007-wind-gui-expectation-evidence.json', {'items': [
            {'id': 'duplicate-vote', 'reportId': 'wind-gui', 'channel': 'Wind',
             'firstAvailableDate': None, 'historicalAsOfEligible': False}]})
        self.put('local-bibliography.json', {'articles': [
            {'id': 'origin', 'path': '报告/origin.pdf',
             'sha256': hashlib.sha256(origin.read_bytes()).hexdigest()}]})
        data = self.build_fixture()
        self.assertEqual(data['windResearchEvidence'], [])
        self.assertNotIn('wind-gui', {r['id'] for r in data['reports']})

    def test_archive_hash_mismatch_is_rejected(self):
        archived = self.stage / 'test-only.pdf'
        archived.write_bytes(b'TEST FIXTURE ONLY, not a claimed PDF')
        self.put('local-bibliography.json', {'articles': [{'id': 'fixture', 'path': str(archived), 'sha256': hashlib.sha256(b'wrong').hexdigest()}]})
        with self.assertRaisesRegex(ValueError, 'SHA'):
            self.build_fixture()

    def test_duplicate_article_identity_is_rejected(self):
        self.put('local-bibliography.json', {'articles': [{'id': 'fixture'}, {'id': 'fixture'}]})
        with self.assertRaisesRegex(ValueError, 'Duplicate report'):
            self.build_fixture()

    def test_stage_relative_archives_are_resolved_without_changing_source_metadata(self):
        archived = self.stage / '报告' / 'fixture.pdf'
        archived.parent.mkdir()
        archived.write_bytes(b'TEST ARCHIVE ONLY')
        self.put('local-bibliography.json', {'articles': [{'id': 'fixture',
            'path': '报告/fixture.pdf', 'sha256': hashlib.sha256(archived.read_bytes()).hexdigest()}]})
        data = self.build_fixture()
        self.assertEqual(data['reports'][0]['path'], 'stage/报告/fixture.pdf')
        self.assertEqual(data['reports'][0]['archiveRelativePath'], '报告/fixture.pdf')

    def test_verification_only_calendar_is_not_a_retrospective_source(self):
        self.put('official-evidence.json', {'sources': [{'id': 'calendar', 'date': '2026-10-02', 'scope': 'verification-only'}], 'events': []})
        data = self.build_fixture()
        self.assertEqual(data['sources'], [])

    def test_blocked_channel_audit_is_not_reported_as_success(self):
        self.put('channel-bibliography.json', {'articles': [], 'audit': [{'channel': 'Wind',
            'status': 'blocked_before_historical_search', 'reason': 'TEST GUI BLOCKED', 'searchExecuted': False, 'matchedCount': None}]})
        data = self.build_fixture()
        wind = next(a for a in data['acquisition'] if a['provider'] == 'Wind')
        self.assertIn('受阻', wind['status'])
        self.assertIn('TEST GUI BLOCKED', wind['detail'])

    def test_retrospective_event_has_the_later_sources_availability_date(self):
        self.put('official-evidence.json', {'sources': [{'id': 'official', 'date': '2026-05-22'}],
            'events': [{'id': 'nomination', 'date': '2026-03-04', 'realitySourceIds': ['official']}]})
        data = self.build_fixture()
        self.assertEqual(data['events'][0]['availableFrom'], '2026-05-22')

    def test_cross_channel_sha_identity_is_not_counted_as_independent_documents(self):
        archived = self.stage / 'fixture.pdf'
        archived.write_bytes(b'TEST DOCUMENT ONLY')
        sha = self.put_parent({'id': 'star', 'channel': '知识星球', 'path': str(archived), 'filenameDate': '2026-01-12'})['sha256']
        self.put('local-bibliography.json', {'articles': [{'id': 'local', 'path': str(archived), 'sha256': sha}]})
        self.put('channel-bibliography.json', {'articles': [{'id': 'star', 'channel': '知识星球', 'path': str(archived), 'sha256': sha}]})
        data = self.build_fixture()
        self.assertEqual(data['archiveCoverage']['channelEntries'], 2)
        self.assertEqual(data['archiveCoverage']['uniqueDocuments'], 1)
        self.assertEqual(data['reports'][1]['sharedDocumentWith'], ['local'])

    def test_different_sha_text_verified_alias_preserves_origin_without_another_vote(self):
        local_path = self.stage / 'test-local.pdf'
        wind_path = self.stage / 'test-wind.pdf'
        local_path.write_bytes(b'TEST ONLY: original archive')
        wind_path.write_bytes(b'TEST ONLY: watermarked archive')
        local_sha = hashlib.sha256(local_path.read_bytes()).hexdigest()
        wind_sha = self.put_parent({'id': 'wind', 'channel': 'Wind', 'path': str(wind_path), 'publicationDate': '2026-01-12'})['sha256']
        self.put('local-bibliography.json', {'articles': [{'id': 'local', 'path': str(local_path), 'sha256': local_sha}]})
        self.put('channel-monthly-bibliography.json', {'articles': [
            {'id': 'wind', 'channel': 'Wind', 'path': str(wind_path), 'sha256': wind_sha}]})
        self.put('local-expectation-evidence.json', {'items': [{'id': 'local-view', 'reportId': 'local', 'claim': 'TEST ONLY'}]})
        alias = {'reportId': 'wind', 'originReportId': 'local', 'sha256': wind_sha,
                 'originSha256': local_sha, 'sameUnderlyingReport': True,
                 'countsAsIndependentDocument': False, 'countsAsAdditionalOpinion': False,
                 'duplicateOfEvidenceIds': ['local-view'], 'note': 'TEST ONLY: text layer verified, images not compared'}
        self.put('channel-monthly-parent-expectation-evidence.json', {'items': [], 'sourceAliases': [alias]})
        data = self.build_fixture()
        wind = next(report for report in data['reports'] if report['id'] == 'wind')
        self.assertEqual(wind['originReportId'], 'local')
        self.assertEqual(wind['sharedDocumentWith'], ['local'])
        self.assertFalse(wind['countsAsIndependentDocument'])
        self.assertEqual(data['windResearchEvidence'], [])
        self.assertEqual(data['archiveCoverage']['uniqueDocuments'], 2)
        self.assertEqual(data['archiveCoverage']['textVerifiedAliasCount'], 1)
        self.assertEqual(data['sourceAliases'], [alias])

    def test_market_sources_keep_retrieval_date_and_are_retrospective_only(self):
        self.put('market-paths.json', {'series': [], 'sources': [{'id': 'data', 'url': 'https://example.com/data', 'retrievedAt': '2026-10-02T00:00:00Z'}]})
        data = self.build_fixture()
        source = next(s for s in data['sources'] if s['id'] == 'data')
        self.assertEqual(source['date'], '2026-10-02')
        self.assertTrue(source['retrospectiveOnly'])
        self.assertFalse(source['historicalAsOfEligible'])

    def test_synthesis_keeps_verification_only_sources_in_archive_not_presentation(self):
        self.put('official-evidence.json', {'sources': [{'id': 'calendar', 'date': '2026-10-02', 'scope': 'verification-only'}], 'events': []})
        original = {'conclusion': 'TEST[calendar]', 'sections': [{'id': 'policy', 'sourceIds': ['calendar'], 'reportIds': []}],
                    'references': [{'id': 'calendar'}]}
        self.put('market-analysis.json', original)
        data = self.build_fixture()
        self.assertEqual(data['marketAnalysis']['sections'][0]['sourceIds'], [])
        self.assertEqual(data['marketAnalysis']['references'], [])
        self.assertEqual(data['marketAnalysis']['conclusion'], 'TEST')
        self.assertEqual(json.loads((self.stage / '研究/market-analysis.json').read_text(encoding='utf-8')), original)

    def test_pairs_are_separate_from_original_opinions_and_enrich_event_expectations(self):
        self.put('official-evidence.json', {'sources': [{'id': 'official', 'date': '2026-01-28'}],
            'events': [{'id': 'event', 'date': '2026-01-28', 'expectation': '', 'realitySourceIds': ['official']}]})
        self.put('local-bibliography.json', {'articles': [{'id': 'report', 'publicationDate': '2026-01-21'}]})
        self.put('local-expectation-evidence.json', {'items': [{'reportId': 'report', 'reality': None}]})
        self.put('expectation-reality-pairs.json', {'pairs': [{'id': 'pair', 'reportId': 'report', 'eventId': 'event',
            'eventDate': '2026-01-28', 'assessmentAsOf': '2026-08-31', 'realitySourceIds': ['official']}],
            'eventExpectations': [{'eventId': 'event', 'text': 'TEST INDIVIDUAL FORECAST', 'sourceIds': ['report'], 'historicalAsOfEligible': False}]})
        data = self.build_fixture()
        self.assertEqual(len(data['realityComparisons']), 1)
        self.assertEqual(data['events'][0]['expectation'], 'TEST INDIVIDUAL FORECAST')
        self.assertEqual(data['events'][0]['expectationSourceIds'], ['report'])
        self.assertFalse(data['events'][0]['historicalAsOfEligible'])
        self.assertFalse(data['realityComparisons'][0].get('historicalAsOfEligible', True))
        self.assertIsNone(data['realityComparisons'][0]['firstAvailableDate'])
        self.assertIsNone(data['localResearchEvidence'][0]['reality'])

    def test_monthly_coverage_is_explicit_and_missing_months_cannot_be_complete(self):
        data = self.build_fixture()
        self.assertEqual(data['monthlyCoverage']['requiredCells'], 24)
        self.assertEqual(data['monthlyCoverage']['coveredCells'], 0)
        self.assertFalse(data['monthlyCoverage']['complete'])

    def test_monthly_wechat_bodies_and_original_opinions_are_additive(self):
        archived = self.stage / 'fixture-body.txt'
        archived.write_text('TEST ONLY: text-body archive fixture, not actual research.', encoding='utf-8')
        report = {'id': 'test-wechat', 'channel': '微信', 'provider': 'TEST ONLY',
            'title': 'TEST ONLY', 'path': str(archived), 'accountActual': 'TEST ACCOUNT',
            'publicationDate': '2026-01-08', 'dateBasis': 'official_header_test_only',
            'sha256': hashlib.sha256(archived.read_bytes()).hexdigest()}
        self.put('wechat-monthly-bibliography.json', {'articles': [report]})
        self.put_parent(report)
        self.put('wechat-monthly-expectation-evidence.json', {'items': [
            {'reportId': 'test-wechat', 'channel': '微信', 'claim': 'TEST ONLY', 'reality': None}]})
        data = self.build_fixture()
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(len(data['wechatResearchEvidence']), 1)
        self.assertIsNone(data['wechatResearchEvidence'][0]['reality'])
        self.assertEqual(data['wechatCoverage']['totalArticles'], 1)
        self.assertEqual(data['monthlyCoverage']['coveredCells'], 1)

    def test_fresh_monthly_receipt_replaces_stale_zero_download_summary(self):
        archived = self.stage / 'test-new-wind.pdf'
        archived.write_bytes(b'%PDF-1.7\nTEST ONLY: archive-integrity fixture')
        report = {'id': 'new-wind', 'channel': 'Wind', 'path': str(archived),
            'sha256': hashlib.sha256(archived.read_bytes()).hexdigest(),
            'publicationDate': '2026-01-29', 'downloadedThisRun': True}
        self.put('channel-bibliography.json', {'articles': [], 'audit': [
            {'channel': 'Wind', 'status': 'blocked', 'downloadedCount': 0, 'reason': 'TEST STALE NO PDF'}]})
        self.put('channel-monthly-bibliography.json', {'articles': [report]})
        self.put_parent(report)
        audit = self.stage / '核验/逐月补采20261002/gui-monthly-audit.json'
        audit.parent.mkdir(parents=True)
        audit.write_text(json.dumps({'rows': [{'month': '2026-01', 'channel': 'Wind',
            'searchExecuted': True, 'status': 'acquired_limited_sample', 'reason': 'TEST FRESH RECEIPT'}]}), encoding='utf-8')
        data = self.build_fixture()
        wind = next(row for row in data['acquisition'] if row['provider'] == 'Wind')
        self.assertIn('新增下载1份', wind['detail'])
        self.assertIn('TEST FRESH RECEIPT', data['monthlyCoverage']['rows'][0]['channels']['Wind']['reason'])
        self.assertNotIn('TEST STALE NO PDF', wind['detail'])
        self.assertNotIn('全部补齐', wind['status'])

    def test_existing_star_monthly_selection_is_not_a_duplicate_report(self):
        archived = self.stage / 'test-star.pdf'
        archived.write_bytes(b'%PDF-1.7\nTEST ONLY: archive-integrity fixture')
        report = {'id': 'star', 'channel': '知识星球', 'path': str(archived),
            'sha256': hashlib.sha256(archived.read_bytes()).hexdigest(),
            'filenameDate': '2026-08-06', 'publicationDate': None,
            'dateBasis': 'filename_date_user_preferred'}
        self.put('channel-bibliography.json', {'articles': [report]})
        self.put('channel-monthly-bibliography.json', {'articles': [{**report, 'reuse': True}]})
        self.put_parent(report)
        data = self.build_fixture()
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['archiveCoverage']['channelEntries'], 1)
        self.assertEqual(data['monthlyCoverage']['rows'][-1]['channels']['知识星球']['bodyCount'], 1)

    def test_incremental_identity_conflict_cannot_replace_original(self):
        original = {'id': 'star', 'channel': '知识星球', 'sha256': '0' * 64, 'path': 'x.pdf'}
        self.put('channel-bibliography.json', {'articles': [original]})
        self.put('channel-monthly-bibliography.json', {'articles': [{**original, 'sha256': '1' * 64}]})
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.build_fixture()

    def test_star_filename_policy_reaches_source_catalogue_without_erasing_printed_date(self):
        self.put_parent({'id': 'date-conflict-star', 'channel': '知识星球', 'filenameDate': '2026-01-12'},
                        publication_date='2026-02-01')
        data = self.build_fixture()
        report = data['reports'][0]
        self.assertEqual(report['publicationDate'], '2026-02-01')
        self.assertEqual(report['date'], '2026-01-12')
        self.assertEqual(next(s for s in data['sources'] if s['id'] == report['id'])['date'], '2026-01-12')
        self.assertFalse(report['historicalAsOfEligible'])

    def test_canonical_ids_keep_verified_legacy_references_and_expose_merge_aliases(self):
        record = self.put_parent({'id': 'canonical-star', 'channel': '知识星球', 'filenameDate': '2026-01-12'})
        self.put('channel-bibliography.json', {'articles': [{**record, 'id': 'old-star'}]})
        data = self.build_fixture()
        self.assertEqual([r['id'] for r in data['reports']], ['old-star'])
        self.assertEqual(data.get('reportIdAliases', {}).get('canonical-star'), 'old-star')
        self.assertEqual(data['monthlyCoverage']['rows'][0]['channels']['知识星球']['archives'][0]['reportId'], 'old-star')

    def test_public_evidence_whitelist_does_not_dump_private_author_contacts_or_text_paths(self):
        self.assertTrue(hasattr(self.builder, 'publication_snapshot'), 'Public evidence whitelist is missing')
        data = {'reports': [], 'windResearchEvidence': [{'id': 'TEST ONLY', 'reportId': 'TEST ONLY',
            'claim': 'TEST ONLY short attributed claim', 'evidenceExcerpt': 'TEST ONLY short excerpt',
            'authorIdentity': {'institution': 'TEST institution', 'authors': ['TEST author'],
                               'contacts': {'TEST author': 'PRIVATE@example.com'}},
            'textPath': 'E:\\private\\full-text.txt', 'fullText': 'TEST ONLY private full body',
            'publicationDateEvidence': {'auditPath': 'E:\\private\\audit.json'}}]}
        public = self.builder.publication_snapshot(data, self.root)
        serialized = json.dumps(public)
        for field in ('contacts', 'fullText', 'textPath', 'auditPath', '@'):
            self.assertNotIn(field, serialized)
        self.assertEqual(public['windResearchEvidence'][0]['authorIdentity']['authors'], ['TEST author'])
        self.assertEqual(public['windResearchEvidence'][0]['evidenceExcerpt'], 'TEST ONLY short excerpt')

    def test_public_reviewed_opinion_preserves_reality_references_and_not_private_pair_audit(self):
        public=self.builder.publication_snapshot({'reports':[], 'windResearchEvidence':[{
            'id':'TEST ONLY','reportId':'TEST ONLY','claim':'TEST ONLY',
            'realitySourceIds':['TEST OFFICIAL'], 'attributionStatus':'original_research_attribution_not_market_consensus',
            'realizationPair':{'privateAuditPath':'E:\\private\\audit.json','context':'TEST ONLY private full support'},
        }]},self.root)
        self.assertEqual(public['windResearchEvidence'][0].get('realitySourceIds'),['TEST OFFICIAL'])
        self.assertNotIn('realizationPair',public['windResearchEvidence'][0])

    def test_cli_exposes_explicit_parent_source_manifest_without_future_path_guessing(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, str(SCRIPT), '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--parent-source-manifest', result.stdout)

    def test_library_whitelist_and_unknown_quality_propagate_to_source_catalogue(self):
        self.put('local-bibliography.json', {'articles': [{'id': 'local-private', 'title': 'TEST ONLY',
            'publicationDate': None, 'firstAvailableDate': None, 'historicalAsOfEligible': True,
            'fullText': 'TEST ONLY private paid full body', 'contacts': ['PRIVATE@example.com'],
            'identityEvidence': {'text': 'TEST ONLY private body'}, 'sourcePath': 'E:\\private\\full.pdf'}]})
        data = self.build_fixture()
        serialized = json.dumps(data['reports'])
        for denied in ('fullText', 'contacts', 'identityEvidence', 'sourcePath', '@'):
            self.assertNotIn(denied, serialized)
        source = next(s for s in data['sources'] if s['id'] == 'local-private')
        self.assertIsNone(source['firstAvailableDate'])
        self.assertFalse(source['historicalAsOfEligible'])
        self.assertEqual(source['sourceQuality'], {'status': 'unknown'})

    def test_rejected_legacy_body_and_dependent_analysis_cannot_leak_to_library(self):
        self.put('channel-bibliography.json', {'articles': [{'id': 'wrong-tag', 'channel': '知识星球',
            'title': 'TEST ONLY PRIVATE WRONG TAG', 'archiveBytesAndAllPagesVerified': True,
            'bodyTitleVerified': True, 'historicalAsOfEligible': True}]})
        self.put('channel-expectation-evidence.json', {'items': [{'id': 'wrong-view', 'reportId': 'wrong-tag',
            'channel': '知识星球', 'claim': 'TEST ONLY UNQUALIFIED CLAIM'}]})
        self.put('market-analysis.json', {'conclusion': 'TEST ONLY old conclusion',
            'sections': [{'id': 'theme', 'title': 'TEST ONLY theme', 'reportIds': ['wrong-tag'], 'sourceIds': [],
                          'judgement': 'TEST ONLY UNQUALIFIED CLAIM'}], 'limitations': []})
        data = self.build_fixture()
        self.assertEqual(data['reports'], [])
        self.assertEqual(data['researchEvidence'], [])
        self.assertNotIn('TEST ONLY UNQUALIFIED CLAIM', json.dumps(data))
        self.assertNotIn('TEST ONLY PRIVATE WRONG TAG', json.dumps(data))
        self.assertEqual(data['marketAnalysis']['sections'][0]['reportIds'], [])

    def test_current_clean_parent_library_drives_real_partial_matrix(self):
        root = SCRIPT.parents[1]
        stage = root / '美国宏观复盘/降息起步后的双向政策时代/2026-01_2026-08'
        data = self.builder.build(stage, root, allow_partial=True)
        from collections import Counter
        counts = Counter(self.builder.channel_of(r) for r in data['reports'])
        self.assertEqual({c: counts[c] for c in ('知识星球', 'Wind', '微信公众号')},
                         {'知识星球': 138, 'Wind': 80, '微信公众号': 41})
        self.assertEqual(data['monthlyCoverage']['acceptedCells'], 22)
        self.assertFalse(data['monthlyCoverage']['complete'])
        self.assertEqual([row['channels']['知识星球']['bodyCount'] for row in data['monthlyCoverage']['rows']],
                         [6, 12, 20, 20, 20, 20, 20, 20])
        star_acquisition = next(a for a in data['acquisition'] if a['provider'] == '知识星球')
        self.assertIn('新增下载129份', star_acquisition['detail'])
        self.assertNotIn('未取得本轮新PDF', star_acquisition['detail'])
        self.assertIn('月度验收8/8', next(a for a in data['acquisition'] if a['provider'] == 'Wind')['detail'])
        self.assertNotIn('正文未核', next(a for a in data['acquisition'] if a['provider'] == '微信')['detail'])
        for report in data['reports']:
            if self.builder.channel_of(report):
                self.assertTrue(report['sourceQuality']['parentLedgerVerified'])
                self.assertIsNone(report['firstAvailableDate'])
                self.assertFalse(report['historicalAsOfEligible'])
        ids = {r['id'] for r in data['reports']}
        for field in ('researchEvidence', 'windResearchEvidence', 'wechatResearchEvidence', 'localResearchEvidence'):
            self.assertTrue(all(v['reportId'] in ids for v in data[field]))
        self.assertNotIn('wechat-min5-5302914972ca2ce3', ids)
        self.assertNotIn('wechat-min5-6a6eb65592ba166e', ids)

if __name__ == '__main__':
    unittest.main()
