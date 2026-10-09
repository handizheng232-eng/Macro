"""Offline archive-backed coverage; search results never count as obtained bodies."""
import hashlib
import json
import re
from datetime import date
from pathlib import Path

CHANNELS = ('知识星球', 'Wind', '微信公众号')
REQUIRED_COUNTS = {'知识星球': 20, 'Wind': 10, '微信公众号': 5}

def source_quality_verified(report, channel):
    quality = report.get('sourceQuality', {})
    if not all(quality.get(k) is True for k in ('parentLedgerVerified', 'originalBodyVerified', 'datePolicyVerified', 'scopeVerified')):
        return False
    if channel == '知识星球':
        return quality.get('tag') == '调研纪要' and quality.get('versionType') in (
            'original_audio_transcript_pdf', 'platform_original_full_speech_transcript',
            'platform_original_continuous_transcript')
    if channel == 'Wind':
        return quality.get('versionType') == 'institutional_research_pdf' and quality.get('printedPublicationVerified') is True
    return quality.get('officialHeaderVerified') is True and quality.get('versionType') == 'official_original_article_text'

AUDIT_REASON_ZH = {
    'No verified full-month search; 0 files does not mean 0 matches.': '逐月检索未完成；零文件不等于零发布。',
    'Only the prior January 美联储 title branch was searched and not exhausted. Four PDFs print 2026-01-29; the fifth lacks a verified printed publication date and is not date-qualified for January.': '1月仅检索部分标题：4份印刷日可核，1份日期待核；检索未穷尽。',
    'No authenticated Edge original-account article body collected; separate public search audit covered six accounts × eight months and found no qualifying full original body.': '未取得可核公众号原文；公共检索六账号八个月未补齐正文。',
    'RPP title searches executed in prior batch but not exhausted; this batch saved one February PDF.': '新增1份2月原版PDF；RPP检索范围未穷尽。',
    'Date-picker actions did not establish a valid monthly search.': '日期筛选未完成有效逐月检索。',
    'Official site file search only partially inspected; not an exhaustive monthly search.': '星球附件仅局部检索；未穷尽该月结果。',
}


def load_monthly_audits(stage):
    audits = {}
    latest = None
    latest_wind_acquisition_after = None
    for folder in sorted((Path(stage) / '核验').glob('逐月补采20*')):
        for path in sorted(folder.glob('*monthly-audit*.json')):
            for row in json.loads(path.read_text(encoding='utf-8')).get('rows', []):
                if row.get('month') and row.get('channel'):
                    gap = row.get('gap', '')
                    audits[(row['month'], row['channel'])] = {
                        **row, 'reason': row.get('reason') or AUDIT_REASON_ZH.get(gap, gap)}
        for path in sorted(folder.glob('wind-rpp-monthly-receipts-*.json')):
            receipt = json.loads(path.read_text(encoding='utf-8'))
            latest_wind_acquisition_after = receipt.get('normalGuiAcquisitionAfter') or latest_wind_acquisition_after
            for row in receipt.get('rows', []):
                month = row.get('month')
                if not month:
                    continue
                audits[(month, 'Wind')] = {
                    **row, 'channel': 'Wind',
                    'searchExecuted': row.get('searchExecutedThisRun') is True,
                    'searchComplete': row.get('searchComplete') is True,
                    'matchedCount': row.get('resultCountTitle'),
                    'reason': row.get('gap', ''), 'status': 'acquired_limited_sample'}
        for path in sorted(folder.glob('gui-resume-checkpoint-*.json')):
            latest = json.loads(path.read_text(encoding='utf-8')).get('resumeAttempt') or latest
        for path in sorted(folder.glob('gui-monthly-audit-*.json')):
            blocker = json.loads(path.read_text(encoding='utf-8')).get('blocker')
            if blocker:
                latest = {'status': 'blocked_windows_lock', 'observedAt': blocker.get('observedAt'),
                          'reason': blocker.get('state')}
        tag_path = folder / 'gui-monthly-audit-incremental.json'
        if tag_path.exists():
            tag_audit = json.loads(tag_path.read_text(encoding='utf-8'))
            for month, row in tag_audit.get('months', {}).items():
                # A traversed hashtag feed is not a complete search of the month's
                # documents. Candidates and attachment rows are not original PDFs.
                scope = row.get('searchCompleteScope', '局部逐帖页面')
                note = row.get('note', '').rstrip('。； ')
                audits[(month, '知识星球')] = {
                    'month': month, 'channel': '知识星球',
                    'searchExecuted': row.get('searchExecutedThisRun') is True,
                    'searchComplete': False, 'matchedCount': None,
                    'status': 'partial_tag_feed_only',
                    'reason': f'{scope}；该标签审计批次备注（非后续下载状态）：{note}；整月完整检索未完成。' if note else
                              f'{scope}；整月完整检索未完成。',
                }
    return {'rows': list(audits.values()), 'latestGuiCheck': latest,
            'latestWindGuiAcquisitionAfter': latest_wind_acquisition_after}


