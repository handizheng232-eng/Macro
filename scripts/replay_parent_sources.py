"""Private offline intake; only explicit, hash-pinned parent receipts grant admission.

Extend DEFAULT_SOURCES via --parent-source-manifest, never by scanning future books.
Descriptors: channel, canonicalSourcePath, sourceSHA256, parentLedgers[{path,sha256,section?}].
Paths may be project/stage relative. All resolved evidence must stay inside this stage.
Output is a public bibliographic whitelist, NOT a copy of the private source books.
"""
import hashlib
import json
import re
from pathlib import Path

DEFAULT_SOURCES = [{
    'channel': '知识星球',
    'canonicalSourcePath': '研究/channel-monthly-20261008-zsxq-diaoyan-redo-bibliography.json',
    'sourceSHA256': 'c21c997bd1b8278558ffa43bcb092fe181ac79c46ca3707955c567baae38841a',
    'parentLedgers': [{'path': '核验/调研纪要重做20261008/parent/independent-verification.json',
                       'sha256': '1aec1ae6a64e7852a518271c36b30860dcb8c5f147314f047f24b9c8626c2ab3'}],
}]

DEFAULT_SOURCES.extend([
    {'channel': '知识星球', 'canonicalSourcePath': '研究/channel-monthly-20261008-zsxq-diaoyan-completion01-bibliography.json',
     'sourceSHA256': '88517c7652bf5620808aa44ed58bc9c9818e9e1b0e5103951409e1ee5e92bd7e',
     'parentLedgers': [{'path': '核验/调研纪要补全20261008-batch01/parent/independent-increment-verification.json',
                        'sha256': '4295bfb0c766b13f68550fd6050c22c833220bed82734449375c215625308e3d'}]},
    {'channel': '知识星球', 'canonicalSourcePath': '研究/channel-monthly-20261008-zsxq-diaoyan-completion02-bibliography.json',
     'sourceSHA256': '36b602176908ad1437eb6d9d77e1301324031911b13a4b536d4962c47717f78e',
     'parentLedgers': [{'path': '核验/调研纪要补全20261008-batch02/parent/independent-increment-verification.json',
                        'sha256': '5490ebf960381c75ad99766e8f02f624f1bf961731c2fed0edd4327af59aab87'}]},
    {'channel': 'Wind', 'canonicalSourcePath': '研究/channel-monthly-20261009-wind-parent-accepted80-bibliography.json',
     'sourceSHA256': 'f443d1a34dac084a22aef70633e9427c1ab2e16d74b439ebc4a4afea10670969',
     'parentLedgers': [
         {'path': '核验/逐月最低篇数补采20261009/Wind-resume01/parent/independent-increment-verification.json',
          'sha256': '6f6e7f6b0a6839040bf85159d374be761cc26ca76b0b96faef9df35743e89f99', 'rowsKey': 'allPDFs'},
         {'path': '核验/逐月最低篇数补采20261009/Wind-resume02/parent/independent-increment-verification.json',
          'sha256': '05e3647284c9190ab27acef7f175dec24748b8663810892b5ef4180370ba2a96'},
         {'path': '核验/逐月最低篇数补采20261009/parent/independent-channel-verification.json', 'section': 'Wind',
          'sha256': 'db02723cc45ba6c84282324350ddd8b292ed0ad928f5cd5fd18b163c780d7746'}]},
    {'channel': '微信公众号', 'canonicalSourcePath': '研究/wechat-min5-20261009-parent-accepted-bibliography.json',
     'sourceSHA256': '4e0b9d8b801880c7fe86df923110e9fe44433deb4de4fced946a7e3d64aebba8',
     'parentLedgers': [{'path': '核验/逐月最低篇数补采20261009/parent/independent-channel-verification.json', 'section': 'wechat',
                        'sha256': 'db02723cc45ba6c84282324350ddd8b292ed0ad928f5cd5fd18b163c780d7746'}]},
])


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def resolve(value, stage, root):
    path = Path(value)
    if not path.is_absolute():
        path = root / value if (root / value).is_file() else stage / value
    path = path.resolve()
    if not path.is_relative_to(stage.resolve()) or not path.is_file():
        raise ValueError('Missing or out-of-stage parent evidence')
    return path


