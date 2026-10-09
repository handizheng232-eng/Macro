"""Tests of archive-backed month/channel coverage; fixtures are not real reports."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

class MonthlyCoverageTests(unittest.TestCase):
    def test_same_bytes_with_different_claimed_work_ids_cannot_inflate_quota(self):
        receipt=self.receipt()
        records=[{**receipt,'independentWorkId':'fixture-a'},
                 {**receipt,'id':'fixture-b','independentWorkId':'fixture-b'}]
        cell=self.coverage(records)['rows'][0]['channels']['知识星球']
        self.assertEqual(cell['archiveEntries'],2)
        self.assertEqual(cell['bodyCount'],1)

    def test_unadmitted_missing_sha_and_missing_file_remains_unassigned(self):
        receipt=self.receipt()
        receipt.pop('sha256');receipt.pop('sourceQuality')
        Path(receipt['path']).unlink()
        data=self.coverage([receipt])
        self.assertEqual(data['unassignedArchiveEntries'],1)
        self.assertEqual(data['coveredCells'],0)

    def test_admitted_sha_failure_is_not_hidden_by_unassigned_date(self):
        receipt=self.receipt(day=None)
        receipt['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'SHA mismatch'):
            self.coverage([receipt])
        receipt.pop('sha256')
        with self.assertRaisesRegex(ValueError,'Missing SHA'):
            self.coverage([receipt])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / 'stage'
        self.stage.mkdir()
        spec = importlib.util.spec_from_file_location('coverage', Path(__file__).with_name('replay_monthly_coverage.py'))
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def receipt(self, channel='知识星球', day='2026-01-12', name='fixture.pdf'):
        path = self.stage / name
        path.write_bytes(b'%PDF-1.7\nTEST ONLY: archive-integrity fixture, not published research.\n')
        return {'id': name, 'channel': channel, 'path': str(path),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'filenameDate': day, 'publicationDate': None,
                'dateBasis': 'filename_date_user_preferred',
                'sourceQuality': {'parentLedgerVerified': True, 'originalBodyVerified': True,
                    'datePolicyVerified': True, 'scopeVerified': True, 'tag': '调研纪要',
                    'versionType': 'original_audio_transcript_pdf' if channel == '知识星球' else
                                   'institutional_research_pdf' if channel == 'Wind' else 'official_original_article_text',
                    'printedPublicationVerified': True, 'officialHeaderVerified': True,
                    'account': 'TEST ACCOUNT'}}

    def coverage(self, reports, audit=None):
        return self.module.build_monthly_coverage('2026-01-01', '2026-08-31', reports, self.root, self.stage, audit)

    def test_every_month_and_channel_present_even_when_not_searched(self):
        data = self.coverage([])
        self.assertEqual(len(data['rows']), 8)
        self.assertEqual(data['requiredCells'], 24)
        self.assertEqual(data['coveredCells'], 0)
        self.assertFalse(data['complete'])
        self.assertEqual(list(data['rows'][0]['channels']), ['知识星球', 'Wind', '微信公众号'])
        self.assertTrue(all(c['status'] == '未取得正文' for row in data['rows'] for c in row['channels'].values()))

    def test_only_last_month_archive_is_not_interval_completion(self):
        data = self.coverage([self.receipt(day='2026-08-02')])
        self.assertEqual(data['rows'][-1]['channels']['知识星球']['bodyCount'], 1)
        self.assertEqual(data['coveredCells'], 1)
        self.assertFalse(data['complete'])
        self.assertFalse(data['rows'][-1]['channels']['知识星球']['searchExecuted'])

    def test_archive_source_not_local_provider_name_determines_channel(self):
        local = self.receipt()
        local.pop('channel')
        local.update(provider='长江证券', path=str(self.stage / 'fixture.pdf'), accountActual='知识星球附件')
        data = self.coverage([local])
        self.assertEqual(data['coveredCells'], 0)

    def test_same_sha_cannot_inflate_unique_month_count(self):
        receipt = self.receipt()
        duplicate = {**receipt, 'id': 'duplicate'}
        data = self.coverage([receipt, duplicate])
        cell = data['rows'][0]['channels']['知识星球']
        self.assertEqual(cell['archiveEntries'], 2)
        self.assertEqual(cell['bodyCount'], 1)

    def test_missing_or_mismatched_archive_fails_closed(self):
        receipt = self.receipt()
        receipt['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'SHA'):
            self.coverage([receipt])

    def test_month_only_date_does_not_manufacture_a_day(self):
        receipt = self.receipt(day='2026-01')
        data = self.coverage([receipt])
        self.assertEqual(data['coveredCells'], 0)
        self.assertEqual(data['unassignedArchiveEntries'], 1)

    def test_legacy_unverified_archive_without_sha_is_not_a_verified_monthly_body(self):
        receipt = self.receipt()
        receipt.pop('sha256')
        receipt.pop('sourceQuality')
        data = self.coverage([receipt])
        self.assertEqual(data['coveredCells'], 0)
        self.assertEqual(data['unassignedArchiveEntries'], 1)
        self.assertFalse(data['complete'])

    def test_parent_verified_archive_without_sha_still_fails_closed(self):
        receipt = self.receipt()
        receipt.pop('sha256')
        with self.assertRaisesRegex(ValueError, 'Missing SHA'):
            self.coverage([receipt])

    def test_wind_filename_cannot_replace_unverified_printed_publication_date(self):
        receipt = self.receipt(channel='Wind')
        data = self.coverage([receipt])
        self.assertEqual(data['coveredCells'], 0)
        receipt['publicationDate'] = '2026-02-03'
        receipt['dateBasis'] = 'printed_publication_date'
        data = self.coverage([receipt])
        self.assertEqual(data['rows'][1]['channels']['Wind']['bodyCount'], 1)

    def test_search_log_is_not_body_and_blocked_search_is_not_success(self):
        audit = {'rows': [{'month': '2026-01', 'channel': 'Wind', 'searchExecuted': True,
                           'status': 'blocked', 'matchedCount': 50, 'reason': 'TEST ACCESS BLOCK'}]}
        data = self.coverage([], audit)
        cell = data['rows'][0]['channels']['Wind']
        self.assertEqual(cell['bodyCount'], 0)
        self.assertEqual(cell['status'], '采集受阻')
        self.assertFalse(data['complete'])

    def test_partial_search_is_not_accepted_even_with_original_pdf(self):
        audit = {'rows': [{'month': '2026-01', 'channel': '知识星球',
                           'searchExecuted': True, 'searchComplete': False,
                           'status': 'partial_not_complete'}]}
        cell = self.coverage([self.receipt()], audit)['rows'][0]['channels']['知识星球']
        self.assertTrue(cell['covered'])
        self.assertFalse(cell['accepted'])
        audit['rows'][0]['searchComplete'] = True
        # A complete-search flag is not an independently verified actual-shortage proof.
        self.assertFalse(self.coverage([self.receipt()], audit)['rows'][0]['channels']['知识星球']['accepted'])

    def test_latest_monthly_audit_supersedes_earlier_partial_receipt(self):
        old = self.stage / '核验/逐月补采20261002'
        new = self.stage / '核验/逐月补采20261007'
        old.mkdir(parents=True)
        new.mkdir(parents=True)
        (old / 'gui-monthly-audit.json').write_text('{"rows":[{"month":"2026-05","channel":"知识星球","searchExecuted":true,"searchComplete":true}]}', encoding='utf-8')
        (new / 'gui-monthly-audit-20261007.json').write_text('{"rows":[{"month":"2026-05","channel":"知识星球","searchExecuted":true,"searchComplete":false,"gap":"search incomplete"}]}', encoding='utf-8')
        rows = self.module.load_monthly_audits(self.stage)['rows']
        self.assertEqual([row for row in rows if row['month'] == '2026-05'], [
            {'month': '2026-05', 'channel': '知识星球', 'searchExecuted': True,
             'searchComplete': False, 'gap': 'search incomplete', 'reason': 'search incomplete'}])

    def test_wind_gui_receipt_maps_executed_but_not_complete(self):
        folder = self.stage / '核验/逐月补采20261007-晚间'
        folder.mkdir(parents=True)
        (folder / 'wind-rpp-monthly-receipts-incremental.json').write_text(json.dumps({'rows': [
            {'month': '2026-03', 'searchExecutedThisRun': True, 'searchComplete': False,
             'resultCountTitle': 20, 'resultCountFulltext': 264,
             'gap': '仅审标题及全文首屏，未检索其他关键词'}]}), encoding='utf-8')
        rows = self.module.load_monthly_audits(self.stage)['rows']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['channel'], 'Wind')
        self.assertTrue(rows[0]['searchExecuted'])
        self.assertFalse(rows[0]['searchComplete'])
        self.assertEqual(rows[0]['matchedCount'], 20)
        self.assertIn('未检索其他关键词', rows[0]['reason'])

    def test_zsxq_tag_feed_receipt_never_passes_full_month_gate(self):
        folder = self.stage / '核验/逐月补采20261008-知识星球'
        folder.mkdir(parents=True)
        (folder / 'gui-monthly-audit-incremental.json').write_text(json.dumps({
            'months': {
                '2026-05': {'searchExecutedThisRun': True, 'searchComplete': True,
                            'searchCompleteScope': '仅#调研纪要标签逐帖页面',
                            'newPdfCount': 0, 'note': '标签跨度已遍历'},
                '2026-06': {'searchExecutedThisRun': True, 'searchComplete': True,
                            'searchCompleteScope': '仅#调研纪要标签逐帖页面',
                            'selectedCandidateOnlyCount': 20, 'newPdfCount': 0},
                '2026-01': {'searchExecutedThisRun': True, 'searchComplete': False,
                            'matchedCount': None, 'newPdfCount': 0,
                            'note': '滚动经过该月但未导出文件名'}}}), encoding='utf-8')
        rows = {row['month']: row for row in self.module.load_monthly_audits(self.stage)['rows']}
        self.assertEqual(set(rows), {'2026-01', '2026-05', '2026-06'})
        for row in rows.values():
            self.assertTrue(row['searchExecuted'])
            self.assertFalse(row['searchComplete'])
            self.assertIsNone(row['matchedCount'])
            self.assertIn('未完成', row['reason'])
        cell = self.coverage([self.receipt(day='2026-05-19')], {'rows': list(rows.values())})['rows'][4]['channels']['知识星球']
        self.assertEqual(cell['bodyCount'], 1)
        self.assertFalse(cell['accepted'])

    def test_later_full_zsxq_search_can_supersede_tag_only_receipt(self):
        partial = self.stage / '核验/逐月补采20261008-知识星球'
        later = self.stage / '核验/逐月补采20261009'
        partial.mkdir(parents=True)
        later.mkdir(parents=True)
        (partial / 'gui-monthly-audit-incremental.json').write_text(json.dumps({
            'months': {'2026-05': {'searchExecutedThisRun': True, 'searchComplete': True,
                                   'searchCompleteScope': '仅#调研纪要标签逐帖页面'}}}), encoding='utf-8')
        (later / 'gui-monthly-audit.json').write_text(json.dumps({'rows': [
            {'month': '2026-05', 'channel': '知识星球', 'searchExecuted': True,
             'searchComplete': True, 'matchedCount': 20}]}), encoding='utf-8')
        row = self.module.load_monthly_audits(self.stage)['rows'][0]
        self.assertTrue(row['searchComplete'])
        self.assertEqual(row['matchedCount'], 20)

    def test_public_reason_is_concise_chinese_without_changing_raw_audit(self):
        note = 'No verified full-month search; 0 files does not mean 0 matches.'
        folder = self.stage / '核验/逐月补采20261007'
        folder.mkdir(parents=True)
        (folder / 'gui-monthly-audit-20261007.json').write_text(
            json.dumps({'rows': [{'month': '2026-01', 'channel': '知识星球',
                                   'searchExecuted': False, 'searchComplete': False, 'gap': note}]}), encoding='utf-8')
        receipt = self.module.load_monthly_audits(self.stage)['rows'][0]
        self.assertEqual(receipt['gap'], note)
        self.assertEqual(receipt['reason'], '逐月检索未完成；零文件不等于零发布。')

    def test_verified_wind_issue_month_counts_without_fabricating_day(self):
        report = self.receipt(channel='Wind')
        report.update(publicationDate=None, publicationDatePrecision='month', verifiedPublicationMonth='2026-03')
        cell = self.coverage([report])['rows'][2]['channels']['Wind']
        self.assertEqual(cell['bodyCount'], 1)
        self.assertEqual(cell['archives'][0]['date'], '2026-03')

    def test_pinned_complete_zero_eligible_search_is_not_confused_with_unknown_or_blocked(self):
        evidence = self.stage / 'zero-search.txt'
        evidence.write_text('TEST ONLY full-month enumeration with no qualifying original PDFs', encoding='utf-8')
        proof = self.stage / 'zero-parent-proof.json'
        ledger = {'month': '2026-02', 'channel': '知识星球', 'requiredTopicTag': '调研纪要',
                  'onlyOriginalPdf': True, 'searchExecuted': True, 'searchExhaustive': True, 'blocked': False,
                  'actualEligibleTotal': 0, 'eligibleWorks': [], 'evidenceArtifacts': [
                      {'path': str(evidence), 'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}]}
        proof.write_text(json.dumps(ledger), encoding='utf-8')
        audit = {'trustedShortageProofs': [{'path': str(proof), 'sha256': hashlib.sha256(proof.read_bytes()).hexdigest()}]}
        cell = self.coverage([], audit)['rows'][1]['channels']['知识星球']
        self.assertTrue(cell['accepted'])
        self.assertTrue(cell['searchExecuted'])
        self.assertTrue(cell['searchExhaustive'])
        self.assertEqual(cell['bodyCount'], 0)
        ledger['blocked'] = True
        proof.write_text(json.dumps(ledger), encoding='utf-8')
        audit['trustedShortageProofs'][0]['sha256'] = hashlib.sha256(proof.read_bytes()).hexdigest()
        self.assertFalse(self.coverage([], audit)['rows'][1]['channels']['知识星球']['accepted'])
        self.assertFalse(self.coverage([])['rows'][1]['channels']['知识星球']['accepted'])

    def test_quota_status_distinguishes_acceptance_from_search_exhaustion(self):
        report = self.receipt()
        audit = {'rows': [{'month': '2026-01', 'channel': '知识星球', 'searchExecuted': True,
                           'searchComplete': True, 'searchExhaustive': True}]}
        cell = self.coverage([report], audit)['rows'][0]['channels']['知识星球']
        self.assertFalse(cell['accepted'])
        self.assertIn('不足', cell['status'])

    def test_independent_work_linkage_deduplicates_different_archive_hashes(self):
        first = self.receipt(name='first.pdf')
        second = self.receipt(name='second.pdf')
        path = Path(second['path'])
        path.write_bytes(path.read_bytes() + b' TEST ONLY watermark')
        second['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        first['independentWorkId'] = second['independentWorkId'] = 'same-underlying-work'
        cell = self.coverage([first, second])['rows'][0]['channels']['知识星球']
        self.assertEqual(cell['bodyCount'], 1)
        self.assertEqual(cell['archiveEntries'], 2)
        self.assertEqual(len(cell['distributionRecords']), 2)

    def test_wechat_minimum_requires_multiple_real_publishing_accounts(self):
        reports = []
        for n in range(5):
            report = self.receipt(channel='微信公众号', name=f'wechat-{n}.txt')
            path = Path(report['path'])
            path.write_text(f'TEST ONLY published original body {n}', encoding='utf-8')
            report.update(publicationDate='2026-01-12', sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            reports.append(report)
        self.assertFalse(self.coverage(reports)['rows'][0]['channels']['微信公众号']['accepted'])
        reports[-1]['sourceQuality']['account'] = 'OTHER TEST ACCOUNT'
        self.assertTrue(self.coverage(reports)['rows'][0]['channels']['微信公众号']['accepted'])
        self.assertEqual(self.coverage(reports)['rows'][0]['channels']['微信公众号']['accountCount'], 2)

    def test_real_smaller_total_requires_hash_pinned_parent_search_evidence(self):
        report = self.receipt()
        report['independentWorkId'] = 'test-work'
        evidence = self.stage / 'actual-search.txt'
        evidence.write_text('TEST ONLY complete eligible enumeration receipt', encoding='utf-8')
        proof = self.stage / 'parent-shortage.json'
        ledger = {'month': '2026-01', 'channel': '知识星球', 'requiredTopicTag': '调研纪要',
                  'onlyOriginalPdf': True, 'searchExecuted': True, 'searchExhaustive': True,
                  'blocked': False, 'actualEligibleTotal': 1,
                  'evidenceArtifacts': [{'path': str(evidence), 'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}],
                  'eligibleWorks': [{'independentWorkId': 'test-work', 'path': report['path'],
                                     'sha256': report['sha256'], 'date': '2026-01-12'}]}
        proof.write_text(json.dumps(ledger), encoding='utf-8')
        binding = {'path': str(proof), 'sha256': hashlib.sha256(proof.read_bytes()).hexdigest()}
        audit = {'rows': [{'month': '2026-01', 'channel': '知识星球', 'searchExecuted': True,
                           'searchComplete': True, 'searchExhaustive': True,
                           'actualEligibleTotal': 1, 'shortageEvidenceVerified': True}]}
        self.assertFalse(self.coverage([report], audit)['rows'][0]['channels']['知识星球']['accepted'])
        audit['trustedShortageProofs'] = [binding]
        cell = self.coverage([report], audit)['rows'][0]['channels']['知识星球']
        self.assertTrue(cell['accepted'])
        self.assertTrue(cell['shortageEvidenceVerified'])
        self.assertEqual(cell['acceptanceBasis'], 'verified_actual_eligible_total')
        self.assertEqual(cell['shortageEvidence']['actualEligibleTotal'], 1)
        self.assertFalse(self.coverage([], audit)['rows'][0]['channels']['知识星球']['accepted'])
        evidence.write_text('TEST ONLY altered evidence', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'shortage.*SHA|SHA.*shortage'):
            self.coverage([report], audit)

    def test_twenty_verified_originals_accept_without_claiming_exhaustive_search(self):
        reports = []
        for n in range(20):
            report = self.receipt(name=f'quota-{n}.pdf')
            path = Path(report['path'])
            path.write_bytes(path.read_bytes() + str(n).encode())
            report['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            report['sourceQuality'] = {'parentLedgerVerified': True, 'originalBodyVerified': True,
                                      'datePolicyVerified': True, 'scopeVerified': True,
                                      'tag': '调研纪要', 'versionType': 'original_audio_transcript_pdf'}
            reports.append(report)
        audit = {'rows': [{'month': '2026-01', 'channel': '知识星球', 'searchExecuted': True,
                           'searchComplete': False, 'searchExhaustive': False}]}
        cell = self.coverage(reports, audit)['rows'][0]['channels']['知识星球']
        self.assertTrue(cell['accepted'])
        self.assertTrue(cell['quotaAccepted'])
        self.assertEqual(cell['requiredCount'], 20)
        self.assertEqual(cell['verifiedBodyCount'], 20)
        self.assertEqual(cell['acceptanceBasis'], 'minimum_verified_originals')
        self.assertFalse(cell['searchExhaustive'])
        self.assertFalse(cell['searchComplete'])
        reports[-1]['sourceQuality']['originalBodyVerified'] = False
        self.assertFalse(self.coverage(reports, audit)['rows'][0]['channels']['知识星球']['accepted'])

if __name__ == '__main__':
    unittest.main()
