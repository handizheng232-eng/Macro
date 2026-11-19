import json
from pathlib import Path
import shutil
import tempfile
import unittest
import verify_aggressive_publish as v

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        m, _, _ = v.contract(v.ROOT)
        for n in set(m['baselinePins']) | v.CHANGES | {v.RECEIPT, v.INVERSE}:
            p = self.root / n
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(v.ROOT / n, p)
    def tearDown(self):
        self.tmp.cleanup()
    def receipt(self, fn):
        p = self.root / v.RECEIPT
        r = json.loads(p.read_bytes()); fn(r)
        p.write_text(json.dumps(r), encoding='utf-8')
    def mutate_data(self, fn):
        p = self.root / v.DATA
        d = json.loads(p.read_bytes()); fn(d)
        p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        self.receipt(lambda r: r['sourcePins'].__setitem__(v.DATA, v.sha(p.read_bytes())))
    def test_valid(self):
        self.assertEqual(v.verify(self.root)['status'], 'PASS_AGGRESSIVE_PUBLICATION_01')
    def test_absent_authorization(self):
        self.receipt(lambda r: r.__setitem__('publicationAuthorized', False))
        with self.assertRaisesRegex(ValueError, 'authorization'): v.verify(self.root)
    def test_changed_scope(self):
        self.receipt(lambda r: r.__setitem__('scope', 'other'))
        with self.assertRaisesRegex(ValueError, 'scope'): v.verify(self.root)
    def test_missing_pin(self):
        self.receipt(lambda r: r['sourcePins'].pop(v.DATA))
        with self.assertRaisesRegex(ValueError, 'pin scope'): v.verify(self.root)
    def test_rehashed_economic_edit(self):
        self.mutate_data(lambda d: d['reviewProjection']['conclusion'][0].__setitem__('text', 'changed'))
        with self.assertRaisesRegex(ValueError, 'economic text'): v.verify(self.root)
    def test_rehashed_qualification_upgrade(self):
        self.mutate_data(lambda d: d['localReview'].__setitem__('fullStageReady', True))
        with self.assertRaisesRegex(ValueError, 'economic text'): v.verify(self.root)
    def test_rehashed_star_zero(self):
        self.mutate_data(lambda d: d['localReview']['verifiedCoverage']['star'].__setitem__('obtained', 0))
        with self.assertRaisesRegex(ValueError, 'economic text'): v.verify(self.root)
    def test_rehashed_citation_edit(self):
        self.mutate_data(lambda d: d['sources'][0].__setitem__('url', 'https://example.com/'))
        with self.assertRaisesRegex(ValueError, 'economic text'): v.verify(self.root)
    def test_legacy_receipt_mutation(self):
        p=self.root/'release/comments-publication-01.json'; p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError, 'baseline differs'): v.verify(self.root)
    def test_extra_public_file(self):
        (self.root/'public/private.txt').write_text('private')
        with self.assertRaisesRegex(ValueError, 'unapproved'): v.verify(self.root)
    def test_unsafe_paths(self):
        for name in ['/absolute', '../secret', 'C:/secret', 'a\\b']:
            with self.assertRaises(ValueError): v.safe(name)

if __name__ == '__main__': unittest.main()