def pinned_json(value, digest, stage, root):
    path = resolve(value, stage, root)
    payload = path.read_bytes()
    if not re.fullmatch(r'[0-9a-f]{64}', digest or '') or sha(payload) != digest:
        raise ValueError('Parent source/ledger SHA mismatch')
    return json.loads(payload.decode('utf-8'))


def _original_star(record, parent, payload, stage, root):
    proof = (parent.get('twoParserPerPageShaMatch') is True and
             parent.get('sourceTagIndependentTextCheck') == ['调研纪要'] or
             parent.get('independentTagAndOriginalVersionChecked') is True and
             parent.get('allDualParserPageShaMatch') is True or
             parent.get('qualified') is True and parent.get('allPageHashPairsMatched') is True)
    if not proof:
        raise ValueError('Parent original body/tag proof missing')
    source = json.loads(resolve(record['topicDOMEvidence'], stage, root).read_text(encoding='utf-8'))
    if isinstance(source, list):
        source = next((s for s in source if s.get('sourceTopicURL') == record.get('topicURL')), {})
    rendered = source.get('renderedTopic', {}).get('text', '') or source.get('renderedBodyText', '')
    continuous = record.get('versionType') == 'platform_original_continuous_transcript'
    if continuous and not (parent.get('parentSemanticOriginalVersionAccepted') is True and
                           parent.get('parentSemanticScopeAccepted') is True):
        raise ValueError('Continuous transcript parent semantic review missing')
    if ('#调研纪要' not in rendered or record['originalFilename'] not in rendered or
            (source.get('topicURL') or source.get('sourceTopicURL')) != record.get('topicURL') or
            record.get('versionType') not in ('original_audio_transcript_pdf', 'platform_original_full_speech_transcript',
                                             'platform_original_continuous_transcript') or
            re.search(r'导读|摘要|纪要版', record['originalFilename'])):
        raise ValueError('Actual source tag/file/original-version mismatch')
    return {'date': record['filenameDate'], 'filenameDate': record['filenameDate'],
            'publicationDate': record.get('publicationDate'), 'dateBasis': 'filename_date_user_preferred',
            'title': record['originalFilename'].removesuffix('.pdf'),
            'provider': '知识星球·前沿信息收录 #调研纪要',
            'note': '原文转写PDF与实际标签已核；机构独立身份、录音完整度及历史首次可得未核。',
            'sourceQuality': {'tag': '调研纪要', 'versionType': record['versionType'],
                              'institutionIdentityIndependentlyVerified': False,
                              'recordingCompletenessVerified': False}}


def _original_wind(record, parent):
    if (parent.get('accepted') is not True or not any(parent.get(k) is True for k in
            ('allPageTextAndContentHashesMatch', 'allDualParserPageHashesMatched', 'allPageParserHashPairsMatched')) or
            record.get('countsTowardMonthlyMinimum') is not True or record.get('exclusionReasons') or
            record.get('pdfEncrypted', record.get('encrypted')) is not False or not record.get('institution') or
            not record.get('independentWorkId')):
        raise ValueError('Parent Wind body/origin/scope proof missing')
    printed = record.get('publicationDate')
    if printed is None:
        if record.get('publicationDatePrecision') != 'month' or not re.fullmatch(r'2026-0[1-8]', record.get('verifiedPublicationMonth', '')):
            raise ValueError('Wind printed month proof missing')
        printed = record['verifiedPublicationMonth']
    return {'date': printed, 'publicationDate': record.get('publicationDate'),
            'publicationDatePrecision': record.get('publicationDatePrecision') or ('day' if record.get('publicationDate') else 'month'),
            'verifiedPublicationMonth': record['verifiedPublicationMonth'],
            'dateBasis': 'printed_publication_date_or_issue_month',
            'title': record['title'], 'institution': record['institution'], 'provider': record['institution'] + ' · Wind',
            'note': '机构研报原件与刊发日/刊期已核；图表未OCR，首次可得未知。',
            'sourceQuality': {'versionType': 'institutional_research_pdf', 'printedPublicationVerified': True,
                              'institutionIdentityIndependentlyVerified': record.get('institutionIndependentOfficialWebsiteVerified') is True}}


