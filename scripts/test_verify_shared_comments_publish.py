import json, shutil, tempfile, unittest
from pathlib import Path
import verify_shared_comments_publish as v
class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        m,_=v.contract();self.files=set(m['baselinePins'])|set(m['allowedChanges'])|{v.RECEIPT,v.INVERSE}
        for n in self.files:
            p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(v.ROOT/n,p)
    def tearDown(self):self.tmp.cleanup()
    def receipt(self,fn):
        p=self.root/v.RECEIPT;r=json.loads(p.read_bytes());fn(r);p.write_text(json.dumps(r),encoding='utf8')
    def test_valid(self):self.assertEqual(v.verify(self.root)['status'],'PASS_SHARED_REPLAY_COMMENTS_01')
    def test_authorization(self):
        self.receipt(lambda r:r.__setitem__('publicationAuthorized',False))
        with self.assertRaisesRegex(ValueError,'authorization'):v.verify(self.root)
    def test_scope(self):
        self.receipt(lambda r:r.__setitem__('scope','arbitrary-discussion'))
        with self.assertRaisesRegex(ValueError,'scope'):v.verify(self.root)
    def test_missing_pin(self):
        self.receipt(lambda r:r['sourcePins'].pop('src/App.tsx'))
        with self.assertRaisesRegex(ValueError,'pin scope'):v.verify(self.root)
    def test_research_unchanged(self):
        p=self.root/'src/data/historyReplayAggressiveHikesQt.json';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'immutable baseline'):v.verify(self.root)
    def test_worker_unchanged(self):
        p=self.root/'comments-worker/src/service.mjs';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'immutable baseline'):v.verify(self.root)
    def test_legacy_receipt_unchanged(self):
        p=self.root/'release/aggressive-publication-01.json';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'immutable baseline'):v.verify(self.root)
    def test_extra_public_file(self):
        (self.root/'public/private.txt').write_text('private')
        with self.assertRaisesRegex(ValueError,'unapproved'):v.verify(self.root)
    def test_inverse_tampering(self):
        p=self.root/v.INVERSE;p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'inverse binding'):v.verify(self.root)
    def test_unsafe_paths(self):
        for n in ['/absolute','../secret','C:/secret','a\\b']:
            with self.assertRaises(ValueError):v.safe(n)
if __name__=='__main__':unittest.main()
