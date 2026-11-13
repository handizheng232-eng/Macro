"""Public-data admission, distinct from the separately archived original-source audit."""
from datetime import date, datetime, timedelta, timezone
import json
import math
from refresh_ifind_us_gdp import contribution_rounding_check
from refresh_ifind_us_employment import shift_month
from verify_renewed_easing_publish import require

IDENTITY_FIELDS = {'id', 'label', 'title', 'unit', 'frequency', 'provider', 'institution', 'code', 'name',
                   'rawUnit', 'url', 'transformLabel', 'parentId', 'depth', 'rowType', 'derived',
                   'lowerExclusive', 'upperInclusive', 'tolerance', 'tolerancePercentagePoints',
                   'color', 'kind', 'defaultRange', 'schemaVersion'}


def walk(value, path=()):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            if key != 'latestComponents':
                yield from walk(child, (*path, key))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            if isinstance(child, (dict, list)):
                yield from walk(child, (*path, str(i)))


def identities(doc):
    return {path: {k: v for k, v in obj.items() if k in IDENTITY_FIELDS}
            for path, obj in walk(doc) if IDENTITY_FIELDS.intersection(obj)}


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_series(doc, baseline):
    old = {path: obj for path, obj in walk(baseline) if 'dates' in obj and 'values' in obj}
    current = {path: obj for path, obj in walk(doc) if 'dates' in obj and 'values' in obj}
    require(set(old) == set(current), 'dated series coverage differs')
    for path, series in current.items():
        dates, values = series['dates'], series['values']
        require(len(dates) == len(values) > 0, 'series date/value lengths differ')
        require(all(isinstance(d, str) for d in dates), 'non-text series date')
        # Published monthly/quarterly axes use YYYYMM; daily axes use YYYYMMDD.
        parsed = [date.fromisoformat(d + '01' if len(d) == 6 else d) for d in dates]
        require(parsed == sorted(set(parsed)), 'series dates unordered or duplicated')
        require(all(v is None or number(v) for v in values), 'nonfinite/non-numeric series value')
        removed = set(old[path]['dates']) - set(dates)
        # The pinned builder samples daily data at each month's last observed
        # date (plus institution start). A partial-month endpoint legitimately
        # moves forward; this is not removal of an earlier monthly observation.
        month_end = series.get('frequency') == '月' and (
            series.get('transformLabel') == '官方日频序列保留首日并取各月最后有效值'
            or series.get('id') == 'reserve_rate')
        replaceable = set()
        if month_end and removed == {old[path]['dates'][-1]}:
            last = old[path]['dates'][-1]
            if any(d[:6] == last[:6] and d > last and v is not None for d, v in zip(dates, values)):
                replaceable = {last}
        require(removed <= replaceable, 'available series history was removed')
        actual = dict(zip(dates, values))
        require(all(v is None or d in replaceable or actual[d] is not None for d, v in zip(old[path]['dates'], old[path]['values'])), 'previous observations became missing')
    return len(current)


def validate_tables(doc, baseline):
    old = {path: obj for path, obj in walk(baseline) if isinstance(obj.get('history'), dict) and 'rows' in obj}
    current = {path: obj for path, obj in walk(doc) if isinstance(obj.get('history'), dict) and 'rows' in obj}
    require(set(old) == set(current), 'history table coverage differs')
    for path, table in current.items():
        history = table['history']; periods = history['periods']
        require(periods and len(periods) == len(set(periods)), 'history calendar duplicates')
        require(all(shift_month(a, -1) == b for a, b in zip(periods, periods[1:])), 'history calendar gap or ordering differs')
        require(set(old[path]['history']['periods']) <= set(periods), 'available table history removed')
        require(len(table['rows']) == len(history['rows']), 'history row count differs')
        previous_history = old[path]['history']
        previous_rows = {r['id']: r for r in previous_history['rows']}
        positions = {period: i for i, period in enumerate(periods)}
        require({r['id'] for r in history['rows']} == set(previous_rows), 'historical row coverage differs')
        for recent, row in zip(table['rows'], history['rows']):
            require(recent['id'] == row['id'], 'history row identity differs')
            measure_fields = {'values', 'yoy', 'mom'}
            require(measure_fields.intersection(row) == measure_fields.intersection(previous_rows[row['id']])
                    == measure_fields.intersection(recent), 'historical measurement field removed or changed')
            for field in ('values', 'yoy', 'mom'):
                if field in row:
                    require(len(row[field]) == len(periods), 'history column length differs')
                    require(all(v is None or number(v) for v in row[field]), 'history values invalid')
                    previous_values = previous_rows[row['id']][field]
                    require(all(v is None or row[field][positions[p]] is not None
                                for p, v in zip(previous_history['periods'], previous_values)),
                            'previous historical table observations became missing')
                    require([row[field][periods.index(p)] for p in table['periods']] == recent[field], 'recent/history projection differs')


