"""Public-only regressions: never load private archives or generate receipts."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from verify_renewed_easing_publish import verify_publication, check_dist

ROOT = Path(__file__).resolve().parents[1]

class ThirdPublicationTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT / 'release/snapshots/renewed-easing-publication-1.json').read_bytes()
        self.data = json.loads(self.raw)
        self.receipt = json.loads((ROOT / 'release/replay-renewed-easing-publication.json').read_bytes())

    def rebound(self):
        raw = (json.dumps(self.data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        sha = hashlib.sha256(raw).hexdigest()
        self.receipt['datasetSHA256'] = sha
        self.receipt['pageQADatasetSHA256'] = sha
        self.receipt['localCandidateReceipt']['datasetSHA256'] = sha
        return raw

    def test_approved_public_snapshot_without_any_private_inputs(self):
        result = verify_publication(self.data, self.raw, self.receipt)
        self.assertEqual(result['nodes'], 232)
        self.assertEqual(result['acceptedCells'], 12)
        self.assertFalse(result['rawOriginalReadbackPerformed'])
        self.assertTrue(result['publicationAuthorized'])

    def test_exact_raw_bytes_required(self):
        with self.assertRaises(ValueError):
            verify_publication(self.data, self.raw + b'\n', self.receipt)

    def test_public_gate_cannot_upgrade_unapproved_candidate(self):
        self.receipt['publicationAuthorized'] = False
        with self.assertRaises(ValueError):
            verify_publication(self.data, self.raw, self.receipt)

    def test_private_readback_claim_required_but_not_reperformed_in_public(self):
        self.receipt['privateChecksPassed'] = False
        with self.assertRaises(ValueError):
            verify_publication(self.data, self.raw, self.receipt)

    def test_page_qa_must_bind_same_actual_snapshot(self):
        self.receipt['pageQADatasetSHA256'] = '0' * 64
        with self.assertRaises(ValueError):
            verify_publication(self.data, self.raw, self.receipt)

    def test_actual_monthly_documents_not_declared_totals(self):
        report = next(r for r in self.data['reports'] if r['channel'] == '知识星球' and r['date'].startswith('2025-09'))
        report['date'] = '2025-10-07'
        raw = self.rebound()
        with self.assertRaises(ValueError):
            verify_publication(self.data, raw, self.receipt)

    def test_quota_does_not_mean_exhaustive_search(self):
        self.data['monthlyCoverage']['rows'][0]['channels']['知识星球']['searchExhaustive'] = True
        raw = self.rebound()
        with self.assertRaises(ValueError):
            verify_publication(self.data, raw, self.receipt)

    def test_historical_eligibility_cannot_be_upgraded(self):
        self.data['researchEvidence'][0]['historicalAsOfEligible'] = True
        raw = self.rebound()
        with self.assertRaises(ValueError):
            verify_publication(self.data, raw, self.receipt)

    def test_private_path_rejected_even_with_rebound_sha(self):
        self.data['privateLocalPath'] = 'E:/HermesProject/private-paid.pdf'
        raw = self.rebound()
        with self.assertRaises(ValueError):
            verify_publication(self.data, raw, self.receipt)

    def test_duplicate_node_identity_rejected(self):
        entries = self.data['marketAnalysis']['sections'][0]['deepDive']['expectationTimeline']
        entries[1]['id'] = entries[0]['id']
        raw = self.rebound()
        with self.assertRaises(ValueError):
            verify_publication(self.data, raw, self.receipt)

    def test_dist_requires_nonempty_actual_public_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                check_dist(Path(directory))
            (Path(directory) / 'index.js').write_text('console.log("public");', encoding='utf-8')
            self.assertEqual(check_dist(Path(directory)), 1)

    def test_private_pdf_never_allowed_in_dist(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'index.js').write_text('console.log("public");', encoding='utf-8')
            (Path(directory) / 'paid.pdf').write_bytes(b'%PDF')
            with self.assertRaises(ValueError):
                check_dist(Path(directory))

if __name__ == '__main__':
    unittest.main()
