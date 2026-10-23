"""The explicitly authorized revision is accepted without rewriting old receipts."""
import copy
import json
import unittest
from verify_economic_mechanisms_publish import (
    verify_economic, verify_revision, baseline_bytes, ROOT, RECEIPT, DATA, FIXTURE,
)
from verify_renewed_limited_publish import digest

class EconomicPublicationTests(unittest.TestCase):
    def test_authorized_revision(self):
        receipt = json.loads((ROOT / RECEIPT).read_bytes())
        result = verify_economic(receipt)
        self.assertEqual(result['officialParagraphs'], 16)
        self.assertEqual(result['institutionParagraphs'], 8)
        self.assertFalse(result['fullStageReady'])

    def test_authorization_scope_and_every_pin_fail_closed(self):
        receipt = json.loads((ROOT / RECEIPT).read_bytes())
        for field, value in [('schemaVersion', 'wrong'), ('scope', 'all-stages'),
                             ('publicationAuthorized', False), ('pageQAComplete', False),
                             ('fullStageReady', True), ('pinEncoding', 'ignore-whitespace'),
                             ('datasetSHA256', '0' * 64)]:
            with self.subTest(field=field):
                changed = copy.deepcopy(receipt)
                changed[field] = value
                with self.assertRaises(ValueError):
                    verify_economic(changed)
        for name in receipt['publicFilePins']:
            for mode in ['remove', 'alter']:
                with self.subTest(name=name, mode=mode):
                    changed = copy.deepcopy(receipt)
                    if mode == 'remove':
                        del changed['publicFilePins'][name]
                    else:
                        changed['publicFilePins'][name] = '0' * 64
                    with self.assertRaises(ValueError):
                        verify_economic(changed)

    def test_scope_and_condition_mutations_without_outer_hash_shortcut(self):
        baseline = json.loads(baseline_bytes(DATA))
        data = json.loads((ROOT / DATA).read_bytes())
        receipt = json.loads((ROOT / RECEIPT).read_bytes())
        fixture = json.loads((ROOT / FIXTURE).read_bytes())
        verify_revision(data, baseline, receipt, fixture)
        for mode in ['official', 'institution', 'citation', 'month-order', 'history',
                     'new-source-history', 'other-topic', 'seven-increments', 'market-series',
                     'quota', 'CME', 'summary-node', 'report', 'source-duplicate']:
            with self.subTest(mode=mode):
                changed = copy.deepcopy(data)
                r = copy.deepcopy(receipt)
                topic = next(s for s in changed['marketAnalysis']['sections'] if s['id'] == 'inflation-vintages')
                summary = topic['periodSummary']
                if mode == 'official': summary['paragraphs'][0] += ' altered'
                if mode == 'institution': summary['paragraphs'][2] = summary['paragraphs'][2][:-30]
                if mode == 'citation': summary['paragraphSources'][0] = []
                if mode == 'month-order': summary['paragraphs'][0], summary['paragraphs'][3] = summary['paragraphs'][3], summary['paragraphs'][0]
                if mode == 'history': summary['historicalAsOfEligible'] = True
                if mode == 'summary-node': summary['evidenceRefs'] = []
                if mode == 'report': summary['reportIds'] = []
                if mode == 'other-topic': changed['marketAnalysis']['sections'][0]['periodSummary']['paragraphs'][0] += ' changed'
                if mode in ['seven-increments', 'CME']:
                    nodes = [n for s in changed['marketAnalysis']['sections'] for ns in s['deepDive'].values() for n in ns]
                    target = next(n for n in nodes if n['id'].startswith('local03-')) if mode == 'seven-increments' else next(n for n in nodes if n['id'] == 'local02-cme-gap')
                    target['text'] = 'changed'
                if mode == 'market-series': changed['marketPaths'] = []
                if mode == 'quota': changed['monthlyCoverage']['rows'][3]['channels']['Wind']['bodyCount'] = 15
                if mode == 'source-duplicate': changed['sources'].append(copy.deepcopy(changed['sources'][0]))
                if mode == 'new-source-history':
                    source = next(s for s in changed['sources'] if s['id'].startswith('EM01-'))
                    source['firstAvailableDate'] = '2025-09-01'
                    r['approvedAddedSourceDigests'][source['id']] = digest(source)
                # Rehash the affected summary: independent fixture and scope checks must reject.
                r['approvedSummaryDigests'][topic['id']] = digest(summary)
                self.assertNotEqual(changed, data)
                with self.assertRaises(ValueError):
                    verify_revision(changed, baseline, r, fixture)


if __name__ == '__main__':
    unittest.main()
