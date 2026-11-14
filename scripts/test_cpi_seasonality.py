"""CPI adjustment identity is a contract, not a display-label assumption."""
import copy
import json
from pathlib import Path
import unittest
import refresh_ifind_us_inflation as inflation

ROOT = Path(__file__).resolve().parents[1]


class CpiSeasonalityTests(unittest.TestCase):
    def review_dataset(self):
        """Public candidate only: regression tests must not depend on private raw files."""
        return json.loads((ROOT / 'src/data/usInflationData.json').read_bytes())

    def test_heatmap_latest_cannot_be_changed_with_matching_status(self):
        import cpi_seasonality as contract
        data = self.review_dataset()
        contract.validate_dataset(data)
        for key in contract.CONTRACT:
            if key == 'core_cpi_mom':
                continue
            wrong = copy.deepcopy(data)
            wrong['dataQuality']['cpiSeasonality']['series'][key]['latest'] = 9.9
            if key == 'cpi_mom':
                wrong['actual']['releaseStatus']['cpiMom'] = 9.9
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'CPI row latest observation mismatch: ' + key):
                contract.validate_dataset(wrong)

    def test_heatmap_boundaries_cannot_be_changed_with_matching_metadata_or_status(self):
        import cpi_seasonality as contract
        data = self.review_dataset()
        contract.validate_dataset(data)
        for key in contract.CONTRACT:
            if key == 'core_cpi_mom':
                continue
            for field, metadata_field, date in [('first', 'sdate', '19000131'), ('last', 'edate', '20261130')]:
                wrong = copy.deepcopy(data)
                record = wrong['dataQuality']['cpiSeasonality']['series'][key]
                record[field] = record['metadata'][metadata_field] = date
                if key == 'cpi_mom' and field == 'last':
                    wrong['actual']['releaseStatus'].update(period='202611', coreCpiMom=None,
                                                          missingYoyReason='not-available-for-period')
                with self.subTest(key=key, field=field), self.assertRaisesRegex(ValueError, 'CPI row observation boundary mismatch: ' + key):
                    contract.validate_dataset(wrong)

    def test_core_public_observations_are_complete_unrounded_parsed_source(self):
        from test_pce_distribution import synthetic_ifind
        raw = synthetic_ifind()  # Unit fixture only, never candidate evidence.
        raw['core_cpi_mom']['data']['tables'][0]['value'][-1] = '0.123456789'
        data = inflation.build_dataset(raw, raw['__batchGeneratedAt'], 'synthetic-only.json')
        dates, values = inflation.fetch_response_series(raw['core_cpi_mom'], inflation.SERIES_SPEC['core_cpi_mom'][0])
        record = data['dataQuality']['cpiSeasonality']['series']['core_cpi_mom']
        self.assertIn('observations', record, 'Core CPI needs public full-history observation evidence')
        self.assertEqual(record['observations'], {'dates': dates, 'values': values})
        self.assertEqual((record['first'], record['last'], record['points'], record['latest']),
                         (dates[0], dates[-1], len(dates), values[-1]))
        self.assertEqual(record['observations']['values'][-1], 0.123456789)

    def test_core_summaries_and_digest_are_bound_to_public_observations(self):
        import cpi_seasonality as contract
        data = self.review_dataset()
        contract.validate_dataset(data)
        cases = {
            'missing': 'CPI core observations required',
            'empty': 'CPI core observation count/calendar mismatch',
            'length': 'CPI core observation count/calendar mismatch',
            'count': 'CPI core observation count/calendar mismatch',
            'digest': 'CPI core observations do not match audited source values',
            'value': 'CPI core observations do not match audited source values',
            'first': 'CPI core observation boundary mismatch',
            'last-day': 'CPI core observation boundary mismatch',
            'future-status': 'CPI core observation boundary mismatch',
            'latest-status': 'CPI core latest observation mismatch',
            'unrounded-latest': 'CPI core latest observation mismatch',
            'reordered': 'CPI core observation count/calendar mismatch',
        }
        for kind, message in cases.items():
            wrong = copy.deepcopy(data)
            record = wrong['dataQuality']['cpiSeasonality']['series']['core_cpi_mom']
            observations = record['observations']
            if kind == 'missing': del record['observations']
            elif kind == 'empty': observations.update(dates=[], values=[])
            elif kind == 'length': observations['values'].pop()
            elif kind == 'count': record['points'] -= 1
            elif kind == 'digest': record['normalizedSeriesSHA256'] = '0' * 64
            elif kind == 'value': observations['values'][10] += 1
            elif kind == 'first': record['first'] = record['metadata']['sdate'] = '19570201'
            elif kind == 'last-day': record['last'] = record['metadata']['edate'] = '20261001'
            elif kind == 'future-status':
                record['last'] = record['metadata']['edate'] = '20261130'
                wrong['actual']['releaseStatus'].update(period='202611', cpiMom=None,
                                                      missingYoyReason='not-available-for-period')
            elif kind in ('latest-status', 'unrounded-latest'):
                record['latest'] = wrong['actual']['releaseStatus']['coreCpiMom'] = 9.9 if kind == 'latest-status' else 0.3001
            else:
                observations['dates'][1], observations['dates'][2] = observations['dates'][2], observations['dates'][1]
                record['normalizedSeriesSHA256'] = contract.series_digest(observations['dates'], observations['values'])
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, message):
                contract.validate_dataset(wrong)

    def test_contribution_residual_must_remain_strictly_diagnostic_only(self):
        import cpi_seasonality as contract
        data = self.review_dataset()
        contract.validate_dataset(data)
        for value in (False, 1, 'true', None):
            wrong = copy.deepcopy(data)
            residual = next(s for s in wrong['actual']['cpiContributions']['series'] if s['id'] == 'contribution_residual')
            if value is None:
                del residual['diagnosticOnly']
            else:
                residual['diagnosticOnly'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'CPI contribution residual must remain diagnostic-only'):
                contract.validate_dataset(wrong)

    def test_current_gate_rejects_review_reproductions_against_real_public_candidate(self):
        import verify_cpi_correction_publish as gate
        documents = {name: json.loads((ROOT / name).read_bytes()) for name in gate.DATA_FILES}
        data = documents[gate.INFLATION]
        bindings = [{'role': 'row:' + row['id'], 'paths': [
            ['actual', 'cpiHeatmap', 'rows', i, 'source', 'mom'],
            ['actual', 'cpiHeatmap', 'history', 'rows', i, 'source', 'mom']]}
            for i, row in enumerate(data['actual']['cpiHeatmap']['rows'])]
        bindings += [{'role': 'headline:' + role, 'paths': [['actual', 'releaseStatus', name + 'Source']]}
                     for role, name in [('cpi', 'cpiMom'), ('core', 'coreCpiMom')]]
        # In-memory metadata bindings, NOT authorization or a corrected reference artifact.
        binding_context = {'saBindings': gate.bind_sources(data, bindings)}
        baseline = copy.deepcopy(documents)
        gate.validate_current(documents, baseline, binding_context, ROOT)
        for key, name in [('cpi_mom', 'cpiMom'), ('core_cpi_mom', 'coreCpiMom')]:
            for kind in ('latest', 'future'):
                wrong = copy.deepcopy(documents)
                record = wrong[gate.INFLATION]['dataQuality']['cpiSeasonality']['series'][key]
                status = wrong[gate.INFLATION]['actual']['releaseStatus']
                if kind == 'latest':
                    record['latest'] = status[name] = 9.9
                else:
                    record['last'] = record['metadata']['edate'] = '20261130'
                    status.update(period='202611', missingYoyReason='not-available-for-period')
                    status['coreCpiMom' if name == 'cpiMom' else 'cpiMom'] = None
                reason = ('CPI row ' if key == 'cpi_mom' else 'CPI core ') + (
                    'latest observation mismatch' if kind == 'latest' else 'observation boundary mismatch')
                with self.subTest(key=key, kind=kind), self.assertRaisesRegex(ValueError, reason):
                    gate.validate_current(wrong, baseline, binding_context, ROOT)

    def test_only_two_registered_ordinary_sources_are_nsa(self):
        import cpi_seasonality as contract
        expected = {
            'food_away_mom': ('G005464519', '美国:CPI:家庭外就餐:当月环比', 'Food away from home'),
            'personal_services_mom': ('G005464538', '美国:CPI:其他个人服务:当月环比', 'Miscellaneous personal services'),
        }
        for key, (code, name, alias) in expected.items():
            meta = {'displayid': code, 'name': name, 'unit': '%', 'frequency': '月', 'datasource': '美国劳工局'}
            contract.validate_metadata(key, meta)
            source = contract.source_metadata(key)
            self.assertEqual(source['seasonalAdjustment'], 'NSA')
            self.assertEqual(source['entityAlias'], alias)
            self.assertEqual(source['name'], name)
            self.assertEqual(inflation.SERIES_SPEC[key][0], code)
        self.assertEqual(sum(contract.source_metadata(k)['seasonalAdjustment'] == 'SA' for k in contract.CONTRACT), 22)
        self.assertEqual(sum(contract.source_metadata(k)['seasonalAdjustment'] == 'NSA' for k in contract.CONTRACT), 2)

    def test_contribution_diagnostics_do_not_treat_an_arithmetic_residual_as_economic_coverage(self):
        self.assertTrue(hasattr(inflation, 'contribution_diagnostics'), 'Missing non-self-closing contribution audit')
        audit = inflation.contribution_diagnostics(['20260930', '20261031'], [0.173, 0.048])
        self.assertEqual(audit['comparedPeriods'], 2)
        self.assertEqual(audit['outsideRoundingBudget'], 1)
        self.assertEqual(audit['roundingBudget'], 0.052)
        self.assertTrue(audit['latest']['withinRoundingBudget'])
        self.assertIn('未核实', audit['note'])

    def test_cli_refuses_unaudited_or_unversioned_replay_without_overwriting(self):
        import subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'input.json'; target = Path(folder) / 'output.json'
            original = b'{"preserve":true}'; target.write_bytes(original)
            for raw, message in [({'__pceDistribution': {}}, 'seasonality metadata'),
                                 ({'__pceDistribution': {}, '__cpiSeasonality': {}}, 'batch vintage')]:
                source.write_text(json.dumps(raw), encoding='utf-8')
                result = subprocess.run([sys.executable, str(ROOT / 'scripts/refresh_ifind_us_inflation.py'), '--input', str(source), '--output', str(target)], cwd=ROOT, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertEqual(target.read_bytes(), original)

    def test_publication_validation_rejects_mixed_sources_and_changed_heatmap_values(self):
        import cpi_seasonality as contract
        self.assertTrue(hasattr(contract, 'validate_dataset'), 'Missing publication-time CPI semantic validator')
        data = json.loads((ROOT / 'src/data/usInflationData.json').read_bytes())
        contract.validate_dataset(data)
        for kind in ['ordinary-code', 'wrong-name', 'false-value', 'fake-yoy', 'fresh-batch-time', 'rolled-back-status']:
            wrong = copy.deepcopy(data)
            if kind == 'ordinary-code': wrong['actual']['cpiHeatmap']['history']['rows'][0]['source']['momCode'] = 'G002600387'
            elif kind == 'wrong-name': wrong['dataQuality']['cpiSeasonality']['series']['cpi_mom']['metadata']['name'] = '美国:CPI:环比'
            elif kind == 'false-value': wrong['actual']['cpiHeatmap']['history']['rows'][0]['mom'][0] = (wrong['actual']['cpiHeatmap']['history']['rows'][0]['mom'][0] or 0) + 1
            elif kind == 'fake-yoy': wrong['actual']['releaseStatus']['cpiYoy'] = (wrong['actual']['releaseStatus']['cpiYoy'] or 0) + 1
            elif kind == 'rolled-back-status':
                status = wrong['actual']['releaseStatus']
                status['period'] = inflation.shift_months([status['period'] + '01'], -1)[0][:6]
                status['cpiMom'] = None; status['coreCpiMom'] = None
            else: wrong['generatedAt'] = '2026-11-14T13:00:00+00:00'
            with self.subTest(kind=kind), self.assertRaises(ValueError): contract.validate_dataset(wrong)

    def test_dataset_includes_audit_and_metric_specific_release_status(self):
        from cpi_seasonality import CONTRACT
        raw = {key: {'code': 1, 'data': {'tables': [{'displayid': spec[0], 'id': spec[0][1:].lstrip('0'),
                                                   'time': ['20250131', '20250228', '20250331', '20250430', '20260131', '20260228', '20260331', '20260430'],
                                                   'value': ['3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8']}]}} for key, spec in inflation.SERIES_SPEC.items()}
        raw['__cpiSeasonality'] = {'metadata': {k: {'displayid': v['code'], **{field: v[field] for field in ('name', 'unit', 'frequency', 'datasource')}} for k, v in CONTRACT.items()},
                                    'retrievedAt': {k: '2026-11-14T11:00:00+00:00' for k in CONTRACT}}
        data = inflation.build_dataset(raw, '2026-11-12T11:14:09+00:00', 'fixture-only.json')
        self.assertIn('cpiSeasonality', data['dataQuality'])
        self.assertTrue(data['dataQuality']['cpiSeasonality']['metadataVerified'])
        self.assertIn('releaseStatus', data['actual'])
        self.assertEqual(data['generatedAt'], '2026-11-12T11:14:09+00:00')

    def test_release_status_separates_missing_yoy_base_from_available_mom(self):
        self.assertTrue(hasattr(inflation, 'build_release_status'), 'Missing metric-specific release status')
        parsed = {'cpi_mom': (['20261031'], [0.4]), 'core_cpi_mom': (['20261031'], [0.3]),
                  'cpi_yoy': (['20260930'], [3.7]), 'core_cpi_yoy': (['20260930'], [2.6]),
                  'pce_yoy': (['20260930'], [2.8])}
        status = inflation.build_release_status(parsed)
        self.assertEqual(status['period'], '202610')
        self.assertEqual(status['cpiMom'], 0.4)
        self.assertEqual(status['coreCpiMom'], 0.3)
        self.assertIsNone(status['cpiYoy'])
        self.assertEqual(status['missingYoyReason'], 'prior-year-base-unavailable')
        self.assertEqual(status['pcePeriod'], '202609')
        parsed['cpi_mom'] = (['20261130'], [0.1])
        self.assertEqual(inflation.build_release_status(parsed)['missingYoyReason'], 'not-available-for-period')

    def test_audit_requires_all_source_metadata_and_preserves_base_vintage(self):
        import cpi_seasonality as contract
        self.assertTrue(hasattr(contract, 'build_audit'), 'Missing CPI source audit envelope')
        parsed = {k: (['20261031'], [0.4]) for k in contract.CONTRACT}
        envelope = {'metadata': {k: {'displayid': v['code'], **{field: v[field] for field in ('name', 'unit', 'frequency', 'datasource')}} for k, v in contract.CONTRACT.items()},
                    'retrievedAt': {k: '2026-11-14T11:00:00+00:00' for k in contract.CONTRACT}}
        audit = contract.build_audit(envelope, parsed, '2026-11-12T11:14:09+00:00')
        self.assertTrue(audit['metadataVerified'])
        self.assertEqual(audit['baseGeneratedAt'], '2026-11-12T11:14:09+00:00')
        self.assertEqual(audit['checkedAt'], '2026-11-14T11:00:00+00:00')
        self.assertEqual(len(audit['series']), 24)
        self.assertEqual(audit['classificationCounts'], {'total': 24, 'SA': 22, 'NSA': 2})
        self.assertEqual(audit['heatmapCounts'], {'total': 23, 'SA': 21, 'NSA': 2})
        self.assertIn('2026-10官方例外核对', audit['note'])
        self.assertIn('未来发布', audit['note'])
        self.assertNotIn('两项本期BLS未季调', audit['note'])
        for key, record in audit['series'].items():
            self.assertEqual(record['seasonalAdjustment'], contract.source_metadata(key)['seasonalAdjustment'])
        altered = copy.deepcopy(envelope); del altered['metadata']['cpi_mom']
        with self.assertRaises(ValueError): contract.build_audit(altered, parsed, '2026-11-12T11:14:09+00:00')

    def test_january_profile_discloses_counts_and_never_invents_zero_for_no_sample(self):
        self.assertTrue(hasattr(inflation, 'monthly_profile'), 'Missing sample-aware monthly profile')
        profile = inflation.monthly_profile(['20220131', '20230131', '20230228'], [0.2, 0.4, 0.0], 2022, 2025)
        self.assertEqual(profile['sampleCounts'][:3], [2, 1, 0])
        self.assertEqual(profile['values'][:3], [0.3, 0.0, None])

    def test_detail_retains_latest_mom_and_marks_missing_yoy_instead_of_rolling_back(self):
        self.assertTrue(hasattr(inflation, 'build_detail_rows'), 'Missing independent latest-period detail builder')
        parsed = {}
        for _, yoy, mom, _ in inflation.DETAIL_ROWS:
            parsed[yoy] = (['20260930'], [3.7])
            parsed[mom] = (['20260930', '20261031'], [0.6, 0.4])
        rows = inflation.build_detail_rows(parsed)
        for row in rows:
            self.assertEqual(row['observation'], '20261031')
            self.assertIsNone(row['yoy'])
            self.assertIsNone(row['yoyChange'])
            self.assertEqual(row['mom'], 0.4)
            self.assertEqual(row['latestAvailableYoy'], {'observation': '20260930', 'value': 3.7})
            self.assertEqual(row['source']['momAdjustment'], 'SA')

    def test_derived_monthly_changes_never_bridge_a_missing_month(self):
        dates, values = inflation.pct_change_series(['20250131', '20250331', '20250430'], [100, 121, 133.1], lag=1)
        self.assertEqual(dates, ['20250430'])
        self.assertAlmostEqual(values[0], 10)

    def test_latest_heatmap_month_and_sources_do_not_depend_on_yoy_availability(self):
        parsed = {}
        for _, _, yoy, mom, weight, _ in inflation.HEATMAP_ROWS:
            parsed[yoy] = (['20250930'], [3.7])
            parsed[mom] = (['20250930', '20261031'], [0.6, 0.4])
            if weight: parsed[weight] = (['20250930'], [10.0])
        table = inflation.build_heatmap(parsed)
        self.assertEqual(table['periods'][0], '202610')
        self.assertIsNone(table['rows'][0]['yoy'][0])
        self.assertEqual(table['rows'][0]['mom'][0], 0.4)
        for row, spec in zip(table['rows'], inflation.HEATMAP_ROWS):
            self.assertEqual(row['source']['momCode'], inflation.SERIES_SPEC[spec[3]][0])
            expected_adjustment = 'NSA' if row['id'] in {'food_away_yoy', 'personal_services_yoy'} else 'SA'
            self.assertEqual(row['source']['momAdjustment'], expected_adjustment)
            self.assertEqual('季调' in row['source']['momName'], expected_adjustment == 'SA')
            self.assertIn('mom', row['source'])
            self.assertEqual(row['source']['mom']['seasonalAdjustment'], expected_adjustment)
            self.assertEqual(row['source']['mom']['code'], row['source']['momCode'])

    def test_fetch_rejects_wrong_adjustment_before_requesting_values(self):
        from unittest.mock import patch
        code = 'G005464034'
        metadata = {'displayid': code, 'name': '美国:CPI:当月环比', 'unit': '%', 'frequency': '月', 'sdate': '19470228', 'datasource': '美国劳工局'}
        payload = {'code': 1, 'data': {'tables': [{'displayid': code, 'id': '5464034', 'time': ['19470228'], 'value': ['0.1']}]}}
        with patch.dict(inflation.SERIES_SPEC, {'cpi_mom': (code, 'CPI环比', '#000')}, clear=True), patch.object(inflation, 'search_indicator', return_value=metadata), patch.object(inflation, 'fetch_indicator', return_value=payload) as fetch:
            with self.assertRaisesRegex(ValueError, 'seasonal-adjustment'):
                inflation.fetch_all('test-only-not-a-credential')
            fetch.assert_not_called()

    def test_total_core_and_heatmap_mom_sources_follow_exact_classification(self):
        self.assertEqual(inflation.SERIES_SPEC['cpi_mom'][0], 'G005464034')
        self.assertEqual(inflation.SERIES_SPEC['core_cpi_mom'][0], 'G005464040')
        from cpi_seasonality import CONTRACT, validate_metadata
        keys = {r[3] for r in inflation.HEATMAP_ROWS} | {'core_cpi_mom'}
        self.assertEqual(set(CONTRACT), keys)
        for key in keys:
            row = CONTRACT[key]
            self.assertEqual(inflation.SERIES_SPEC[key][0], row['code'])
            meta = {'displayid': row['code'], 'name': row['name'], 'unit': '%', 'frequency': '月', 'datasource': '美国劳工局'}
            validate_metadata(key, meta)
            for field, value in [('displayid', 'G002600387'), ('name', row['name'].replace('季调', '非季调') if '季调' in row['name'] else row['name'] + ':季调'), ('unit', '指数'), ('frequency', '季'), ('datasource', '非美国劳工局')]:
                wrong = copy.deepcopy(meta); wrong[field] = value
                with self.subTest(key=key, field=field), self.assertRaises(ValueError):
                    validate_metadata(key, wrong)

    def test_dataset_enforces_exact_classification_counts_and_headline_sa(self):
        import cpi_seasonality as contract
        from test_pce_distribution import synthetic_ifind
        raw = synthetic_ifind()
        data = inflation.build_dataset(raw, raw['__batchGeneratedAt'], 'synthetic-only.json')
        contract.validate_dataset(data)
        for kind in ('exception-sa', 'total-nsa', 'other-entity', 'audit-count', 'audit-class', 'headline-nsa'):
            wrong = copy.deepcopy(data)
            rows = wrong['actual']['cpiHeatmap']['history']['rows']
            if kind == 'exception-sa':
                row = next(r for r in rows if r['id'] == 'food_away_yoy')
                row['source']['momAdjustment'] = 'SA'
            elif kind == 'total-nsa': rows[0]['source']['mom']['seasonalAdjustment'] = 'NSA'
            elif kind == 'other-entity':
                row = next(r for r in rows if r['id'] == 'personal_services_yoy')
                row['source']['mom']['entityAlias'] = 'Other personal services'
            elif kind == 'audit-count': wrong['dataQuality']['cpiSeasonality']['classificationCounts']['SA'] = 24
            elif kind == 'audit-class': wrong['dataQuality']['cpiSeasonality']['series']['food_away_mom']['seasonalAdjustment'] = 'SA'
            else: wrong['actual']['releaseStatus']['coreCpiMomSource']['seasonalAdjustment'] = 'NSA'
            message = {'exception-sa': 'row adjustment identity', 'total-nsa': 'canonical source identity',
                       'other-entity': 'canonical source identity', 'audit-count': 'classification counts',
                       'audit-class': 'audit classification', 'headline-nsa': 'headline source identity'}[kind]
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, message):
                contract.validate_dataset(wrong)

    def test_exception_registry_cannot_be_relabeled_expanded_or_change_entity(self):
        import cpi_seasonality as contract
        from unittest.mock import patch
        for key, field, value in [('food_away_mom', 'seasonalAdjustment', 'SA'),
                                   ('personal_services_mom', 'entityAlias', 'Other personal services'),
                                   ('personal_services_mom', 'code', 'G004765676'),
                                   ('food_away_mom', 'adjustmentBasis', 'all-historical-releases-NSA')]:
            wrong = copy.deepcopy(contract.CONTRACT_DOCUMENT)
            wrong['nsaExceptions'][key][field] = value
            with self.subTest(key=key, field=field), patch.object(contract, 'CONTRACT_DOCUMENT', wrong):
                with self.assertRaisesRegex(ValueError, 'registered NSA exception classification'):
                    contract.source_metadata(key)
        wrong = copy.deepcopy(contract.CONTRACT_DOCUMENT)
        wrong['nsaExceptions']['cpi_mom'] = copy.deepcopy(wrong['nsaExceptions']['food_away_mom'])
        with patch.object(contract, 'CONTRACT_DOCUMENT', wrong):
            with self.assertRaisesRegex(ValueError, 'registered NSA exception classification'):
                contract.source_metadata('cpi_mom')

    def test_fetch_all_verifies_both_exception_metadata_and_records_acquisition_time(self):
        from unittest.mock import patch
        from datetime import datetime
        import cpi_seasonality as contract
        specs = {k: inflation.SERIES_SPEC[k] for k in ('food_away_mom', 'personal_services_mom')}
        def metadata(_token, code):
            row = next(v for v in contract.CONTRACT.values() if v['code'] == code)
            return {'displayid': code, **{f: row[f] for f in ('name', 'unit', 'frequency', 'datasource')}, 'sdate': '20261031', 'edate': '20261031'}
        def payload(_token, code, _start, _end):
            return {'code': 1, 'data': {'tables': [{'displayid': code, 'id': code[1:].lstrip('0'), 'time': ['20261031'], 'value': ['0.5']}]}}
        with patch.dict(inflation.SERIES_SPEC, specs, clear=True), patch.object(inflation, 'search_indicator', side_effect=metadata), patch.object(inflation, 'fetch_indicator', side_effect=payload):
            result = inflation.fetch_all('unit-test-only')
        for key in specs:
            contract.validate_metadata(key, result['__cpiSeasonality']['metadata'][key])
            self.assertIsNotNone(datetime.fromisoformat(result['__cpiSeasonality']['retrievedAt'][key]).tzinfo)


if __name__ == '__main__':
    unittest.main()
