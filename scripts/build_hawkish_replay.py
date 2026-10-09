"""Assemble the Jan-Aug 2026 replay from independently archived evidence.

No network/authentication access. Missing inputs stay explicit; --allow-partial is
only for development, never a claim that the research is complete.
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from replay_monthly_coverage import build_monthly_coverage, load_monthly_audits, channel_of
from replay_public_export import public_snapshot
from replay_parent_sources import load_parent_sources, DEFAULT_SOURCES, resolve
from replay_reviewed_analysis import reviewed_analysis
from replay_research_integration import integrate_reviewed

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '美国宏观复盘/降息起步后的双向政策时代/2026-01_2026-08'
CUTOFF = '2026-08-31'

REPORT_PUBLIC_FIELDS = {
    'id', 'title', 'date', 'publicationDate', 'publicationDatePrecision', 'verifiedPublicationMonth',
    'postDate', 'filenameDate', 'dateBasis', 'dateConflict', 'provider', 'institution', 'path',
    'archiveRelativePath', 'sha256', 'bodySha256', 'bytes', 'pageCount', 'paragraphCount',
    'scope', 'note', 'geography', 'topics', 'accountActual', 'authors', 'researchOrigin',
    'distributionType', 'channel', 'firstAvailableDate', 'historicalAsOfEligible',
    'sourceQuality', 'downloadedThisRun', 'independentWorkId', 'identityBasis',
    'sharedDocumentWith', 'originReportId', 'countsAsIndependentDocument', 'countsAsAdditionalOpinion',
}
QUALITY_PUBLIC_FIELDS = {'status', 'parentLedgerVerified', 'originalBodyVerified', 'datePolicyVerified',
    'scopeVerified', 'tag', 'versionType', 'institutionIdentityIndependentlyVerified',
    'recordingCompletenessVerified', 'imageOCRComplete', 'printedPublicationVerified',
    'officialHeaderVerified', 'account', 'underlyingFullReportObtained'}



def load(stage, name, fallback):
    path = stage / '研究' / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else fallback

def incremental_channel_reports(original, batches):
    reports = [dict(report) for report in original]
    by_id = {report.get('id'): report for report in reports}
    for batch in batches:
        for report in batch:
            prior = by_id.get(report.get('id'))
            if prior:
                same_sha = bool(prior.get('sha256') and prior['sha256'] == report.get('sha256'))
                same_channel = prior.get('channel') == report.get('channel')
                if not same_sha or not same_channel:
                    raise ValueError(f'Duplicate incremental identity conflict: {report.get("id")}')
                # A monthly selection of an existing archive is not a new report.
                continue
            reports.append(dict(report))
            by_id[report.get('id')] = reports[-1]
    return reports

def acquired_after_block(acquisition_after, blocked_at):
    if not acquisition_after or not blocked_at:
        return False
    try:
        return datetime.fromisoformat(acquisition_after) > datetime.fromisoformat(blocked_at.replace(' +', '+'))
    except (TypeError, ValueError):
        return False

def build(stage=STAGE, root=ROOT, allow_partial=False, parent_sources=None, shortage_proofs=None, reviewed_research_manifest=None):
    stage, root = Path(stage), Path(root)
    official = load(stage, 'official-evidence.json', {'sources': [], 'events': []})
    local = load(stage, 'local-bibliography.json', {'articles': []})
    legacy_books = [load(stage, name, {'articles': []}) for name in (
        'channel-bibliography.json', 'channel-monthly-bibliography.json',
        'channel-monthly-20261007-bibliography.json', 'channel-monthly-20261007-wind-gui-incremental.json',
        'channel-monthly-20261008-zsxq-cdp-first-bibliography.json',
        'channel-monthly-20261008-zsxq-cdp-batch02-bibliography.json',
        'channel-monthly-20261008-zsxq-cdp-parent03-bibliography.json', 'wechat-monthly-bibliography.json')]
    # Legacy books are an ID compatibility index only; they cannot admit a body.
    legacy = incremental_channel_reports([], [b.get('articles', b.get('items', [])) for b in legacy_books])
    parent_reports, parent_audits = load_parent_sources(stage, root, parent_sources)
    source_remap = {}
    for report in parent_reports:
        compatible = [r for r in legacy if (r.get('sha256') or r.get('bodySha256')) == report['sha256']
                      and channel_of(r) == channel_of(report)]
        if compatible:
            canonical_id = report['id']
            report['id'] = compatible[0]['id']
            source_remap[canonical_id] = report['id']
            for old_report in compatible:
                source_remap[old_report['id']] = report['id']
    admitted = {r['id'] for r in parent_reports}
    denied_source_ids = {r['id'] for r in legacy if r['id'] not in source_remap and r['id'] not in admitted}
    channels = {'articles': parent_reports, 'audit': legacy_books[0].get('audit', [])}
    cdp_channels = [r for r in parent_reports if channel_of(r) == '知识星球']
    wind_gui_channels = {'articles': []}
    local_views = load(stage, 'local-expectation-evidence.json', {'items': []})
    collections = [load(stage, name, {'items': []}) for name in (
        'channel-expectation-evidence.json', 'wechat-monthly-expectation-evidence.json',
        'channel-monthly-expectation-evidence.json', 'channel-monthly-parent-expectation-evidence.json',
        'channel-monthly-20261007-expectation-evidence.json',
        'channel-monthly-20261007-wind-gui-expectation-evidence.json')]
    parent_pdf_views = collections[3]
    accepted_by_id = {r['id']: r for r in parent_reports}
    views, view_ids = [], set()
    for collection in collections:
        for item in collection.get('items', []):
            rid = source_remap.get(item.get('reportId'), item.get('reportId'))
            report = accepted_by_id.get(rid)
            if not report:
                continue  # Known denied sources never leak their opinions/titles.
            if item.get('evidenceSha256') and item['evidenceSha256'] != report['sha256']:
                raise ValueError('Opinion evidence SHA differs from admitted original')
            if item.get('id') and item['id'] in view_ids:
                raise ValueError('Duplicate opinion identity')
            if item.get('id'):
                view_ids.add(item['id'])
            views.append({**item, 'reportId': rid, 'channel': report['channel'],
                          'firstAvailableDate': report['firstAvailableDate'],
                          'historicalAsOfEligible': report['historicalAsOfEligible'],
                          'sourceQuality': report['sourceQuality']})
    channel_views = {'items': views}
    analysis = load(stage, 'market-analysis.json', None)
    if analysis:
        analysis = reviewed_analysis(stage, analysis)
    paths = load(stage, 'market-paths.json', {'series': []})
    excluded_ids = {s['id'] for s in official.get('sources', []) if s.get('scope') == 'verification-only'} | denied_source_ids
    if analysis:
        invalid = False
        for section in analysis.get('sections', []):
            if (set(section.get('reportIds', [])) | set(section.get('sourceIds', []))) & denied_source_ids:
                invalid = True
                for field in ('judgement', 'expectation', 'reality', 'mechanism', 'divergence', 'implication', 'validation'):
                    section[field] = '旧引用来源未通过当前原文范围验收；本节待重新核验，不沿用原判断。'
                section['reportIds'], section['sourceIds'] = [], []
        if invalid:
            analysis['conclusion'] = '部分旧引用未通过当前原文范围验收；综合判断待重新核验。'
    def presentation_copy(value):
        if isinstance(value, str):
            if value in source_remap:
                return source_remap[value]
            for prior, current in source_remap.items():
                value = value.replace('[' + prior + ']', '[' + current + ']')
            for excluded in excluded_ids:
                value = value.replace('[' + excluded + ']', '')
            return value
        if isinstance(value, list):
            return [presentation_copy(v) for v in value if not
                    (isinstance(v, str) and v in excluded_ids or isinstance(v, dict) and
                     (v.get('id') in excluded_ids or v.get('reportId') in denied_source_ids))]
        if isinstance(value, dict):
            if value.get('reportId') in denied_source_ids:
                return None
            return {k: presentation_copy(v) for k, v in value.items()}
        return value
    analysis = presentation_copy(analysis)
    comparisons = presentation_copy(load(stage, 'expectation-reality-pairs.json', {'pairs': [], 'eventExpectations': []}))
    sources = [dict(s) for s in official.get('sources', []) if s.get('scope') != 'verification-only']
    reports = [{k: v for k, v in a.items() if k in REPORT_PUBLIC_FIELDS}
               for a in local.get('articles', []) + channels.get('articles', [])]
    for report in reports:
        report['sourceQuality'] = {k: v for k, v in report.get('sourceQuality', {'status': 'unknown'}).items()
                                   if k in QUALITY_PUBLIC_FIELDS}
        report['firstAvailableDate'] = report.get('firstAvailableDate')
    events = list(official.get('events', []))
    report_ids = set()
    for report in reports:
        rid = report.get('id')
        if not rid or rid in report_ids:
            raise ValueError(f'Duplicate report or missing identity: {rid}')
        report_ids.add(rid)
        archive_path = report.get('path') or report.get('localPath') or report.get('bodyPath')
        sha = report.get('sha256') or report.get('bodySha256')
        if sha:
            if not archive_path:
                raise ValueError(f'SHA without archive path: {rid}')
            artifact = Path(archive_path)
            if not artifact.is_absolute():
                artifact = root / artifact
                if not artifact.is_file():
                    artifact = stage / archive_path
            if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != sha:
                raise ValueError(f'SHA mismatch or missing archive: {rid}')
            report['archiveRelativePath'] = archive_path
            report['path'] = artifact.relative_to(root).as_posix() if artifact.is_relative_to(root) else str(artifact)
        # A verified printed date is not proof of historical first availability.
        report['historicalAsOfEligible'] = bool(report.get('historicalAsOfEligible')
                                               and report.get('firstAvailableDate'))
    document_groups = {}
    for report in reports:
        identity = report.get('sha256') or report.get('bodySha256') or report['id']
        document_groups.setdefault(identity, []).append(report['id'])
    for report in reports:
        identity = report.get('sha256') or report.get('bodySha256') or report['id']
        peers = [rid for rid in document_groups[identity] if rid != report['id']]
        if peers:
            report['sharedDocumentWith'] = peers
            report['note'] = report.get('note', '') + ' 同SHA原文跨渠道复用，与' + '、'.join(peers) + '不构成独立证据。'
    source_aliases = [presentation_copy(alias) for alias in parent_pdf_views.get('sourceAliases', [])
                      if source_remap.get(alias.get('reportId'), alias.get('reportId')) in report_ids
                      and alias.get('originReportId') in report_ids]
    report_by_id = {report['id']: report for report in reports}
    for report in wind_gui_channels.get('articles', []):
        if not report.get('sameUnderlyingReportAs'):
            continue
        copy = report_by_id[report['id']]
        origin = next((candidate for candidate in reports
                       if candidate.get('archiveRelativePath') == report['sameUnderlyingReportAs']), None)
        if not origin or origin['id'] == copy['id']:
            raise ValueError('Unknown Wind GUI duplicate origin')
        copy['originReportId'] = origin['id']
        copy['countsAsIndependentDocument'] = False
        copy['sharedDocumentWith'] = list(dict.fromkeys(copy.get('sharedDocumentWith', []) + [origin['id']]))
        origin['sharedDocumentWith'] = list(dict.fromkeys(origin.get('sharedDocumentWith', []) + [copy['id']]))
    original_view_ids = {item.get('id') for item in local_views.get('items', [])}
    for alias in source_aliases:
        report = report_by_id.get(alias.get('reportId'))
        origin = report_by_id.get(alias.get('originReportId'))
        if not report or not origin or report is origin:
            raise ValueError('Unknown or self-referencing source alias')
        if alias.get('sha256') != report.get('sha256') or alias.get('originSha256') != origin.get('sha256'):
            raise ValueError('Source alias SHA identity mismatch')
        if alias.get('sameUnderlyingReport') is not True or alias.get('countsAsAdditionalOpinion') is not False:
            raise ValueError('Unverified or independently counted source alias')
        if not set(alias.get('duplicateOfEvidenceIds', [])) <= original_view_ids:
            raise ValueError('Unknown source alias original opinion')
        if any(item.get('reportId') == report['id'] for item in channel_views['items']):
            raise ValueError('Source alias must reuse original opinion rather than adding a duplicate')
        report.update(originReportId=origin['id'], countsAsIndependentDocument=False,
                      countsAsAdditionalOpinion=False, historicalAsOfEligible=False)
        report['sharedDocumentWith'] = list(dict.fromkeys(report.get('sharedDocumentWith', []) + [origin['id']]))
        origin['sharedDocumentWith'] = list(dict.fromkeys(origin.get('sharedDocumentWith', []) + [report['id']]))
        report['note'] = (report.get('note', '') + ' 文字层已核同文，不新增独立观点；图像未比较。' + alias.get('note', '')).strip()
    for source in sources:
        if source.get('date', '') > CUTOFF:
            raise ValueError(f'Source after cutoff: {source.get("id")}')
    for source in paths.get('sources', []):
        sources.append({**source, 'title': source.get('title') or source['id'],
            'publisher': '美国财政部' if source['id'].startswith('treasury-') else 'FRED / Federal Reserve',
            'date': source.get('publicationDate') or source.get('retrievedAt', '')[:10],
            'dateBasis': '现时追溯资料取得日期，不等于观测日或首次可得日',
            'url': source.get('url', ''), 'kind': '追溯行情与交叉核验',
            'status': '当前追溯·不纳入历史信息集', 'note': '保留真实取得日期；当前版本不能证明当时可得。',
            'retrospectiveOnly': True, 'historicalAsOfEligible': False})
    for event in events:
        if not ('2026-01-01' <= event.get('date', '') <= CUTOFF):
            raise ValueError(f'Event outside interval: {event.get("id")}')
    source_ids = {s['id'] for s in sources}
    if len(source_ids) != len(sources):
        raise ValueError('Duplicate source identity')
    for report in reports:
        if report['id'] not in source_ids:
            sources.append({'id': report['id'], 'title': report.get('title', ''),
                'publisher': report.get('provider', report.get('accountActual', '待核')),
                'date': (report.get('filenameDate') or report.get('date') or '') if channel_of(report) == '知识星球' else
                        (report.get('publicationDate') or report.get('date') or ''),
                'url': '', 'kind': '授权研究材料', 'status': '本地资料·核验见归档审计',
                'note': report.get('note', ''), 'firstAvailableDate': report['firstAvailableDate'],
                'sourceQuality': report['sourceQuality'], 'historicalAsOfEligible': report['historicalAsOfEligible']})
            source_ids.add(report['id'])
    for event in events:
        for field in ('expectationSourceIds', 'realitySourceIds'):
            if not set(event.get(field, [])) <= source_ids:
                raise ValueError(f'Unknown event source: {event.get("id")}')
        reality_sources = [s for s in sources if s['id'] in event.get('realitySourceIds', [])]
        event['availableFrom'] = max([event['date']] + [s['date'] for s in reality_sources if s.get('date')])
        event['historicalAsOfEligible'] = bool(reality_sources) and all(s.get('historicalAsOfEligible') is True for s in reality_sources)
    if analysis:
        for section in analysis.get('sections', []):
            if not set(section.get('sourceIds', [])) <= source_ids or not set(section.get('reportIds', [])) <= report_ids:
                raise ValueError(f'Unknown synthesis reference: {section.get("id")}')
    for opinion in local_views.get('items', []) + channel_views.get('items', []):
        if opinion.get('reportId') not in report_ids:
            raise ValueError('Unknown opinion report')
        report = report_by_id[opinion['reportId']]
        opinion['sourceQuality'] = report['sourceQuality']
        opinion['firstAvailableDate'] = report['firstAvailableDate']
        opinion['historicalAsOfEligible'] = report['historicalAsOfEligible']
    event_ids = {e['id'] for e in events}
    for pair in comparisons.get('pairs', []):
        if pair['reportId'] not in report_ids or not set(pair.get('realitySourceIds', [])) <= source_ids:
            raise ValueError(f'Unknown pair reference: {pair["id"]}')
        if pair.get('eventId') and pair['eventId'] not in event_ids:
            raise ValueError(f'Unknown pair event: {pair["id"]}')
        pair_report = report_by_id[pair['reportId']]
        pair['firstAvailableDate'] = pair_report['firstAvailableDate']
        pair['sourceQuality'] = pair_report['sourceQuality']
        pair['historicalAsOfEligible'] = pair_report['historicalAsOfEligible'] and all(
            s.get('historicalAsOfEligible') is True for s in sources if s['id'] in pair.get('realitySourceIds', []))
        if pair.get('futureOutcomeUsed') or pair.get('eventDate') and pair['eventDate'] > CUTOFF:
            raise ValueError(f'Pair uses future outcome: {pair["id"]}')
    for mapped in comparisons.get('eventExpectations', []):
        if mapped['eventId'] not in event_ids or not set(mapped['sourceIds']) <= source_ids:
            raise ValueError('Unknown mapped expectation reference')
        event = next(e for e in events if e['id'] == mapped['eventId'])
        event['expectation'] = mapped['text']
        event['expectationSourceIds'] = mapped['sourceIds']
        event['historicalAsOfEligible'] = event['historicalAsOfEligible'] and all(
            s.get('historicalAsOfEligible') is True for s in sources if s['id'] in mapped['sourceIds'])
    if not allow_partial and (not events or not analysis or len(analysis.get('sections', [])) != 5
                              or not any(s.get('observations') for s in paths.get('series', []))):
        raise ValueError('Research incomplete; official events, five themes and actual market observations required')
    channel_evidence = channel_views.get('items', [])
    acquisition = []
    for provider, available, count in [
        ('官方事件与行情', bool(official.get('sources')), len(official.get('sources', []))),
        ('本地授权研报', (stage / '研究/local-bibliography.json').exists(), len(local.get('articles', []))),
        *[(c, (stage / '研究/channel-bibliography.json').exists(), sum(a.get('channel') == c for a in channels.get('articles', [])))
          for c in ('知识星球', 'Wind', '微信')]]:
        acquisition.append({'provider': provider, 'status': '本批资料已接入·完整性见审计' if available else '待采集核验',
            'detail': f'实际接入{count}条；不代表完整区间检索或独立机构数量。' if available else '尚无可核验归档；匹配数量未知，不将未执行检索写成0匹配。'})
        audit = next((a for a in channels.get('audit', []) if a.get('channel') == provider), None)
        if audit:
            blocked = 'blocked' in audit.get('status', '')
            acquisition[-1]['status'] = ('部分复用·实时采集受阻' if count else '未取得正文·采集受阻') if blocked else '有限样本·未完成全窗口'
            acquisition[-1]['detail'] = f'本批实际归档{count}份，新下载{audit.get("downloadedCount", 0)}份；检索完整性未确认。' + audit.get('reason', '')
    data = {'title': '鹰派换届与反转酝酿', 'startDate': '2026-01-01', 'endDate': CUTOFF,
        'asOf': CUTOFF, 'workbenchLabel': '鹰派换届研究工作台',
        'eyebrow': 'HAWKISH TRANSITION · RESEARCH WORKBENCH',
        'summary': ['资料正在采集与独立核验；未形成研究结论。'] if not analysis else [analysis['conclusion']],
        'sources': sources, 'events': sorted(events, key=lambda e: e['date']), 'reports': reports,
        'hypotheses': load(stage, 'hypotheses.json', []), 'acquisition': acquisition,
        'localResearchEvidence': local_views.get('items', []),
        'researchEvidence': [v for v in channel_evidence if v.get('channel') == '知识星球'],
        'windResearchEvidence': [v for v in channel_evidence if v.get('channel') == 'Wind'],
        'wechatResearchEvidence': [v for v in channel_evidence if v.get('channel') == '微信'],
        'marketPaths': paths,
        'realityComparisons': comparisons.get('pairs', []),
        'reportIdAliases': source_remap,
        'sourceAliases': source_aliases,
        'archiveCoverage': {'channelEntries': len(reports), 'uniqueDocuments': len(document_groups),
                            'sharedDocuments': sum(len(ids) > 1 for ids in document_groups.values()),
                            'textVerifiedAliasCount': len(source_aliases)}}
    if analysis:
        data['marketAnalysis'] = analysis
    coverage = load(stage, 'wechat-coverage.json', None)
    wechat_reports = [r for r in reports if r.get('channel') in ('微信', '微信公众号')]
    if coverage or wechat_reports:
        coverage = dict(coverage or {'requestedAccounts': [], 'limitations': []})
        accounts = {}
        for report in wechat_reports:
            account = report.get('accountActual') or report.get('provider', '未确认')
            accounts[account] = accounts.get(account, 0) + 1
        coverage.update(totalArticles=len(wechat_reports), totalOpinions=len(data['wechatResearchEvidence']),
            actualAccounts=[{'accountActual': account, 'articleCount': count} for account, count in accounts.items()])
        data['wechatCoverage'] = coverage
    monthly_audits = load_monthly_audits(stage)
    for receipt in parent_audits:
        prior = next((a for a in reversed(monthly_audits['rows']) if a.get('month') == receipt['month'] and
                      ('微信公众号' if a.get('channel') == '微信' else a.get('channel')) == receipt['channel']), None)
        if prior:
            receipt['searchExecuted'] = receipt['searchExecuted'] or prior.get('searchExecuted') is True
        if prior and prior.get('reason'):
            receipt['reason'] += ' 原检索记录：' + prior['reason']
        monthly_audits['rows'].append(receipt)
    monthly_audits['trustedShortageProofs'] = shortage_proofs or []
    data['monthlyCoverage'] = build_monthly_coverage(data['startDate'], CUTOFF, reports, root, stage, monthly_audits)
    # New receipts supersede historical failed-acquisition prose, not original evidence.
    for entry in acquisition:
        channel = '微信公众号' if entry['provider'] == '微信' else entry['provider']
        receipts = [row for row in monthly_audits['rows'] if row.get('channel') in
            (('微信公众号', '微信') if channel == '微信公众号' else (channel,))]
        if not receipts:
            continue
        archived = [report for report in reports if channel_of(report) == channel]
        if channel == '知识星球' and cdp_channels:
            downloaded = sum(report.get('downloadedThisRun') is True for report in cdp_channels)
        else:
            downloaded = (len(wind_gui_channels.get('articles', [])) if channel == 'Wind' and
                          wind_gui_channels.get('articles') else
                          sum(report.get('downloadedThisRun') is True for report in archived))
        cells = [row['channels'][channel] for row in data['monthlyCoverage']['rows']]
        covered_months = sum(cell['covered'] for cell in cells)
        blocked = any('blocked' in row.get('status', '').lower() or '受阻' in row.get('status', '') for row in receipts)
        entry['status'] = ('有限样本已接入' if archived else '未取得正文') + ('·续采受阻' if blocked else '·逐月范围见覆盖表')
        reasons = list(dict.fromkeys(row.get('reason', '') for row in receipts if row.get('reason')))
        entry['detail'] = (f'实际归档{len(archived)}份，新增下载{downloaded}份；'
            f'有日期正文覆盖{covered_months}/{len(cells)}个月，未证明全区间穷尽。' + ' '.join(reasons))
        latest = monthly_audits.get('latestGuiCheck')
        if latest and latest.get('status', '').startswith('blocked') and not (
            channel == 'Wind' and acquired_after_block(monthly_audits.get('latestWindGuiAcquisitionAfter'),
                                                        latest.get('observedAt'))):
            entry['status'] = ('有限样本已接入' if archived else '未取得正文') + '·续采受阻'
            entry['detail'] += f' 最新GUI检查（{latest.get("observedAt", "时间待核")}）：{latest.get("reason", "")}'
        parent_archives = [r for r in parent_reports if channel_of(r) == channel]
        if parent_archives:
            accepted_months = sum(cell['accepted'] for cell in cells)
            entry['status'] = ('月度最低原文验收达标' if accepted_months == len(cells) else '真实原文已核·月度验收仍不足') + '·检索未穷尽'
            entry['detail'] = (f'实际归档{len(archived)}份，新增下载{downloaded}份；'
                               f'月度验收{accepted_months}/{len(cells)}；检索未穷尽，不代表网站实际全部符合数量。')
            if channel == '微信公众号':
                entry['detail'] = (f'实际归档{len(archived)}篇完整原发文章；月度验收{accepted_months}/{len(cells)}；'
                                   '累计量已核，文章捕获不冒称研报PDF下载；检索未穷尽。')
    if reviewed_research_manifest is not None:
        data = integrate_reviewed(data, reviewed_research_manifest, stage, root)
    return data

PUBLIC_EVIDENCE_FIELDS = {
    'id', 'reportId', 'eventId', 'expressedAt', 'dateBasis', 'actor', 'claim', 'scope',
    'value', 'unit', 'observationPeriod', 'pages', 'evidenceExcerpt', 'limitations',
    'reportTitle', 'localPath', 'reality', 'eventDate', 'status', 'claimType',
    'firstAvailableDate', 'historicalAsOfEligible', 'channel', 'sourceQuality',
    'evidenceSha256', 'evidenceExcerptSha256Utf8', 'excerptLocations', 'supportingTextSpans',
    'conditions', 'forecastHorizon', 'countsAsAdditionalOpinion', 'countsAsIndependentDocument',
    'isMarketConsensus', 'sourceActor', 'originReportId', 'sharedDocumentWith', 'authorIdentity',
    'sha256', 'originSha256', 'sameUnderlyingReport', 'sameBytes', 'duplicateOfEvidenceIds', 'note',
    'realitySourceIds', 'attributionStatus',
}


def publication_snapshot(data, root):
    """Expose short evidence and bibliography, not private book/audit payloads."""
    payload = dict(data)
    for field in ('localResearchEvidence', 'researchEvidence', 'windResearchEvidence',
                  'wechatResearchEvidence', 'sourceAliases'):
        if field not in data:
            continue
        items = []
        for evidence in data[field]:
            item = {k: v for k, v in evidence.items() if k in PUBLIC_EVIDENCE_FIELDS}
            if 'authorIdentity' in item:
                item['authorIdentity'] = {k: v for k, v in item['authorIdentity'].items()
                    if k in ('institution', 'authors', 'authorRoles', 'identityPages')}
            if isinstance(item.get('evidenceExcerpt'), str) and len(item['evidenceExcerpt']) > 600:
                raise ValueError('Public evidence must use a verified short excerpt, not a full paid body')
            items.append(item)
        payload[field] = items
    return public_snapshot(payload, root)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-partial', action='store_true')
    parser.add_argument('--require-monthly-complete', action='store_true',
                        help='Fail unless every month/channel has verified archives and an unblocked search audit')
    parser.add_argument('--parent-source-manifest', action='append', default=[],
                        help='Explicit parent-approved source descriptors and optional pinned shortage proofs; no autodiscovery')
    parser.add_argument('--reviewed-research-manifest',
                        help='Explicit hash-pinned parent research review; no draft autodiscovery or trust by filename')
    args = parser.parse_args()
    descriptors, shortages = list(DEFAULT_SOURCES), []
    for value in args.parent_source_manifest:
        manifest = json.loads(resolve(value, STAGE, ROOT).read_text(encoding='utf-8'))
        replacements = manifest.get('replaceChannels', [])
        if any(c not in ('知识星球', 'Wind', '微信公众号') for c in replacements):
            raise ValueError('Unknown channel in parent-source replacement manifest')
        descriptors = [d for d in descriptors if d['channel'] not in replacements]
        descriptors.extend(manifest.get('sources', []))
        shortages.extend(manifest.get('shortageProofs', []))
    data = build(allow_partial=args.allow_partial,
                 parent_sources=descriptors if args.parent_source_manifest else None, shortage_proofs=shortages,
                 reviewed_research_manifest=args.reviewed_research_manifest)
    if args.require_monthly_complete and not data['monthlyCoverage']['complete']:
        raise ValueError('Monthly channel coverage incomplete; no complete replay delivery permitted')
    for target, payload in [(STAGE / '研究/replay-data.json', data),
                            (ROOT / 'src/data/historyReplayHawkishTransition.json', publication_snapshot(data, ROOT))]:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'partial-development' if args.allow_partial else 'validated-inputs',
        'events': len(data['events']), 'reports': len(data['reports']), 'sources': len(data['sources']),
        'monthlyCoverageComplete': data['monthlyCoverage']['complete'],
        'monthlyCoveredCells': data['monthlyCoverage']['coveredCells'],
        'monthlyAcceptedCells': data['monthlyCoverage']['acceptedCells'],
        'monthlyRequiredCells': data['monthlyCoverage']['requiredCells']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