def channel_of(report):
    channel = report.get('channel')
    if channel in ('微信', '微信公众号'):
        return '微信公众号'
    if channel in CHANNELS:
        return channel
    path = str(report.get('path') or report.get('bodyPath') or report.get('localPath') or '').replace('\\', '/').lower()
    if '/报告/知识星球/' in '/' + path:
        return '知识星球'
    if '/报告/wind/' in '/' + path:
        return 'Wind'
    if '/资料/微信公众号/' in '/' + path:
        return '微信公众号'
    return None  # Local reuse is not evidence of acquisition from its original channel.


def archive_date(report, channel):
    if channel == '知识星球':
        value = report.get('filenameDate')  # User's channel-specific archive-date policy.
    elif (channel == 'Wind' and report.get('publicationDate') is None and
          report.get('publicationDatePrecision') == 'month' and source_quality_verified(report, channel)):
        month = report.get('verifiedPublicationMonth')
        if isinstance(month, str) and re.fullmatch(r'\d{4}-\d{2}', month):
            try:
                date.fromisoformat(month + '-01')
                return month
            except ValueError:
                return None
        return None
    elif 'publicationDate' in report:
        value = report['publicationDate']  # Explicit null cannot be replaced by a batch filename.
    else:
        basis = report.get('dateBasis', '')
        verified_basis = ('封面', '正文日期', 'printed_publication_date') if channel == 'Wind' else ('页头', '官方', 'header', 'publication')
        value = report.get('date') if any(token in basis for token in verified_basis) else None
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def months_between(start, end):
    year, month = date.fromisoformat(start).year, date.fromisoformat(start).month
    result = []
    while f'{year:04d}-{month:02d}' <= end[:7]:
        result.append(f'{year:04d}-{month:02d}')
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return result


def verified_shortage_proofs(audit, root, stage):
    """Only caller-authorized parent path/SHA bindings, never search-log booleans."""
    from replay_parent_sources import pinned_json, resolve
    result = {}
    for binding in (audit or {}).get('trustedShortageProofs', []):
        proof = pinned_json(binding['path'], binding['sha256'], stage, root)
        total = proof.get('actualEligibleTotal')
        if (proof.get('channel') != '知识星球' or proof.get('requiredTopicTag') != '调研纪要' or
                proof.get('onlyOriginalPdf') is not True or proof.get('searchExecuted') is not True or
                proof.get('searchExhaustive') is not True or proof.get('blocked') is not False or
                type(total) is not int or not 0 <= total < 20 or not proof.get('evidenceArtifacts') or
                len(proof.get('eligibleWorks', [])) != total):
            continue
        for artifact in proof['evidenceArtifacts']:
            raw = resolve(artifact['path'], stage, root).read_bytes()
            if hashlib.sha256(raw).hexdigest() != artifact['sha256']:
                raise ValueError('Actual shortage search artifact SHA mismatch')
        keys = [work.get('independentWorkId') for work in proof['eligibleWorks']]
        if any(not key for key in keys) or len(set(keys)) != total:
            continue
        key = (proof.get('month'), '知识星球')
        if key in result:
            raise ValueError('Duplicate parent shortage proof')
        result[key] = {**proof, 'proofSHA256': binding['sha256']}
    return result


