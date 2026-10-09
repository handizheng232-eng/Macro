"""Private, offline intake of explicitly selected PDFs; no browser or network access."""
from datetime import date, datetime
from hashlib import sha256
from io import BytesIO
import argparse
from contextlib import contextmanager
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

SELECTION_SCHEMA = 'replay.pdf.intake.selection.v1'
LEDGER_SCHEMA = 'replay.pdf.intake.ledger.v1'
REPORT_SCHEMA = 'replay.pdf.intake.report.v1'


class IntakeError(ValueError):
    """Safe reason code; never persist raw parser messages or untrusted values."""


def atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name + '-', suffix='.tmp', delete=False)
    temporary = Path(handle.name)
    try:
        with handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(6):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.05 * 2 ** attempt)  # Bounded Windows sharing violation retry; never delete target.
    finally:
        temporary.unlink(missing_ok=True)


def load_owned_json(path, schema):
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError, UnicodeError) as error:
        raise IntakeError('EXISTING_OUTPUT_IS_NOT_OWNED_JSON') from error
    if not isinstance(value, dict) or value.get('schema') != schema:
        raise IntakeError('EXISTING_OUTPUT_SCHEMA_MISMATCH')
    return value


@contextmanager
def ledger_lock(path):
    """OS lock releases after crashes; a surviving lock file is harmless."""
    path = Path(str(path) + '.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise IntakeError('LEDGER_IN_USE') from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def publish_pdf(dest, data, digest):
    """Atomic whole-byte publication, never overwrite an existing destination."""
    created = False
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(dir=dest.parent, prefix='.intake-', suffix='.tmp', delete=False)
        temporary = Path(handle.name)
        try:
            with handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, dest)
                created = True
            except FileExistsError:
                pass
        finally:
            temporary.unlink(missing_ok=True)
    if sha256(dest.read_bytes()).hexdigest() != digest:
        raise IntakeError('ARCHIVE_SHA_MISMATCH_NOT_OVERWRITTEN')
    return created


FIELDS = {'path', 'channel', 'originalFilename', 'platformDate', 'filenameDate',
          'publicationDate', 'sourceKind', 'disposition'}
CHANNELS = {'知识星球', 'Wind', '微信公众号'}


def validate_record(record):
    if not isinstance(record, dict) or set(record) - FIELDS:
        raise ValueError('Unsupported metadata fields; credentials and URLs are prohibited')
    required = FIELDS - {'disposition'}
    if not required <= record.keys():
        raise ValueError('Required explicit metadata missing')
    for value in record.values():
        if isinstance(value, str) and (re.search(r'\w+://|https?[:%]', value, re.I)
                or re.search(r'(?i)(authorization|bearer|cookie|token|signature|x-amz-)\s*[=: ]', value)):
            raise ValueError('URLs or authentication-like values prohibited')
    if record['channel'] not in CHANNELS or record['sourceKind'] not in {'original_pdf', 'webpage_print'}:
        raise ValueError('Unsupported channel or sourceKind')
    if record.get('disposition', 'reuse') not in {'reuse', 'new_download'}:
        raise ValueError('Unsupported disposition')
    name = record['originalFilename']
    if not isinstance(name, str) or not name.lower().endswith('.pdf') or any(c in name for c in '/\\\r\n\x00'):
        raise ValueError('originalFilename must be a literal PDF basename')
    for key in ('platformDate', 'filenameDate', 'publicationDate'):
        value = record[key]
        if value is not None:
            if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError('Date must be ISO day or null')
            date.fromisoformat(value)
    if not isinstance(record['path'], str) or not Path(record['path']).is_absolute():
        raise ValueError('Selected path must be an explicit absolute local file')
    return {**record, 'disposition': record.get('disposition', 'reuse')}


