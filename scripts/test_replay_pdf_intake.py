"""Independent PDF intake tests; synthetic PDFs are fixtures, not reports."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import sys
from pypdf import PdfWriter

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / '美国宏观复盘/降息起步后的双向政策时代/2026-01_2026-08/核验/执行优化20261008/PDF入库闭环'


class IntakeTests(unittest.TestCase):
    def setUp(self):
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=EVIDENCE)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        script = Path(__file__).with_name('replay_pdf_intake.py')
        if not script.exists():
            self.fail('Independent intake entry point has not been implemented')
        spec = importlib.util.spec_from_file_location('replay_pdf_intake', script)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def pdf(self, name='selected.pdf', pages=2, encrypted=False):
        path = self.root / name
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(width=300, height=300)
        if encrypted:
            writer.encrypt('TEST-FIXTURE-ONLY')
        with path.open('wb') as handle:
            writer.write(handle)
        return path

    def record(self, path, **overrides):
        return {'path': str(path), 'channel': '知识星球',
                'originalFilename': '美元260120_原文.pdf', 'platformDate': '2026-01-21',
                'filenameDate': '2026-01-20', 'publicationDate': None,
                'sourceKind': 'original_pdf', 'disposition': 'reuse', **overrides}

    def intake(self, records, **extra):
        return self.module.run_intake(
            {'schema': 'replay.pdf.intake.selection.v1', 'files': records, **extra},
            self.root / 'archive', self.root / 'ledger.json', self.root / 'report.json')

    def test_reuse_checks_real_bytes_all_pages_but_is_never_new(self):
        source = self.pdf()
        other = self.root / 'NOT_SELECTED.pdf'
        other.write_bytes(b'not a PDF')
        result = self.intake([self.record(source)])
        row = result['items'][0]
        self.assertEqual(result['validatedPdfCount'], 1)
        self.assertEqual(result['newPdfCount'], 0)
        self.assertEqual(row['sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(row['pageCount'], 2)
        self.assertEqual(len(row['pageChecks']), 2)
        self.assertTrue(row['manualIdentityReviewRequired'])
        self.assertIsNone(row['firstAvailableDate'])
        self.assertFalse(row['historicalAsOfEligible'])
        self.assertEqual(row['archiveDate'], '2026-01-20')
        self.assertFalse((self.root / 'archive').exists())
        self.assertEqual(json.loads((self.root / 'ledger.json').read_text())['schema'],
                         'replay.pdf.intake.ledger.v1')

    def test_invalid_metadata_or_incomplete_pdf_is_rejected_not_a_receipt(self):
        valid = self.pdf()
        missing_eof = self.root / 'partial.pdf'
        missing_eof.write_bytes(valid.read_bytes().split(b'%%EOF')[0])
        fake = self.root / 'receipt.pdf'
        fake.write_bytes(b'%PDF-1.7\nDownload successful\n%%EOF\n')
        html = self.root / 'error.pdf'
        html.write_bytes(b'<html>Download queued</html>')
        encrypted = self.pdf('encrypted.pdf', encrypted=True)
        records = [self.record(path) for path in
                   [missing_eof, fake, html, encrypted, self.root / 'missing.pdf']]
        records += [self.record(valid, token='NEVER_ACCEPT'),
                    self.record(valid, originalFilename='https://host/a.pdf?signature=SECRET'),
                    self.record(valid, originalFilename='https%3A%2F%2Fhost%2FSECRET.pdf'),
                    self.record(valid, filenameDate='2026-02-30'),
                    self.record(valid, originalFilename='../escape.pdf')]
        try:
            result = self.intake(records)
        except Exception:
            self.fail('Intake must persist per-file rejection instead of aborting the whole batch')
        self.assertEqual(result['validatedPdfCount'], 0)
        self.assertEqual(result['rejectedCount'], len(records))
        self.assertEqual(result['newPdfCount'], 0)
        self.assertTrue(all(row['status'] == 'rejected' for row in result['items']))
        self.assertNotIn('SECRET', (self.root / 'report.json').read_text())
        self.assertNotIn('NEVER_ACCEPT', (self.root / 'ledger.json').read_text())
        self.assertFalse((self.root / 'archive').exists())

    def test_new_archive_is_byte_identical_and_rerun_counts_zero(self):
        source = self.pdf()
        record = self.record(source, disposition='new_download')
        first = self.intake([record], knownFiles=[])
        self.assertEqual(first['newPdfCount'], 1)
        self.assertEqual(first['newZsxqOriginalPdfCount'], 1)
        archived = Path(first['items'][0]['archivePath'])
        self.assertEqual(archived.read_bytes(), source.read_bytes())
        second = self.intake([record], knownFiles=[])
        self.assertEqual(second['newPdfCount'], 0)
        self.assertEqual(second['validatedPdfCount'], 1)
        self.assertEqual(len(list((self.root / 'archive').rglob('*.pdf'))), 1)

    def test_print_and_existing_bytes_cannot_inflate_original_count(self):
        original = self.pdf()
        printed = self.pdf('print.pdf', pages=3)
        existing = self.pdf('already.pdf', pages=4)
        records = [self.record(original, disposition='new_download'),
                   self.record(printed, sourceKind='webpage_print', disposition='new_download'),
                   self.record(existing, originalFilename='旧原件.pdf', disposition='new_download')]
        result = self.intake(records, knownFiles=[str(existing)])
        self.assertEqual(result['newPdfCount'], 2)
        self.assertEqual(result['newOriginalPdfCount'], 1)
        self.assertEqual(result['newWebpagePrintCount'], 1)
        self.assertEqual(result['newZsxqOriginalPdfCount'], 1)
        self.assertIn('webpage_print', result['items'][1]['archivePath'])
        self.assertEqual(result['items'][2]['status'], 'reused_known_bytes')
        self.assertEqual(result['acceptedOriginalBodyCount'], 0)

    def test_same_original_filename_different_sha_never_overwrites(self):
        first = self.pdf()
        second = self.pdf('different.pdf', pages=3)
        result = self.intake([self.record(first, disposition='new_download'),
                              self.record(second, disposition='new_download')], knownFiles=[])
        self.assertEqual(result['newPdfCount'], 1)
        self.assertEqual(result['rejectedCount'], 1)
        self.assertEqual(result['items'][1]['reasonCode'], 'FILENAME_SHA_CONFLICT')
        self.assertEqual(Path(result['items'][0]['archivePath']).read_bytes(), first.read_bytes())

    def test_checkpoint_recovers_after_copy_without_recounting(self):
        self.assertTrue(hasattr(self.module, 'atomic_write_json'), 'Atomic checkpoints not implemented')
        source = self.pdf()
        record = self.record(source, disposition='new_download')
        write = self.module.atomic_write_json

        def interrupt_completion(path, payload):
            if payload.get('schema') == 'replay.pdf.intake.ledger.v1' and any(
                    row.get('status') == 'archived_new' for row in payload['items'].values()):
                raise KeyboardInterrupt('TEST: crash after real PDF publication before final checkpoint')
            return write(path, payload)

        with patch.object(self.module, 'atomic_write_json', side_effect=interrupt_completion):
            with self.assertRaises(KeyboardInterrupt):
                self.intake([record], knownFiles=[])
        checkpoint = json.loads((self.root / 'ledger.json').read_text())
        self.assertEqual(next(iter(checkpoint['items'].values()))['status'], 'prepared')
        self.assertEqual(len(list((self.root / 'archive').rglob('*.pdf'))), 1)
        recovered = self.intake([record], knownFiles=[])
        self.assertEqual(recovered['newPdfCount'], 0)
        self.assertEqual(recovered['items'][0]['status'], 'recovered_existing')

    def test_tampered_archive_is_rejected_and_not_replaced(self):
        source = self.pdf()
        record = self.record(source, disposition='new_download')
        result = self.intake([record], knownFiles=[])
        dest = Path(result['items'][0]['archivePath'])
        dest.write_bytes(b'TAMPERED')
        result = self.intake([record], knownFiles=[])
        self.assertEqual(result['rejectedCount'], 1)
        self.assertEqual(result['newPdfCount'], 0)
        self.assertEqual(dest.read_bytes(), b'TAMPERED')

    def test_cli_partial_batch_and_resume(self):
        first, second = self.pdf(), self.pdf('second.pdf', pages=3)
        manifest = self.root / 'selection.json'
        manifest.write_text(json.dumps({'schema': 'replay.pdf.intake.selection.v1', 'knownFiles': [],
            'files': [self.record(first, disposition='new_download'),
                      self.record(second, disposition='new_download', originalFilename='美元260121_原文.pdf')]}))
        args = [sys.executable, str(Path(__file__).with_name('replay_pdf_intake.py')),
                '--selection', str(manifest), '--archive', str(self.root / 'archive'),
                '--ledger', str(self.root / 'ledger.json'), '--report', str(self.root / 'report.json')]
        partial = subprocess.run(args + ['--max-items', '1'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(partial.returncode, 3, partial.stderr)
        resumed = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        summary = json.loads(resumed.stdout)
        self.assertEqual(summary['newPdfCount'], 1)
        self.assertEqual(summary['validatedPdfCount'], 2)
        again = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(json.loads(again.stdout)['newPdfCount'], 0)

    def test_unrelated_json_and_output_alias_are_never_overwritten(self):
        source = self.pdf()
        report = self.root / 'report.json'
        report.write_text('{"production": true}')
        with self.assertRaises(ValueError):
            self.intake([self.record(source)])
        self.assertEqual(report.read_text(), '{"production": true}')
        with self.assertRaises(ValueError):
            self.module.run_intake({'schema': 'replay.pdf.intake.selection.v1', 'files': [self.record(source)]},
                self.root / 'archive', source, self.root / 'out.json')
        self.assertTrue(source.read_bytes().startswith(b'%PDF-'))

    def test_dual_parser_evidence_and_late_page_corruption(self):
        valid = self.pdf()
        accepted = self.intake([self.record(valid)])
        row = accepted['items'][0]
        self.assertEqual(row.get('parsers'), ['pypdf_strict', 'pymupdf_no_repair'])
        self.assertFalse(row.get('isRepaired', True))
        self.assertTrue(all(p.get('secondaryParserRead') for p in row['pageChecks']))
        from pypdf.generic import NameObject, NumberObject
        bad = self.root / 'bad-page2.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        page = writer.add_blank_page(width=300, height=300)
        page[NameObject('/Contents')] = NumberObject(42)
        with bad.open('wb') as handle:
            writer.write(handle)
        result = self.intake([self.record(bad, originalFilename='坏页260121.pdf')])
        self.assertEqual(result['rejectedCount'], 1)
        self.assertEqual(result['newPdfCount'], 0)

    def test_channel_dates_do_not_fall_back_to_platform_or_local_filename(self):
        source = self.pdf('20261008-local-prefix.pdf')
        records = [self.record(source, filenameDate=None),
                   self.record(source, channel='Wind', publicationDate=None),
                   self.record(source, channel='微信公众号', filenameDate='2026-01-20', publicationDate='2026-02-03')]
        result = self.intake(records)
        self.assertEqual([r['archiveDate'] for r in result['items']], [None, None, '2026-02-03'])
        self.assertTrue(all(r['firstAvailableDate'] is None for r in result['items']))

    def test_os_ledger_lock_blocks_concurrent_cli(self):
        self.assertTrue(hasattr(self.module, 'ledger_lock'))
        source = self.pdf()
        manifest = self.root / 'selection.json'
        manifest.write_text(json.dumps({'schema': 'replay.pdf.intake.selection.v1', 'files': [self.record(source)]}))
        args = [sys.executable, str(Path(__file__).with_name('replay_pdf_intake.py')),
                '--selection', str(manifest), '--archive', str(self.root / 'archive'),
                '--ledger', str(self.root / 'ledger.json'), '--report', str(self.root / 'report.json')]
        with self.module.ledger_lock(self.root / 'ledger.json'):
            blocked = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(blocked.returncode, 2)
        self.assertEqual(json.loads(blocked.stderr)['reasonCode'], 'LEDGER_IN_USE')
        self.assertFalse((self.root / 'report.json').exists())

    def test_previous_reuse_cannot_be_relabelled_as_new_download(self):
        source = self.pdf()
        self.intake([self.record(source)])
        result = self.intake([self.record(source, disposition='new_download')], knownFiles=[])
        self.assertEqual(result['newPdfCount'], 0)
        self.assertEqual(result['validatedPdfCount'], 1)
        self.assertFalse((self.root / 'archive').exists())

    def test_same_bytes_across_channels_are_not_two_new_archives(self):
        source = self.pdf()
        result = self.intake([self.record(source, disposition='new_download'),
            self.record(source, channel='Wind', originalFilename='Wind文件.pdf', disposition='new_download')], knownFiles=[])
        self.assertEqual(result['newPdfCount'], 1)
        self.assertTrue(all(r['manualIdentityReviewRequired'] for r in result['items']))

    def test_max_items_does_not_parse_later_selected_files(self):
        first, later = self.pdf(), self.pdf('later.pdf', pages=3)
        with patch.object(self.module, 'validate_pdf', wraps=self.module.validate_pdf) as validate:
            self.module.run_intake({'schema': 'replay.pdf.intake.selection.v1',
                'files': [self.record(first), self.record(later, originalFilename='后续.pdf')]},
                self.root / 'archive', self.root / 'ledger.json', self.root / 'report.json', max_items=1)
        self.assertTrue(all(Path(call.args[0]) == first for call in validate.call_args_list))


if __name__ == '__main__':
    unittest.main()