def _original_wechat(record, parent, body_bytes, stage, root):
    from collections import defaultdict
    from datetime import date
    from html.parser import HTMLParser
    from urllib.parse import urlsplit

    class SavedPage(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.stack, self.values, self.og_url = [], defaultdict(list), None
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            fields = set(self.stack[-1][1]) if self.stack else set()
            if attrs.get('id') in ('js_content', 'activity-name', 'js_name', 'publish_time', 'js_author_name'):
                fields.add(attrs['id'])
            if 'original_primary_card_tips' in attrs.get('class', ''):
                fields.add('reprint')
            if tag == 'meta' and attrs.get('property') == 'og:url':
                self.og_url = attrs.get('content')
            if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
                self.stack.append((tag, fields))
        def handle_endtag(self, tag):
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    self.stack = self.stack[:i]
                    break
        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)
        def handle_data(self, data):
            if self.stack and not any(t in ('script', 'style') for t, _ in self.stack):
                for key in self.stack[-1][1]:
                    self.values[key].append(data)
        def field(self, key):
            return ''.join(self.values[key]).strip()

    norm = lambda text: re.sub(r'[\s\u200d]+', '', text)
    if parent.get('allHeaderBodyAndParagraphChecksPassed') is not True:
        raise ValueError('Parent WeChat original proof missing')
    raw = resolve(record.get('rawHtmlPath') or record['rawHTMLPath'], stage, root).read_bytes()
    if sha(raw) != record['rawHTMLSHA256'] or len(raw) != record['rawHTMLBytes']:
        raise ValueError('WeChat HTML bytes/SHA mismatch')
    rendered = raw
    if record.get('renderedHTMLPath'):
        rendered = resolve(record['renderedHTMLPath'], stage, root).read_bytes()
        if sha(rendered) != record['renderedHTMLSHA256']:
            raise ValueError('WeChat rendered HTML SHA mismatch')
    parser = SavedPage()
    parser.feed(rendered.decode('utf-8'))
    body = body_bytes.decode('utf-8')
    account = record['account']
    match = re.search(r'(\d{4})年(\d+)月(\d+)日', parser.field('publish_time'))
    actual_date = date(*map(int, match.groups())).isoformat() if match else None
    url = record.get('canonicalOriginalUrl') or record.get('canonicalURL')
    if (norm(parser.field('js_content')) != norm(body) or norm(parser.field('activity-name')) != norm(record['title']) or
            parser.field('js_name') != account or actual_date != record['publicationDate'] or parent['date'] != actual_date or
            parent['account'] != account or parser.field('reprint') or record.get('isThirdPartyRepost') is True or
            urlsplit(url).hostname != 'mp.weixin.qq.com' or urlsplit(parser.og_url or '').path != urlsplit(url).path):
        raise ValueError('WeChat original header/date/body mismatch or explicit reprint')
    paragraphs = json.loads(resolve(record['paragraphsPath'], stage, root).read_text(encoding='utf-8'))
    if (len(paragraphs) != record['paragraphCount'] or
            any(sha(p['text'].encode()) != p['sha256'] for p in paragraphs) or
            norm(''.join(p['text'] for p in paragraphs)) != norm(body)):
        raise ValueError('WeChat complete paragraph body mismatch')
    if not any(len(p['text']) >= 60 and re.search(r'美国|美联储|美债|美元', p['text']) for p in paragraphs):
        raise ValueError('WeChat substantive scope missing')
    return {'date': actual_date, 'publicationDate': actual_date,
            'dateBasis': 'actual_original_WeChat_header', 'title': record['title'],
            'accountActual': account, 'provider': account, 'institution': record.get('institution'),
            'authors': record.get('authors', []), 'bodySha256': sha(body_bytes),
            'paragraphCount': len(paragraphs),
            'independentWorkId': record.get('independentWorkId') or 'wechat-body:' + parent['normalizedBodySHA256'],
            'note': '实际原发页头和完整公开文章文字已核；非完整底层研报，图表未OCR，首次可得未知。',
            'sourceQuality': {'versionType': 'official_original_article_text', 'officialHeaderVerified': True,
                              'account': account, 'underlyingFullReportObtained': False}}


