"""Explicit CPI seasonal-adjustment identities; generic MoM is not SA."""
import json
import hashlib
from datetime import datetime
from pathlib import Path

CONTRACT_PATH = Path(__file__).with_name('fixtures') / 'cpi_sa_contract.json'
CONTRACT_DOCUMENT = json.loads(CONTRACT_PATH.read_bytes())
CONTRACT = CONTRACT_DOCUMENT['series']
# Deliberately independent of editable contract declarations: no generic NSA opt-in.
NSA_EXCEPTIONS = {
    'food_away_mom': {'code': 'G005464519', 'name': '美国:CPI:家庭外就餐:当月环比',
                      'seasonalAdjustment': 'NSA',
                      'adjustmentBasis': 'BLS-202610-footnote-1; single-ordinary-source-history',
                      'entityAlias': 'Food away from home', 'blsSeries': 'CUUR0000SEFV'},
    'personal_services_mom': {'code': 'G005464538', 'name': '美国:CPI:其他个人服务:当月环比',
                             'seasonalAdjustment': 'NSA',
                             'adjustmentBasis': 'BLS-202610-footnote-1; single-ordinary-source-history',
                             'entityAlias': 'Miscellaneous personal services', 'blsSeries': 'CUUR0000SEGD'},
}


def adjustment_for(key):
    if (CONTRACT_DOCUMENT.get('nsaExceptions') != NSA_EXCEPTIONS
            or CONTRACT_DOCUMENT.get('defaultAdjustment') != 'SA'
            or CONTRACT_DOCUMENT.get('counts') != {'total': 24, 'SA': 22, 'NSA': 2}
            or not set(NSA_EXCEPTIONS) <= set(CONTRACT) or len(CONTRACT) != 24):
        raise ValueError('CPI registered NSA exception classification mismatch')
    expected = CONTRACT[key]
    if key in NSA_EXCEPTIONS:
        if any(expected[field] != NSA_EXCEPTIONS[key][field] for field in ('code', 'name')):
            raise ValueError('CPI registered NSA exception identity mismatch: ' + key)
        return 'NSA'
    return 'SA'


def validate_metadata(key, metadata):
    expected = CONTRACT[key]
    actual = {'code': metadata.get('displayid'), **{k: metadata.get(k) for k in ('name', 'unit', 'frequency', 'datasource')}}
    adjustment = adjustment_for(key)
    if actual != expected or (adjustment == 'SA' and ('季调' not in actual['name'] or '非季调' in actual['name'] or '未季调' in actual['name'])):
        raise ValueError('CPI seasonal-adjustment identity mismatch: ' + key)


def source_metadata(key):
    expected = CONTRACT[key]
    return {'code': expected['code'], 'name': expected['name'], 'seasonalAdjustment': adjustment_for(key),
            **({k: v for k, v in NSA_EXCEPTIONS[key].items() if k not in ('code', 'name', 'seasonalAdjustment')} if key in NSA_EXCEPTIONS else {}),
            'provider': 'iFinD EDB', 'institution': expected['datasource'],
            'unit': expected['unit'], 'rawUnit': expected['unit'], 'frequency': expected['frequency']}