def validate_employment(doc):
    table = doc['sections']['officialSurveys']['sectorMonitor']; history = table['history']
    rows = {r['id']: r for r in history['rows']}
    monthly = next(c for c in doc['sections']['officialSurveys']['charts'] if c['id'] == 'payroll-momentum')['series'][0]
    payroll = dict(zip((d[:6] for d in monthly['dates']), monthly['values']))
    relations = {
        'private-leaves': ([r['id'] for r in rows.values() if r['parentId'] in ('payroll_goods', 'payroll_services')], 'payroll_private'),
        'government-leaves': (['sector_federal', 'sector_state', 'sector_local'], 'payroll_government'),
        'nonfarm-total': (['payroll_private', 'payroll_government'], 'payroll_total'),
        'goods-subtotal': ([r['id'] for r in rows.values() if r['parentId'] == 'payroll_goods'], 'payroll_goods'),
        'services-subtotal': ([r['id'] for r in rows.values() if r['parentId'] == 'payroll_services'], 'payroll_services'),
        'private-subtotals': (['payroll_goods', 'payroll_services'], 'payroll_private')}
    checks = history['reconciliation']['checks']
    require({c['id'] for c in checks} == {*relations, 'table-vs-payroll'}, 'employment check coverage differs')
    for check in checks:
        require(len(check['values']) == len(history['periods']), 'employment residual columns differ')
        for i, period in enumerate(history['periods']):
            if check['id'] == 'table-vs-payroll':
                values = [rows['payroll_total']['values'][i], payroll.get(period)]
                residual = round(values[0] - values[1], 4) if all(v is not None for v in values) else None
            else:
                children, parent = relations[check['id']]
                values = [rows[k]['values'][i] for k in [*children, parent]]
                residual = round(sum(values[:-1]) - values[-1], 1) if all(v is not None for v in values) else None
            require(check['values'][i] == residual, 'employment residual not independently reproducible')
            if period in table['periods'] and residual is not None:
                require(abs(residual) <= check['tolerance'], 'recent employment reconciliation failed')


def validate_pce(pce, baseline):
    periods = pce['periods']; buckets = pce['buckets']; components = pce['latestComponents']; tolerance = 1e-8
    require(periods and periods == sorted(set(periods)), 'PCE periods invalid')
    require(all(shift_month(a, 1) == b for a, b in zip(periods, periods[1:])), 'PCE calendar gap')
    require(set(baseline['periods']) <= set(periods), 'available PCE history removed')
    require(len(buckets) == 6 and all(len(b['values']) == len(periods) for b in buckets), 'six PCE buckets or lengths differ')
    for i in range(len(periods)):
        values = [b['values'][i] for b in buckets]
        require(all(number(v) and 0 <= v <= 100 for v in values), 'invalid PCE bucket weight')
        require(abs(sum(values) - 100) <= tolerance, 'PCE monthly weights do not close')
    require(components and len({c['label'] for c in components}) == len(components), 'PCE component identity duplicates')
    sums = [0.0] * 6
    for component in components:
        rate, weight = component['annualizedRate'], component['weight']
        require(number(rate) and rate >= -100 and number(weight) and 0 <= weight <= 100, 'invalid PCE rate or weight')
        index = next((i for i, upper in enumerate((0, 2, 3, 5, 10)) if rate <= upper), 5)
        sums[index] += weight
    require(abs(sum(sums) - 100) <= tolerance, 'PCE component weights do not close')
    require(all(abs(value - bucket['values'][-1]) <= tolerance for value, bucket in zip(sums, buckets)), 'PCE independent rebin differs')
    quality = pce['quality']
    require(quality['latestComponentCount'] == len(components), 'PCE component count differs')
    require(abs(quality['latestWeightSum'] - sum(sums)) <= tolerance, 'PCE reported weight sum differs')
    monthly_sums = [sum(b['values'][i] for b in buckets) for i in range(len(periods))]
    require(len(quality['monthlySums']) == len(monthly_sums) and all(abs(a - b) <= tolerance for a, b in zip(quality['monthlySums'], monthly_sums)), 'PCE reported monthly sums differ')
    require(abs(quality['maximumSumResidual'] - max(abs(v - 100) for v in monthly_sums)) <= tolerance, 'PCE reported monthly residual differs')
    require(abs(quality['latestBucketMaxDifference'] - max(abs(v - b['values'][-1]) for v, b in zip(sums, buckets))) <= tolerance, 'PCE reported rebin residual differs')
    require(abs(quality['latestZeroRateWeight'] - sum(c['weight'] for c in components if c['annualizedRate'] == 0)) <= tolerance, 'PCE zero-rate weight differs')
    return len(components)


def validate_documents(documents, baseline):
    require(set(documents) == set(baseline), 'document scope differs')
    dated = 0
    for name, doc in documents.items():
        json.dumps(doc, allow_nan=False)
        old = baseline[name]
        require(identities(doc) == identities(old), 'source/schema/unit/label identity differs: ' + name)
        fetched = datetime.fromisoformat(doc['generatedAt']); previous = datetime.fromisoformat(old['generatedAt'])
        require(fetched.tzinfo is not None and previous <= fetched <= datetime.now(timezone.utc) + timedelta(minutes=5), 'acquisition time invalid or regressed')
        dated += validate_series(doc, old)
        validate_tables(doc, old)
    gdp = documents['src/data/usGdpData.json']
    chart = next(c for section in gdp['sections'].values() for c in section.get('charts', []) if c['id'] == 'growth-contributions')
    maps = [dict(zip(s['dates'], s['values'])) for s in chart['series']]
    total = chart['totalSeries']; checked = 0
    for d, value in zip(total['dates'], total['values']):
        if value is not None and all(m.get(d) is not None for m in maps):
            require(contribution_rounding_check(value, [m[d] for m in maps])['passed'], 'GDP published-precision closure failed')
            checked += 1
    require(checked > 0, 'No GDP contribution quarters verified')
    validate_employment(documents['src/data/usEmploymentData.json'])
    inflation = documents['src/data/usInflationData.json']; old_inflation = baseline['src/data/usInflationData.json']
    history = inflation['actual']['cpiHeatmap']['history']
    require(history['rows'][0]['yoy'][history['periods'].index('202510')] is None, 'Documented CPI calendar gap was filled')
    count = validate_pce(inflation['actual']['pceDistribution'], old_inflation['actual']['pceDistribution'])
    return {'datedSeries': dated, 'gdpContributionQuarters': checked, 'pceComponents': count,
            'rawSourceIdentityRequeriedInCI': False}