def validate_pdf(path):
    """Read actual PDF bytes and force strict parsing of every physical page."""
    from pypdf import PdfReader
    import pymupdf
    data = Path(path).read_bytes()
    if not re.match(rb'%PDF-\d\.\d(?:\r|\n|\s)', data) or not data.rstrip().endswith(b'%%EOF'):
        raise IntakeError('INCOMPLETE_PDF_HEADER_OR_EOF')
    reader = PdfReader(BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise IntakeError('ENCRYPTED_PDF')
    if not reader.pages:
        raise IntakeError('EMPTY_PDF')
    pages = []
    with pymupdf.open(stream=data, filetype='pdf') as document:
        if document.is_encrypted or document.needs_pass or document.is_repaired:
            raise IntakeError('ENCRYPTED_OR_REPAIRED_PDF')
        if len(document) != len(reader.pages):
            raise IntakeError('PARSER_PAGE_COUNT_DISAGREEMENT')
        for number, page in enumerate(reader.pages, 1):
            content = page.get_contents()
            if content is not None:
                content.get_data()
            text = page.extract_text() or ''
            secondary_text = document[number - 1].get_text()
            pages.append({'page': number, 'textCharacters': len(text),
                          'secondaryTextCharacters': len(secondary_text), 'secondaryParserRead': True})
    return data, {'sha256': sha256(data).hexdigest(), 'bytes': len(data),
                  'pageCount': len(pages), 'pageChecks': pages,
                  'parsers': ['pypdf_strict', 'pymupdf_no_repair'], 'isRepaired': False,
                  'textLayerStatus': 'present' if any(p['textCharacters'] or p['secondaryTextCharacters'] for p in pages)
                  else 'absent_or_blank_manual_visual_review_required'}


def run_intake(selection, archive, ledger, report, max_items=None):
    from pypdf import PdfReader  # Dependency preflight before any writes.
    import pymupdf
    del PdfReader, pymupdf
    if (not isinstance(selection, dict) or selection.get('schema') != SELECTION_SCHEMA
            or set(selection) - {'schema', 'files', 'knownFiles'}
            or not isinstance(selection.get('files'), list) or not selection['files']
            or not isinstance(selection.get('knownFiles', []), list)):
        raise IntakeError('INVALID_EXPLICIT_SELECTION')
    if max_items is not None and (not isinstance(max_items, int) or max_items < 1):
        raise IntakeError('INVALID_MAX_ITEMS')
    archive, ledger, report = Path(archive).resolve(), Path(ledger).resolve(), Path(report).resolve()
    inputs = set()
    for path in selection.get('knownFiles', []):
        if not isinstance(path, str) or not Path(path).is_absolute() or re.search(r'\w+://', path):
            raise IntakeError('INVALID_KNOWN_FILE_PATH')
        inputs.add(Path(path).resolve())
    for raw in selection['files']:
        if isinstance(raw, dict) and isinstance(raw.get('path'), str) and Path(raw['path']).is_absolute():
            inputs.add(Path(raw['path']).resolve())
    if (ledger == report or ledger in inputs or report in inputs
            or ledger.suffix.lower() != '.json' or report.suffix.lower() != '.json'):
        raise IntakeError('OUTPUT_INPUT_ALIAS_OR_NON_JSON_OUTPUT')
    load_owned_json(report, REPORT_SCHEMA)
    with ledger_lock(ledger):
        return _run_intake(selection, archive, ledger, report, max_items)


def _run_intake(selection, archive, ledger, report, max_items):
    rows = []
    book = load_owned_json(ledger, LEDGER_SCHEMA) or {'schema': LEDGER_SCHEMA, 'items': {}}
    if not isinstance(book.get('items'), dict):
        raise IntakeError('INVALID_LEDGER')
    known = {}
    for path in selection.get('knownFiles', []):
        _, validation = validate_pdf(path)
        known.setdefault(validation['sha256'], str(path))
    for raw in selection['files'][:max_items]:
        try:
            safe = validate_record(raw)
            if safe['disposition'] == 'reuse':
                _, validation = validate_pdf(safe['path'])
                known.setdefault(validation['sha256'], safe['path'])
        except Exception:
            pass  # Per-item rejection is persisted below, not silently accepted.
    for index, raw in enumerate(selection['files'][:max_items]):
        key = 'invalid-' + str(index)
        record = None
        try:
            record = validate_record(raw)
            key = sha256(json.dumps(record, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            data, checks = validate_pdf(record['path'])
            previous = book['items'].get(key, {})
            if previous.get('sha256'):
                if previous['sha256'] != checks['sha256']:
                    raise IntakeError('SOURCE_SHA_CHANGED')
                previous_target = Path(previous['archivePath'])
                if not previous_target.is_file() and previous.get('status') != 'prepared':
                    raise IntakeError('PREVIOUS_ARCHIVE_MISSING')
                if previous_target.is_file() and sha256(previous_target.read_bytes()).hexdigest() != checks['sha256']:
                    raise IntakeError('PREVIOUS_ARCHIVE_SHA_MISMATCH')
            for prior in book['items'].values():
                if (prior.get('status') != 'rejected'
                        and all(prior.get(field) == record[field] for field in ('channel', 'sourceKind', 'originalFilename'))
                        and prior.get('sha256') != checks['sha256']):
                    raise ValueError('FILENAME_SHA_CONFLICT')
            dest = Path(record['path'])
            created = False
            status = 'reused_existing'
            previously_seen_bytes = any(
                prior_key != key and prior.get('sha256') == checks['sha256']
                and prior.get('status') not in ('rejected', 'prepared')
                for prior_key, prior in book['items'].items())
            if previously_seen_bytes:
                status = 'reused_ledger_bytes'  # Same bytes never prove identity; use current explicit source.
            elif checks['sha256'] in known:
                dest = Path(known[checks['sha256']])
                status = 'reused_known_bytes'
            elif record['disposition'] == 'new_download':
                dest = archive / record['sourceKind'] / record['channel'] / (checks['sha256'] + '.pdf')
                if previous.get('sha256') and previous['sha256'] != checks['sha256']:
                    raise IntakeError('SOURCE_SHA_CHANGED')
                if previous.get('status') not in (None, 'prepared', 'rejected') and not dest.exists():
                    raise IntakeError('PREVIOUS_ARCHIVE_MISSING')
                book['items'][key] = {**record, **checks, 'archivePath': str(dest),
                                       'status': 'prepared', 'createdThisRun': False}
                atomic_write_json(ledger, book)
                created = publish_pdf(dest, data, checks['sha256'])
                status = 'archived_new' if created else ('recovered_existing'
                         if previous.get('status') == 'prepared' else 'reused_existing')
            if sha256(dest.read_bytes()).hexdigest() != checks['sha256']:
                raise IntakeError('ARCHIVE_READBACK_SHA_MISMATCH')
            row = {**record, **checks, 'index': index, 'itemKey': key, 'status': status,
                   'archivePath': str(dest), 'createdThisRun': created,
                   'archiveDate': record['filenameDate'] if record['channel'] == '知识星球'
                   else record['publicationDate'],
                   'firstAvailableDate': None, 'historicalAsOfEligible': False,
                   'archiveDateBasis': 'original_filename_date' if record['channel'] == '知识星球'
                   else 'supplied_publication_date_pending_body_check',
                   'manualIdentityReviewRequired': True,
                   'identityStatus': 'pending_human_filename_content_correspondence',
                   'sourceKindVerification': 'declared_pending_human_provenance_check',
                   'validation': 'header+EOF; strict pypdf; unrepaired PyMuPDF; every page; byte SHA readback'}
            book['items'][key] = row
            rows.append(row)
        except Exception as error:
            row = {'index': index, 'itemKey': key, 'status': 'rejected',
                   'reasonCode': str(error) if isinstance(error, IntakeError) or str(error) == 'FILENAME_SHA_CONFLICT' else type(error).__name__}
            if record is not None:
                row.update(record)  # Raw rejected metadata (including credentials) never saved.
            rows.append(row)
            if key in book['items'] and book['items'][key].get('sha256'):
                book['items'][key]['lastRejection'] = row
            else:
                book['items'][key] = row
        book['updatedAt'] = datetime.now().astimezone().isoformat()
        atomic_write_json(ledger, book)
    created = [row for row in rows if row.get('createdThisRun')]
    result = {'schema': 'replay.pdf.intake.report.v1',
              'verifiedAt': datetime.now().astimezone().isoformat(),
              'selectedCount': len(selection['files']), 'processedCount': len(rows),
              'validationComplete': len(rows) == len(selection['files']) and not any(r['status'] == 'rejected' for r in rows),
              'manualReviewRequired': True, 'localPrivateOnly': True, 'noBrowserNetworkOrCredentials': True,
              'knownFilesCount': len(selection.get('knownFiles', [])),
              'countMeaning': 'physical new PDF archive writes this run, not independent report identities or verified provenance',
              'validatedPdfCount': sum(r['status'] != 'rejected' for r in rows),
              'rejectedCount': sum(r['status'] == 'rejected' for r in rows),
              'newPdfCount': len(created),
              'newOriginalPdfCount': sum(r['sourceKind'] == 'original_pdf' for r in created),
              'newWebpagePrintCount': sum(r['sourceKind'] == 'webpage_print' for r in created),
              'acceptedOriginalBodyCount': 0,
              'newZsxqOriginalPdfCount': sum(r['channel'] == '知识星球' and r['sourceKind'] == 'original_pdf' for r in created),
              'items': rows}
    atomic_write_json(report, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('selection', 'archive', 'ledger', 'report'):
        parser.add_argument('--' + flag, required=True, type=Path)
    parser.add_argument('--max-items', type=int, help='Process first N records; rerun without this flag to resume')
    args = parser.parse_args(argv)
    try:
        if args.selection.resolve() in {args.ledger.resolve(), args.report.resolve()}:
            raise IntakeError('SELECTION_OUTPUT_ALIAS')
        selection = json.loads(args.selection.read_text(encoding='utf-8-sig'))
        result = run_intake(selection, args.archive, args.ledger, args.report, args.max_items)
    except Exception as error:
        reason = str(error) if isinstance(error, IntakeError) else type(error).__name__
        if isinstance(error, ImportError):
            reason = 'PARSER_MISSING_INSTALL_PYPDF_IN_ISOLATED_UV_ENV'
        print(json.dumps({'status': 'blocked', 'reasonCode': reason}), file=sys.stderr)
        return 2
    print(json.dumps({key: result[key] for key in ('selectedCount', 'processedCount',
        'validationComplete', 'validatedPdfCount', 'rejectedCount', 'newPdfCount',
        'newOriginalPdfCount', 'newWebpagePrintCount', 'newZsxqOriginalPdfCount', 'manualReviewRequired')}))
    return 1 if result['rejectedCount'] else (0 if result['validationComplete'] else 3)


if __name__ == '__main__':
    raise SystemExit(main())
