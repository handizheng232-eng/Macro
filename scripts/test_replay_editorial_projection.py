"""TEST ONLY editorial projection fixtures; no empirical source data."""
import unittest
import importlib
import importlib.util
from copy import deepcopy


class EditorialProjectionTests(unittest.TestCase):
    def setup_payloads(self):
        base = {'title': 'TEST ONLY', 'startDate': '1999-01-01', 'asOf': '1999-01-31',
                'sources': [{'id': 'test-source', 'date': '1999-01-02'}],
                'reports': [{'id': 'test-report', 'sha256': 'TEST ONLY'}],
                'events': [{'id': 'test-event', 'raw': 'TEST ONLY original evidence'}],
                'marketAnalysis': {'title': 'old', 'conclusion': 'old', 'limitations': [], 'sections': [{'id': 'test-topic'}]}}
        entry = {'id': 'test-entry', 'date': '1999-01-02', 'title': 'TEST ONLY', 'text': 'TEST ONLY interpretation [1]',
                 'sourceIds': ['test-source'], 'reportIds': ['test-report'], 'evidenceRefs': ['test-locator'],
                 'firstAvailableDate': None, 'historicalAsOfEligible': False, 'retrospectiveOnly': True}
        study = {'title': 'new', 'conclusion': 'new', 'limitations': [], 'sections': [{'id': 'test-topic', 'deepDive': {'expectationTimeline': [entry]}}],
                 'citationSources': [{'number': 1, 'sourceId': 'test-source'}]}
        frame = {'byTopicId': {'test-topic': [{'id': 'test-frame', 'retrospectiveOnly': True, 'series': [], 'datasetPins': []}]}}
        refs = {'test-locator': {'id': 'test-locator', 'reportId': 'test-report', 'actor': 'TEST ONLY name', 'publicationDate': '1999-01-02', 'locatorLabel': 'PDF物理第1页'}}
        return base, study, frame, refs

    def projector(self):
        self.assertIsNotNone(importlib.util.find_spec('replay_editorial_projection'), 'reviewed editorial projection is not implemented')
        return importlib.import_module('replay_editorial_projection').project_editorial

    def test_projects_reviewed_research_charts_and_public_locators_without_mutating_evidence(self):
        base, study, frame, refs = self.setup_payloads()
        original = deepcopy(base)
        result = self.projector()(base, study, frame, refs, {'test-locator'})
        self.assertEqual(base, original)
        self.assertEqual(result['events'], original['events'])
        self.assertEqual(result['reports'], original['reports'])
        section = result['marketAnalysis']['sections'][0]
        self.assertEqual(section['frameworkEvidence'][0]['id'], 'test-frame')
        node = section['deepDive']['expectationTimeline'][0]
        self.assertEqual(node['supportingEvidence'][0]['locatorLabel'], 'PDF物理第1页')
        self.assertEqual(node['text'], 'TEST ONLY interpretation [test-source]')
        self.assertFalse(node['historicalAsOfEligible'])

    def test_rejects_unregistered_source_report_or_locator_instead_of_hiding_bad_binding(self):
        for field in ['sourceIds', 'reportIds', 'evidenceRefs']:
            with self.subTest(field=field):
                base, study, frame, refs = self.setup_payloads()
                study['sections'][0]['deepDive']['expectationTimeline'][0][field].append('test-not-admitted')
                with self.assertRaisesRegex(ValueError, 'unregistered'):
                    self.projector()(base, study, frame, refs, {'test-locator'})

    def test_explicit_methodology_source_stays_unknown_dated_and_does_not_add_stage_facts(self):
        base, study, frame, refs = self.setup_payloads()
        study['sections'][0]['deepDive']['expectationTimeline'][0]['sourceIds'] = ['test-method']
        study['citationSources'][0]['sourceId'] = 'test-method'
        method = {'id': 'test-method', 'title': 'TEST ONLY 方法', 'publisher': 'TEST ONLY', 'url': '', 'date': None,
                  'kind': 'methodology', 'firstAvailableDate': None, 'historicalAsOfEligible': False, 'retrospectiveOnly': True,
                  'privatePath': 'TEST ONLY must not be published', 'privateQuote': 'TEST ONLY private'}
        result = self.projector()(base, study, frame, refs, {'test-locator'}, source_admissions=[method])
        self.assertEqual(result['events'], base['events'])
        self.assertEqual(result['sources'][-1]['date'], '')
        self.assertEqual(result['sources'][-1].get('status'), '当前追溯补充；历史资格未核')
        self.assertFalse(result['sources'][-1]['historicalAsOfEligible'])
        self.assertNotIn('privatePath', result['sources'][-1])
        self.assertNotIn('privateQuote', result['sources'][-1])

    def test_retrospective_framework_cannot_become_historical_or_drop_a_theme(self):
        base, study, frame, refs = self.setup_payloads()
        frame['byTopicId']['test-topic'][0]['retrospectiveOnly'] = False
        with self.assertRaisesRegex(ValueError, 'framework'):
            self.projector()(base, study, frame, refs, {'test-locator'})
        base, study, frame, refs = self.setup_payloads()
        study['sections'][0]['id'] = 'test-different-theme'
        with self.assertRaisesRegex(ValueError, 'theme'):
            self.projector()(base, study, frame, refs, {'test-locator'})

    def test_added_correction_node_is_chronologically_inserted_not_appended_after_august(self):
        base, study, frame, refs = self.setup_payloads()
        early = deepcopy(study['sections'][0]['deepDive']['expectationTimeline'][0])
        late = deepcopy(early)
        late.update(id='test-late', date='1999-01-20')
        study['sections'][0]['deepDive']['expectationTimeline'] = [late, early]
        result = self.projector()(base, study, frame, refs, {'test-locator'})
        self.assertEqual([e['date'] for e in result['marketAnalysis']['sections'][0]['deepDive']['expectationTimeline']], ['1999-01-02', '1999-01-20'])

    def test_unknown_availability_cannot_be_promoted_to_strict_historical_evidence(self):
        base, study, frame, refs = self.setup_payloads()
        study['sections'][0]['deepDive']['expectationTimeline'][0]['historicalAsOfEligible'] = True
        with self.assertRaisesRegex(ValueError, 'historical'):
            self.projector()(base, study, frame, refs, {'test-locator'})


if __name__ == '__main__':
    unittest.main()