def build_monthly_coverage(start, end, reports, root, stage, audit=None):
    root, stage = Path(root), Path(stage)
    months = months_between(start, end)
    shortage_proofs = verified_shortage_proofs(audit, root, stage)
    cells = {(month, channel): {'entries': [], 'bodies': {}, 'distribution': []} for month in months for channel in CHANNELS}
    unassigned = 0
    for report in reports:
        channel = channel_of(report)
        if not channel:
            continue
        published = archive_date(report, channel)
        if not published:
            unassigned += 1
            continue
        if not (start[:7] <= published <= end[:7] if len(published) == 7 else start <= published <= end):
            continue
        raw_path = report.get('path') or report.get('bodyPath') or report.get('localPath')
        if not raw_path:
            continue
        artifact = Path(raw_path)
        if not artifact.is_absolute():
            artifact = root / raw_path
            if not artifact.is_file():
                artifact = stage / raw_path
        if not artifact.is_file():
            raise ValueError(f'Missing monthly archive: {report.get("id", raw_path)}')
        payload = artifact.read_bytes()
        sha = hashlib.sha256(payload).hexdigest()
        declared = report.get('sha256') or report.get('bodySha256')
        if not declared:
            # Old bibliographic entries are not admitted originals. They must
            # remain unassigned, not crash sibling builds or gain a body vote.
            if not source_quality_verified(report, channel):
                unassigned += 1
                continue
            raise ValueError(f'Missing SHA in monthly archive: {report.get("id", raw_path)}')
        if sha != declared:
            raise ValueError(f'SHA mismatch in monthly archive: {report.get("id", raw_path)}')
        if channel in ('知识星球', 'Wind') and b'%PDF-' not in payload[:1024]:
            raise ValueError(f'Not a PDF monthly archive: {report.get("id", raw_path)}')
        if not payload.strip():
            raise ValueError(f'Empty monthly archive: {report.get("id", raw_path)}')
        cell = cells[(published[:7], channel)]
        cell['entries'].append(report.get('id') or raw_path)
        if not source_quality_verified(report, channel):
            continue
        work_id = report.get('independentWorkId') or report.get('originReportId') or 'sha256:' + sha
        archive = {'sha256': sha, 'path': str(raw_path), 'date': published,
                   'title': report.get('title', ''), 'reportId': report.get('id'),
                   'independentWorkId': work_id, 'sourceQuality': report['sourceQuality']}
        cell['distribution'].append(archive)
        cell['bodies'].setdefault(work_id, archive)
    audits = {}
    for row in (audit or {}).get('rows', []):
        channel = '微信公众号' if row.get('channel') == '微信' else row.get('channel')
        if row.get('month') in months and channel in CHANNELS:
            audits[(row['month'], channel)] = row
    rows = []
    covered = 0
    for month in months:
        channels = {}
        for channel in CHANNELS:
            cell = cells[(month, channel)]
            receipt = audits.get((month, channel), {})
            searched = receipt.get('searchExecuted') is True
            search_complete = receipt.get('searchComplete') is True
            blocked = 'blocked' in receipt.get('status', '').lower() or '受阻' in receipt.get('status', '')
            count = len(cell['bodies'])
            covered += bool(count)
            status = ('已有正文·检索受阻' if count else '采集受阻') if blocked else (
                '已覆盖·逐月检索已核' if count and search_complete else
                '已有正文·逐月检索未完成' if count and searched else
                '已有正文·逐月检索待核' if count else '未取得正文')
            proof = shortage_proofs.get((month, channel))
            shortage_verified = False
            if proof and not blocked:
                from replay_parent_sources import resolve
                obtained = {(a['independentWorkId'], a['sha256'], resolve(a['path'], stage, root), a['date'])
                            for a in cell['bodies'].values()}
                eligible = {(a['independentWorkId'], a['sha256'], resolve(a['path'], stage, root), a['date'])
                            for a in proof['eligibleWorks']}
                shortage_verified = count == proof['actualEligibleTotal'] and obtained == eligible
            account_count = len({a['sourceQuality'].get('account') for a in cell['bodies'].values()
                                 if a['sourceQuality'].get('account')})
            quota_accepted = ((count >= REQUIRED_COUNTS[channel] or shortage_verified) and not blocked and
                              (channel != '微信公众号' or account_count >= 2))
            basis = ('minimum_verified_originals' if count >= REQUIRED_COUNTS[channel] and quota_accepted else
                     'verified_actual_eligible_total' if shortage_verified else 'insufficient_verified_originals')
            if shortage_verified:
                status = f'真实符合{count}份·已全部归档核验'
            elif quota_accepted:
                status = '月度储备达标·' + ('检索已穷尽' if receipt.get('searchExhaustive') is True else '检索未穷尽')
            elif count and not blocked:
                status = f'已核原文{count}/{REQUIRED_COUNTS[channel]}份·月度验收不足'
            channels[channel] = {'bodyCount': count, 'verifiedBodyCount': count,
                                 'requiredCount': REQUIRED_COUNTS[channel], 'quotaAccepted': quota_accepted,
                                 'acceptanceBasis': basis, 'shortageEvidenceVerified': shortage_verified,
                                 'shortageEvidence': ({'actualEligibleTotal': proof['actualEligibleTotal'],
                                      'proofSHA256': proof['proofSHA256'], 'month': month, 'channel': channel,
                                      'requiredTopicTag': '调研纪要', 'onlyOriginalPdf': True,
                                      'searchExecuted': True, 'searchExhaustive': True, 'blocked': False}
                                      if shortage_verified else None),
                                 'searchExhaustive': True if shortage_verified else receipt.get('searchExhaustive', False),
                                 'rawSearchExhaustive': receipt.get('searchExhaustive', False),
                                 'blocked': blocked,
                                 'archiveEntries': len(cell['entries']), 'accountCount': account_count,
                                 'distributionRecords': cell['distribution'],
                                 'searchExecuted': searched or shortage_verified, 'searchComplete': search_complete, 'status': status,
                                 'reason': receipt.get('reason', ''),
                                 'matchedCount': receipt.get('matchedCount'),
                                 'archives': list(cell['bodies'].values()),
                                 'covered': bool(count), 'accepted': quota_accepted}
        rows.append({'month': month, 'channels': channels})
    required = len(months) * len(CHANNELS)
    accepted = sum(cell['accepted'] for row in rows for cell in row['channels'].values())
    return {'startDate': start, 'endDate': end, 'rows': rows, 'requiredCells': required,
            'coveredCells': covered, 'acceptedCells': accepted, 'complete': accepted == required,
            'unassignedArchiveEntries': unassigned,
            'basis': '正文实物、SHA及渠道日期核验；逐月检索另核。星球文件名日仅用于归档，不证明历史首次可得；其他渠道不以文件名替代正文发表日。'}