def series_digest(dates, values):
    pairs = [(d[:6], round(float(v), 2)) for d, v in zip(dates, values)]
    return hashlib.sha256(json.dumps(pairs, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def build_audit(envelope, parsed, base_generated_at):
    if set(envelope.get('metadata', {})) != set(CONTRACT) or set(envelope.get('retrievedAt', {})) != set(CONTRACT):
        raise ValueError('Complete CPI seasonal-adjustment metadata and acquisition times required')
    records = {}
    for key in CONTRACT:
        metadata = envelope['metadata'][key]
        validate_metadata(key, metadata)
        retrieved = envelope['retrievedAt'][key]
        if datetime.fromisoformat(retrieved).tzinfo is None:
            raise ValueError('CPI acquisition time must include timezone')
        dates, values = parsed[key]
        if not dates or len(dates) != len(values) or len({d[:6] for d in dates}) != len(dates):
            raise ValueError('Invalid CPI monthly observations: ' + key)
        records[key] = {'metadata': metadata, 'seasonalAdjustment': adjustment_for(key),
                        'classification': 'registered-NSA-exception' if key in NSA_EXCEPTIONS else 'strict-SA',
                        'retrievedAt': retrieved, 'points': len(dates),
                        'first': dates[0], 'last': dates[-1], 'latest': values[-1],
                        'normalizedSeriesSHA256': series_digest(dates, values)}
        if key == 'core_cpi_mom':
            # Core CPI has no heatmap row: retain the complete parsed source,
            # including original day precision and unrounded numeric values.
            records[key]['observations'] = {'dates': list(dates), 'values': list(values)}
    return {'metadataVerified': True, 'baseGeneratedAt': base_generated_at,
            'checkedAt': max(envelope['retrievedAt'].values(), key=datetime.fromisoformat),
            'series': records,
            'classificationCounts': {'total': len(records), **{a: sum(r['seasonalAdjustment'] == a for r in records.values()) for a in ('SA', 'NSA')}},
            'heatmapCounts': {'total': len(records) - 1, **{a: sum(r['seasonalAdjustment'] == a for k, r in records.items() if k != 'core_cpi_mom') for a in ('SA', 'NSA')}},
            'note': '仅列CPI环比源的实际取得时间：22 SA及2项注册NSA例外；不得据此把其他通胀数据标为本次重新抓取。' + CONTRACT_DOCUMENT['historyPolicy']}


def validate_dataset(dataset):
    """Fail closed on statistical identity, current readings and source digests."""
    try:
        audit = dataset['dataQuality']['cpiSeasonality']
        if audit['metadataVerified'] is not True or set(audit['series']) != set(CONTRACT):
            raise ValueError('Incomplete CPI source audit')
        if (audit.get('classificationCounts') != {'total': 24, 'SA': 22, 'NSA': 2}
                or audit.get('heatmapCounts') != {'total': 23, 'SA': 21, 'NSA': 2}):
            raise ValueError('CPI classification counts mismatch')
        if audit['baseGeneratedAt'] != dataset['generatedAt']:
            raise ValueError('CPI correction cannot relabel the base batch vintage')
        for key, record in audit['series'].items():
            validate_metadata(key, record['metadata'])
            if (record.get('seasonalAdjustment') != adjustment_for(key)
                    or record.get('classification') != ('registered-NSA-exception' if key in NSA_EXCEPTIONS else 'strict-SA')):
                raise ValueError('CPI audit classification mismatch: ' + key)
            if record['first'] != record['metadata']['sdate'] or record['last'] != record['metadata']['edate']:
                raise ValueError('CPI source observation boundary mismatch: ' + key)
            if datetime.fromisoformat(record['retrievedAt']).tzinfo is None:
                raise ValueError('Missing CPI acquisition timezone')
        if audit['checkedAt'] != max((r['retrievedAt'] for r in audit['series'].values()), key=datetime.fromisoformat):
            raise ValueError('CPI audit time does not match source acquisition times')
        table = dataset['actual']['cpiHeatmap']
        history = table['history']
        expected = {key.removesuffix('_mom') + '_yoy' for key in CONTRACT if key != 'core_cpi_mom'}
        if len(history['rows']) != len(expected) or {r['id'] for r in history['rows']} != expected:
            raise ValueError('CPI heatmap row set changed')
        if table['periods'] != history['periods'][:12]:
            raise ValueError('CPI latest month was silently rolled back')
        rows = {r['id']: r for r in history['rows']}
        mom_observations = {}
        for row in history['rows']:
            key = row['id'].removesuffix('_yoy') + '_mom'
            source = row['source']
            if source.get('mom') != source_metadata(key):
                raise ValueError('CPI row canonical source identity mismatch: ' + key)
            if source['momCode'] != CONTRACT[key]['code'] or source['momName'] != CONTRACT[key]['name'] or source['momAdjustment'] != adjustment_for(key):
                raise ValueError('CPI row adjustment identity mismatch: ' + key)
            if len(row['mom']) != len(history['periods']) or len(row['yoy']) != len(history['periods']):
                raise ValueError('CPI row calendar mismatch')
            pairs = [(d, v) for d, v in reversed(list(zip(history['periods'], row['mom']))) if v is not None]
            record = audit['series'][key]
            if len(pairs) != record['points'] or series_digest([d for d, _ in pairs], [v for _, v in pairs]) != record['normalizedSeriesSHA256']:
                raise ValueError('CPI row does not match audited source values: ' + key)
            if not pairs or (record['first'][:6], record['last'][:6]) != (pairs[0][0], pairs[-1][0]):
                raise ValueError('CPI row observation boundary mismatch: ' + key)
            # Heatmap values are published to two decimal places.
            if round(record['latest'], 2) != pairs[-1][1]:
                raise ValueError('CPI row latest observation mismatch: ' + key)
            mom_observations[key] = pairs
        if len(table['rows']) != len(expected) or {r['id'] for r in table['rows']} != expected:
            raise ValueError('CPI recent row set changed')
        for row in table['rows']:
            full = rows[row['id']]
            if row['source'] != full['source'] or any(row[field] != full[field][:12] for field in ('yoy', 'mom')):
                raise ValueError('CPI recent rows disagree with complete history')
        core = audit['series']['core_cpi_mom']
        observations = core.get('observations')
        if not isinstance(observations, dict) or not all(isinstance(observations.get(f), list) for f in ('dates', 'values')):
            raise ValueError('CPI core observations required')
        dates, values = observations['dates'], observations['values']
        if (not dates or len(dates) != len(values) or len(dates) != core['points']
                or [d[:6] for d in dates] != sorted({d[:6] for d in dates})):
            raise ValueError('CPI core observation count/calendar mismatch')
        if (core['first'], core['last']) != (dates[0], dates[-1]):
            raise ValueError('CPI core observation boundary mismatch')
        if series_digest(dates, values) != core['normalizedSeriesSHA256']:
            raise ValueError('CPI core observations do not match audited source values')
        if core['latest'] != values[-1]:
            raise ValueError('CPI core latest observation mismatch')
        mom_observations['core_cpi_mom'] = [(d[:6], v) for d, v in zip(dates, values)]
        status = dataset['actual']['releaseStatus']
        yoy_series = {s['id']: s for s in dataset['actual']['cpiTrend']['series']}
        expected_period = max([mom_observations[key][-1][0] for key in ('cpi_mom', 'core_cpi_mom')] + [yoy_series[key]['dates'][-1][:6] for key in ('cpi_yoy', 'core_cpi_yoy')])
        if status['period'] != expected_period:
            raise ValueError('CPI status must show the latest available headline observation')
        for name, key in [('cpiYoy', 'cpi_yoy'), ('coreCpiYoy', 'core_cpi_yoy')]:
            series = yoy_series[key]
            values = {d[:6]: v for d, v in zip(series['dates'], series['values'])}
            if status[name] != values.get(status['period']) or status['latestYoyPeriods'][name] != max(values):
                raise ValueError('CPI YoY status does not match its actual source observations')
        for name, key in [('cpiMom', 'cpi_mom'), ('coreCpiMom', 'core_cpi_mom')]:
            if status.get(name + 'Source') != source_metadata(key):
                raise ValueError('CPI headline source identity mismatch: ' + key)
            record = audit['series'][key]
            expected_value = record['latest'] if record['last'][:6] == status['period'] else None
            observed_value = dict(mom_observations[key]).get(status['period'])
            published_value = round(status[name], 2) if key == 'cpi_mom' and status[name] is not None else status[name]
            if status[name] != expected_value or published_value != observed_value or status[name + 'Code'] != CONTRACT[key]['code']:
                raise ValueError('CPI headline disagrees with source audit')
        if status['period'] == '202610' and (status['cpiYoy'] is not None or status['coreCpiYoy'] is not None or status['missingYoyReason'] != 'prior-year-base-unavailable'):
            raise ValueError('CPI missing prior-year base must not be fabricated')
        for series in dataset['actual']['cpiContributions']['series']:
            if series['id'] == 'contribution_residual' and series.get('diagnosticOnly') is not True:
                raise ValueError('CPI contribution residual must remain diagnostic-only')
        if dataset['actual']['januaryEffect']['source']['code'] != CONTRACT['core_cpi_mom']['code']:
            raise ValueError('January profile must use the core CPI SA source')
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError('Invalid CPI seasonal-adjustment data contract') from exc