def load_parent_sources(stage, root, descriptors=None):
    stage, root = Path(stage), Path(root)
    reports, audits = [], []
    for descriptor in DEFAULT_SOURCES if descriptors is None else descriptors:
        source_path = descriptor['canonicalSourcePath']
        if descriptors is None and not (stage / source_path).is_file():
            continue
        book = pinned_json(source_path, descriptor['sourceSHA256'], stage, root)
        ledger_rows = []
        for binding in descriptor['parentLedgers']:
            ledger = pinned_json(binding['path'], binding['sha256'], stage, root)
            if binding.get('section'):
                ledger = ledger[binding['section']]
            ledger_rows.extend(ledger.get(binding.get('rowsKey', 'files'), []))
        channel = descriptor['channel']
        if channel not in ('知识星球', 'Wind', '微信公众号'):
            raise ValueError('Unsupported parent channel')
        for record in book.get('articles', book.get('items', [])):
            path = resolve(record.get('path') or record.get('bodyPath'), stage, root)
            digest = record.get('sha256') or record.get('bodySHA256')
            parents = [r for r in ledger_rows if r.get('sha256', r.get('bodySHA256')) == digest
                       and resolve(r.get('path') or r.get('bodyPath'), stage, root) == path]
            if not parents:
                raise ValueError('Archive path/SHA absent from parent allowlist')
            parent = parents[0]
            payload = path.read_bytes()
            if sha(payload) != digest or len(payload) != record.get('bytes', record.get('bodyBytes')):
                raise ValueError('Parent archive bytes/SHA mismatch')
            if parent.get('bytes', len(payload)) != len(payload):
                raise ValueError('Parent ledger byte mismatch')
            if channel != '微信公众号':
                import pymupdf
                with pymupdf.open(stream=payload, filetype='pdf') as pdf:
                    if (pdf.is_encrypted or pdf.needs_pass or pdf.is_repaired or len(pdf) != record['pageCount'] or
                            len(pdf) != parent.get('physicalPages', parent.get('pageCount', parent.get('pages')))):
                        raise ValueError('Unreadable/encrypted/repaired parent PDF')
            fields = (_original_star(record, parent, payload, stage, root) if channel == '知识星球' else
                      _original_wind(record, parent) if channel == 'Wind' else
                      _original_wechat(record, parent, payload, stage, root))
            rid = record.get('id') or record.get('documentId') or 'wind-min10-' + digest[:16]
            quality = fields.pop('sourceQuality')
            reports.append({
                'id': rid, 'channel': '微信' if channel == '微信公众号' else channel,
                'path': path.relative_to(root.resolve()).as_posix(), 'sha256': digest,
                'bytes': len(payload), **fields,
                **({'pageCount': record['pageCount']} if channel != '微信公众号' else {}),
                'independentWorkId': fields.get('independentWorkId') or record.get('independentWorkId') or 'sha256:' + digest,
                'identityBasis': 'parent-verified work linkage or archive SHA; not independent opinion count',
                'firstAvailableDate': None, 'historicalAsOfEligible': False,
                'downloadedThisRun': any(record.get(k) is True for k in ('downloadedThisRun', 'downloadedThisRedo', 'newDownload')),
                'sourceQuality': {**quality, 'parentLedgerVerified': True, 'originalBodyVerified': True,
                                  'datePolicyVerified': True, 'scopeVerified': True, 'imageOCRComplete': False},
            })
        for month in sorted({r['date'][:7] for r in reports if r['channel'] == ('微信' if channel == '微信公众号' else channel)}):
            monthly = book.get('monthly', [])
            raw_row = (monthly.get(month, {}) if isinstance(monthly, dict) else
                       next((r for r in monthly if r['month'] == month), {}))
            audits.append({'month': month, 'channel': channel,
                           'searchExecuted': raw_row.get('searchExecuted', descriptor.get('searchExecuted', False)) is True,
                           'searchComplete': raw_row.get('searchComplete', book.get('searchComplete', False)) is True,
                           'searchExhaustive': raw_row.get('searchExhaustive', book.get('searchExhaustive', False)),
                           'matchedCount': None, 'status': 'parent_verified_partial_search',
                           'reason': '真实已核原文按月累计；检索未穷尽，不把取得数当网站实际总数。'})
    merged_audits = {}
    for row in audits:
        key = (row['month'], row['channel'])
        prior = merged_audits.get(key, {})
        row['searchExecuted'] = row['searchExecuted'] or prior.get('searchExecuted') is True
        merged_audits[key] = row
    audits = list(merged_audits.values())
    ids = [r['id'] for r in reports]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate parent report identity')
    return reports, audits
