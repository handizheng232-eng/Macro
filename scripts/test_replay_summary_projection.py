"""TEST ONLY summary overlay fixtures; no empirical data."""
import unittest
from copy import deepcopy
import replay_editorial_projection as projection


class SummaryOverlayTests(unittest.TestCase):
    def fixtures(self):
        refs = {'sourceIds': ['test-source'], 'reportIds': ['test-report'], 'evidenceRefs': ['test-node']}
        base = {'startDate': '1999-01-01', 'asOf': '1999-01-31', 'sources': [{'id': 'test-source'}], 'reports': [{'id': 'test-report'}],
                'events': [{'id': 'original-event'}], 'marketAnalysis': {'sections': [{'id': 'test-topic', 'judgement': 'Original judgement',
                'deepDive': {'expectationTimeline': [{'id': 'test-node', 'date': None, 'text': 'Original research', 'historicalAsOfEligible': False,
                'sourceIds': ['test-source'], 'reportIds': ['test-report'], 'evidenceRefs': ['original-locator']}]}, 'frameworkEvidence': [{'id': 'original-chart'}]}]}}
        summaries = {'startDate': base['startDate'], 'asOf': base['asOf'], 'sections': [{'id': 'test-topic',
                     'periodSummary': {'paragraphs': ['TEST ONLY period summary'], **deepcopy(refs)},
                     'aspectSummaries': {'expectationTimeline': {'text': 'TEST ONLY aspect summary', **deepcopy(refs)}}}]}
        return base, summaries

    def apply(self):
        fn = getattr(projection, 'apply_summaries', None)
        self.assertTrue(callable(fn), 'summary overlay admission is not implemented')
        return fn

    def test_summary_overlay_adds_only_two_display_fields_without_mutating_admitted_research(self):
        base, summaries = self.fixtures()
        before = deepcopy(base)
        result = self.apply()(base, summaries)
        self.assertEqual(base, before)
        section = result['marketAnalysis']['sections'][0]
        self.assertEqual(section['periodSummary']['paragraphs'], ['TEST ONLY period summary'])
        self.assertEqual(section['aspectSummaries']['expectationTimeline']['text'], 'TEST ONLY aspect summary')
        self.assertFalse(section['periodSummary']['historicalAsOfEligible'])
        section.pop('periodSummary'); section.pop('aspectSummaries')
        self.assertEqual(result, before)

    def test_scope_or_support_mismatch_fails_closed_not_silently_admitted(self):
        for case in ['window', 'topic', 'source', 'report', 'node', 'role']:
            with self.subTest(case=case):
                base, summaries = self.fixtures()
                section = summaries['sections'][0]
                if case == 'window':
                    summaries['asOf'] = '2000-01-31'
                elif case == 'topic':
                    section['id'] = 'foreign-topic'
                elif case == 'source':
                    section['periodSummary']['sourceIds'] = ['unregistered-source']
                elif case == 'report':
                    section['periodSummary']['reportIds'] = ['unregistered-report']
                elif case == 'node':
                    section['periodSummary']['evidenceRefs'] = ['original-locator']
                else:
                    base['marketAnalysis']['sections'][0]['deepDive']['mechanism'] = [{'id': 'test-mechanism', 'sourceIds': [], 'reportIds': []}]
                    section['aspectSummaries']['mechanism'] = deepcopy(section['aspectSummaries']['expectationTimeline'])
                with self.assertRaises(ValueError):
                    self.apply()(base, summaries)


if __name__ == '__main__':
    unittest.main()
