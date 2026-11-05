"""Dallas Fed PCE price-change distribution: strict, offline-replayable XLSX.

Only the Python standard library is required. Excel formulas are NOT evaluated:
cached values in the official workbook are the inputs. No trimmed-mean history
or year-on-year proxy is used to manufacture a longer distribution series.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import urllib.request
import base64
import calendar
import hashlib
from html import unescape
import re
import io
import math
import posixpath
import xml.etree.ElementTree as ET
import zipfile

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
RID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'


def read_xlsx(data: bytes, sheet_name: str) -> dict:
    """Read cell values using the workbook relationships, not sheet indices."""
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        workbook = ET.fromstring(book.read('xl/workbook.xml'))
        props = workbook.find('s:workbookPr', NS)
        if props is not None and props.get('date1904') in ('1', 'true'):
            raise ValueError('Unsupported Excel epoch: expected 1900')
        sheet = next((s for s in workbook.findall('s:sheets/s:sheet', NS)
                      if s.get('name') == sheet_name), None)
        if sheet is None:
            raise ValueError(f'Missing worksheet: {sheet_name}')
        relationships = ET.fromstring(book.read('xl/_rels/workbook.xml.rels'))
        targets = {r.get('Id'): r for r in relationships}
        relation = targets[sheet.get(RID)]
        if relation.get('TargetMode') == 'External' or not relation.get('Type', '').endswith('/worksheet'):
            raise ValueError('Expected internal worksheet relationship')
        target = relation.get('Target', '')
        path = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
        if not path.startswith('xl/') or '..' in path.split('/'):
            raise ValueError('Invalid worksheet path')
        strings = []
        if 'xl/sharedStrings.xml' in book.namelist():
            strings = [''.join(t.text or '' for t in si.findall('.//s:t', NS))
                       for si in ET.fromstring(book.read('xl/sharedStrings.xml'))]
        values = {}
        for cell in ET.fromstring(book.read(path)).findall('s:sheetData/s:row/s:c', NS):
            ref, kind = cell.get('r'), cell.get('t')
            node = cell.find('s:v', NS)
            if kind == 'inlineStr':
                value = ''.join(t.text or '' for t in cell.findall('.//s:t', NS))
            elif node is None or node.text is None:
                value = None
            elif kind == 's':
                value = strings[int(node.text)]
            elif kind in ('str', 'e', 'b'):
                value = node.text
            else:
                value = float(node.text)
            if ref in values:
                raise ValueError(f'Duplicate cell {ref}')
            values[ref] = value
        return values


def excel_month(serial: float) -> str:
    """Excel 1900 epoch, including its fictitious leap day offset after 60."""
    if isinstance(serial, bool) or not isinstance(serial, (int, float)) or not math.isfinite(serial):
        raise ValueError('Invalid Excel date')
    if serial < 61 or serial != int(serial):
        raise ValueError('Expected a modern whole-day Excel date')
    return (datetime(1899, 12, 30) + timedelta(days=serial)).strftime('%Y%m')


SOURCE_URL = 'https://www.dallasfed.org/research/pce'
CHART_URL = 'https://www.dallasfed.org/-/media/documents/research/pce/pcedata.xlsx'
DETAIL_URL = 'https://www.dallasfed.org/~/media/documents/research/pce/detail'
PROVIDER = 'Federal Reserve Bank of Dallas'
HEADERS = ['Rose at 0-2% rate', 'Rose at 2-3% rate', 'Rose at 3-5% rate',
           'Rose at 5-10% rate', 'Rose faster than 10% rate']
# Closed upper bounds match the official latest component table and five rows.
BUCKETS = [('nonpositive', '未上涨（≤0%）', '#94a3b8', None, 0),
           ('0-2', '0%—2%', '#66a78e', 0, 2),
           ('2-3', '2%—3%', '#a8bc6b', 2, 3),
           ('3-5', '3%—5%', '#dfbf62', 3, 5),
           ('5-10', '5%—10%', '#d98d57', 5, 10),
           ('gt10', '>10%', '#bf5956', 10, None)]
TOLERANCE = 1e-8  # percentage points; machine precision, not economic rounding
DEFAULT_BACKUP_DIR = Path(os.environ.get('PCE_DISTRIBUTION_BACKUP_DIR',
                                        str(Path.home() / 'macro-data-archives' / 'pce-distribution')))


def fetch_distribution(raw_dir: Path, backup_dir: Path = DEFAULT_BACKUP_DIR) -> dict:
    """Fetch a coherent batch; preserve originals in ignored raw + durable archive.

    Every resource has its own actual receipt time and SHA. The bundle includes
    both source bytes and their parsed tables, and replays without local files.
    A failed download or validation raises, never returning a partial dataset.
    """
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    raw_dir, backup_dir = Path(raw_dir).resolve() / stamp, Path(backup_dir).resolve() / stamp
    if raw_dir == backup_dir:
        raise ValueError('Durable backup must be separate from raw directory')
    for folder in (raw_dir, backup_dir):
        folder.mkdir(parents=True, exist_ok=False)
    resources = {}
    for name, url, filename in [('page', SOURCE_URL, 'dallas-pce.html'),
                                ('chart', CHART_URL, 'pcedata.xlsx'),
                                ('detail', DETAIL_URL, 'detail.xlsx')]:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        received = datetime.now(timezone.utc).isoformat()
        digest = hashlib.sha256(data).hexdigest()
        for folder in (raw_dir, backup_dir):
            with (folder / filename).open('xb') as handle:
                handle.write(data)
            if hashlib.sha256((folder / filename).read_bytes()).hexdigest() != digest:
                raise OSError('Raw archive integrity verification failed')
        resources[name] = {'url': url, 'fetchedAt': received, 'sha256': digest,
                           'encoding': 'base64', 'body': base64.b64encode(data).decode('ascii'),
                           'rawPath': str(raw_dir / filename), 'backupPath': str(backup_dir / filename)}
    bundle = {'schemaVersion': 1, 'resources': resources,
              'archivePath': str(raw_dir / 'bundle.json'), 'backupArchivePath': str(backup_dir / 'bundle.json')}
    bundle['tables'] = parse_tables(bundle)
    # Preserve a rejected candidate for diagnosis too; only return after gates.
    text = json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False)
    for path in (bundle['archivePath'], bundle['backupArchivePath']):
        Path(path).write_text(text, encoding='utf-8')
    build_distribution(bundle)
    return bundle


def _number(value, context: str, share: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{context}: missing or non-finite numeric cell')
    if share and not 0 <= value <= 100:
        raise ValueError(f'{context}: share/weight outside 0..100')
    return value


def bucket_index(rate: float) -> int:
    _number(rate, 'Annualized rate')
    for i, (_, _, _, lower, upper) in enumerate(BUCKETS):
        if (lower is None or rate > lower) and (upper is None or rate <= upper):
            return i
    raise ValueError('Non-finite annualized rate')


def _column_number(label: str) -> int:
    number = 0
    for letter in label:
        number = number * 26 + ord(letter) - ord('A') + 1
    return number


def _decode_resource(resource: dict) -> bytes:
    body = base64.b64decode(resource['body'], validate=True)
    if hashlib.sha256(body).hexdigest() != resource['sha256']:
        raise ValueError('Resource SHA256 mismatch')
    return body


def parse_tables(bundle: dict) -> dict:
    resources = bundle['resources']
    return {
        'chart': read_xlsx(_decode_resource(resources['chart']), 'Web - Chart Data'),
        'detail': read_xlsx(_decode_resource(resources['detail']), 'Web - Underlying detail'),
    }


def build_distribution(bundle: dict) -> dict:
    """Rebuild exclusively from archived original bytes, with no network access."""
    if bundle.get('schemaVersion') != 1:
        raise ValueError('Unsupported PCE archive schema')
    resources = bundle['resources']
    timestamps = []
    for name, url in [('page', SOURCE_URL), ('chart', CHART_URL), ('detail', DETAIL_URL)]:
        r = resources[name]
        if r.get('url') != url or r.get('encoding') != 'base64':
            raise ValueError(f'Incorrect {name} source identity/encoding')
        timestamp = datetime.fromisoformat(r['fetchedAt'])
        if timestamp.tzinfo is None:
            raise ValueError('Fetch timestamps must include timezone')
        timestamps.append(timestamp)
    if (max(timestamps) - min(timestamps)).total_seconds() > 3600:
        raise ValueError('Page and workbooks must be fetched in the same batch (within one hour)')
    tables = parse_tables(bundle)
    if 'tables' in bundle and bundle['tables'] != tables:
        raise ValueError('Archived parsed tables differ from source bytes')
    chart, detail = tables['chart'], tables['detail']
    for row, header in enumerate(HEADERS, 4):
        if chart.get(f'A{row}') != header:
            raise ValueError(f'Unrecognized distribution header at A{row}')
    if [detail.get(ref) for ref in ('B2', 'C2', 'D2')] != ['Annualized 1-month % change', 'Weight', 'Cumulative weight']:
        raise ValueError('Unrecognized component detail header')
    html = _decode_resource(resources['page']).decode('utf-8-sig')
    title = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
    if not title:
        raise ValueError('Missing official current-month title')
    title_text = unescape(title.group(1))
    month_match = re.fullmatch(r'Trimmed Mean PCE Inflation rate, ([A-Za-z]+) (\d{4})', title_text)
    if not month_match or month_match[1] not in calendar.month_name:
        raise ValueError('Unrecognized official current-month title')
    page_period = month_match[2] + f'{list(calendar.month_name).index(month_match[1]):02d}'
    # Derive the axis from every nonempty date OR data cell: missing headers
    # must not silently drop a column and thereby hide a missing month.
    columns = sorted({match[1] for ref, value in chart.items()
                      if value is not None and (match := re.fullmatch(r'([A-Z]+)[3-8]', ref))
                      and match[1] != 'A'}, key=_column_number)
    if not columns or [_column_number(c) for c in columns] != list(range(2, _column_number(columns[-1]) + 1)):
        raise ValueError('Missing distribution month column')
    periods = [excel_month(chart.get(c + '3')) for c in columns]
    ordinals = [int(p[:4]) * 12 + int(p[4:]) for p in periods]
    if ordinals != list(range(ordinals[0], ordinals[-1] + 1)) or len(set(periods)) != len(periods):
        raise ValueError('Distribution months missing, duplicated or out of order; no interpolation')
    if periods[-1] != page_period:
        raise ValueError('Official page month differs from latest chart month')
    if periods[-1] > max(timestamps).strftime('%Y%m'):
        raise ValueError('Observation month is later than fetch month')
    values = [[_number(chart.get(c + str(r)), f'Chart {c}{r}', share=True)
               for c in columns] for r in range(4, 9)]
    residual = [100 - math.fsum(row[i] for row in values) for i in range(len(periods))]
    for value in residual:
        _number(value, 'Residual (official positive bucket total)', share=True)
    all_values = [residual, *values]
    rows = sorted({int(ref[1:]) for ref, v in detail.items()
                   if re.fullmatch(r'[A-D]\d+', ref) and int(ref[1:]) >= 3 and v is not None})
    if not rows or rows != list(range(3, rows[-1] + 1)):
        raise ValueError('Missing component rows')
    components = []
    labels = set()
    for r in rows:
        label = detail.get(f'A{r}')
        if not isinstance(label, str) or not label.strip() or label in labels:
            raise ValueError(f'Missing/duplicate component label at row {r}')
        labels.add(label)
        rate = _number(detail.get(f'B{r}'), f'Rate B{r}')
        if rate < -100:
            raise ValueError('Annualized price change below -100%')
        weight = _number(detail.get(f'C{r}'), f'Weight C{r}', share=True)
        cumulative = _number(detail.get(f'D{r}'), f'Cumulative weight D{r}', share=True)
        components.append({'label': label, 'annualizedRate': rate, 'weight': weight})
        if abs(cumulative - math.fsum(c['weight'] for c in components)) > TOLERANCE:
            raise ValueError(f'Cumulative component weight mismatch at row {r}')
    if abs(math.fsum(c['weight'] for c in components) - 100) > TOLERANCE:
        raise ValueError('Component weights do not sum to 100%')
    grouped = [math.fsum(c['weight'] for c in components if bucket_index(c['annualizedRate']) == i)
               for i in range(6)]
    sums = [math.fsum(row[i] for row in all_values) for i in range(len(periods))]
    max_difference = max(abs(grouped[i] - all_values[i][-1]) for i in range(6))
    if max_difference > TOLERANCE:
        raise ValueError('Latest detail buckets do not close to official chart; possible mixed months/vintages')
    if any(abs(v - 100) > TOLERANCE for v in sums):
        raise ValueError('Monthly distribution does not sum to 100%')
    fetched_at = max((r['fetchedAt'] for r in resources.values()), key=datetime.fromisoformat)
    return {
        'title': 'PCE分项价格涨幅分布——按消费支出权重加权',
        'description': '按分项季调月度环比折年涨幅分桶，展示各桶占消费支出的权重；不是分项数量占比，也不是同比。',
        'unit': '消费支出占比（%）', 'periods': periods,
        'buckets': [{'id': key, 'label': label, 'color': color, 'lowerExclusive': lower,
                     'upperInclusive': upper, 'derived': i == 0, 'values': all_values[i]}
                    for i, (key, label, color, lower, upper) in enumerate(BUCKETS)],
        'source': {
            'provider': PROVIDER, 'institution': '达拉斯联邦储备银行（底层分项来自BEA）',
            'sourceUrl': SOURCE_URL, 'chartDataUrl': CHART_URL, 'detailDataUrl': DETAIL_URL,
            'fetchedAt': fetched_at, 'latestObservation': periods[-1],
            'sourceObservation': page_period, 'pageTitle': title_text,
            'detailObservation': None,
            'detailMatchEvidence': '明细无显式观察日期；官网当月标题与图表最新月相同，且同批明细按六桶加总与最新图表闭合。该证据为匹配核验，不是明细原载日期。',
            'resources': {k: {field: r[field] for field in ('url', 'fetchedAt', 'sha256')}
                          for k, r in resources.items()},
        },
        'methodology': {
            'rate': '分项价格季调月度环比折年率（%）：100*((P_t/P_{t-1})^12-1)，不是同比；直接使用官方明细折年率，不由已舍入月率推算。',
            'weight': '使用Dallas明细Weight列的官方消费支出权重（%）。其方法为上月名义支出占比与按上月价格计价的本月数量支出占比的均值，不是两个月名义支出占比的简单平均；不自行换用CPI权重或等权。',
            'weightFormula': 'w_i,t = 0.5*(P_i,t-1*Q_i,t-1/sum_j(P_j,t-1*Q_j,t-1) + P_i,t-1*Q_i,t/sum_j(P_j,t-1*Q_j,t)); Weight=100*w_i,t',
            'boundaries': 'r≤0；0<r≤2；2<r≤3；3<r≤5；5<r≤10；r>10。r为月度环比折年率（%），不先四舍五入再分桶。',
            'residual': '未上涨（≤0%）=100减官方五个上涨桶之和，包含价格不变及下降，不能称为纯下降。最新月再与明细独立加总核对。',
            'coverage': f'本次官方图表可得{len(periods)}个月：{periods[0]}—{periods[-1]}；明细仅最新截面。使用全部分项（含被截尾项目），不是截尾后分布。缺失不插值；不使用1977年以来截尾均值历史反推分布，不构造同比。',
            'references': [
                {'url': SOURCE_URL, 'locator': 'Distribution chart description'},
                {'url': SOURCE_URL + '/glossary', 'locator': 'Annualized rates; Components of personal consumption expenditures'},
                {'url': SOURCE_URL + '/descr', 'locator': 'Trimming describes a different statistic, not exclusion from this distribution'},
                {'url': 'https://www.dallasfed.org/-/media/documents/research/papers/2005/wp0506.pdf', 'locator': 'Printed page 5, equation (2): two terms priced at prior-month prices'},
                {'url': 'https://www.dallasfed.org/-/media/Documents/research/pce/tech.pdf', 'locator': '2009 revision; historical component definitions, not current component count'},
            ],
        },
        'quality': {
            'monthlySums': sums, 'maximumSumResidual': max(abs(v - 100) for v in sums),
            'latestComponentCount': len(components), 'latestWeightSum': math.fsum(c['weight'] for c in components),
            'latestBucketMaxDifference': max_difference, 'tolerancePercentagePoints': TOLERANCE,
            'latestZeroRateWeight': math.fsum(c['weight'] for c in components if c['annualizedRate'] == 0),
            'missingPeriods': [],
        },
        'latestComponents': components,
        'notes': ['官方历史图表为当前版本，可能随BEA修订变化，不是逐月首次发布版本。',
                  '明细项目数按本次实际非空数据行统计；旧方法文档的178项不能冒充本次项目数。',
                  'iFinD优先检索未发现现成分桶，故此卡片单独使用Dallas官方来源；抓取时间不代表其他iFinD序列已刷新。'],
    }
