"""Current release plus immutable predecessor: no private review dependency."""
import copy, json, shutil, tempfile, unittest
from pathlib import Path
import verify_policy_reality_publish as v

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        m,_=v.contract()
        for n in set(m['baselinePins'])|set(m['allowedChanges'])|{v.RECEIPT,v.INVERSE}:
            p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(v.ROOT/n,p)
    def tearDown(self):self.tmp.cleanup()
    def receipt(self, fn):
        p=self.root/v.RECEIPT;r=json.loads(p.read_bytes());fn(r);p.write_text(json.dumps(r),encoding='utf8')
    def test_valid(self):self.assertEqual(v.verify(self.root)['status'],'PASS_POLICY_REALITY_01')
    def test_authorization(self):
        self.receipt(lambda r:r.__setitem__('publicationAuthorized',False))
        with self.assertRaisesRegex(ValueError,'authorization'):v.verify(self.root)
    def test_scope(self):
        self.receipt(lambda r:r.__setitem__('scope','other-stage'))
        with self.assertRaisesRegex(ValueError,'scope'):v.verify(self.root)
    def test_pin_scope(self):
        self.receipt(lambda r:r['sourcePins'].pop(v.DATA))
        with self.assertRaisesRegex(ValueError,'pin scope'):v.verify(self.root)
    def test_rehashed_unauthorized_mutations(self):
        p=self.root/v.DATA;original=p.read_bytes(); base=json.loads(original)
        mutations=[lambda d:d['marketAnalysis']['sections'][0]['deepDive']['realityTimeline'][0]['reviewedParagraphs'][0].__setitem__('text','altered'),lambda d:d['marketAnalysis']['sections'][0]['deepDive']['realityTimeline'][0]['reviewedParagraphs'][0].__setitem__('sourceIds',[]),lambda d:d['localReview'].__setitem__('fullStageReady',True),lambda d:d['localReview'].__setitem__('strictHistoricalEligible',True),lambda d:d['localReview'].__setitem__('publicReleaseAllowed',False),lambda d:d['marketAnalysis']['sections'][1].__setitem__('title','altered')]
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)):
                d=copy.deepcopy(base);mutate(d);p.write_text(json.dumps(d,ensure_ascii=False),encoding='utf8')
                self.receipt(lambda r:r['sourcePins'].__setitem__(v.DATA,v.sha(p.read_bytes())))
                with self.assertRaisesRegex(ValueError,'approved source|reviewed candidate|publication state'):v.verify(self.root)
        p.write_bytes(original)
    def test_legacy_receipts(self):
        p=self.root/'release/shared-comments-publication-01.json';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'immutable baseline'):v.verify(self.root)
    def test_worker_unchanged(self):
        p=self.root/'comments-worker/src/service.mjs';p.write_bytes(p.read_bytes()+b' ')
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
    def test_frozen_tests_preserve_all_assertions(self):
        _, originals=v.contract(self.root)
        for name in ['aggressiveReview','templateParity','reviewMissingDetails']:
            n='src/'+name+'.test.tsx'
            expected=originals[n].decode().replace("'./data/historyReplayAggressiveHikesQt.json'","'./data/policyRealityLegacy.fixture.json'")
            self.assertEqual((self.root/n).read_bytes().decode().replace('\r\n','\n'),expected.replace('\r\n','\n'))
if __name__=='__main__':unittest.main()
