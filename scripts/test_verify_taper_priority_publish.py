import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from verify_taper_priority_publish import ROOT, RECEIPT, AUTH, PREVIOUS, DATA, sha, verify, verify_assets

class TaperPriorityPublicationTests(unittest.TestCase):
    def setUp(self):self.r=json.loads((ROOT/RECEIPT).read_bytes())
    def test_authorized_partial_chain(self):
        result=verify(self.r)
        self.assertTrue(result['legacyGateReplayed'])
        self.assertFalse(result['fullStageReady'])
        self.assertTrue(result['publicationAuthorized'])
    def test_authorization_scope_and_pin_set(self):
        for field,value in [('publicationAuthorized',False),('fullStageReady',True),('scope','all-research'),('authorizationSHA256','0'*64)]:
            r=copy.deepcopy(self.r);r[field]=value
            with self.assertRaises(ValueError,msg=field):verify(r)
        for extra in [False,True]:
            r=copy.deepcopy(self.r)
            if extra:r['publicFilePins']['../private']='0'*64
            else:del r['publicFilePins'][DATA]
            with self.assertRaises(ValueError):verify(r)
    def test_rehashed_semantic_and_legacy_mutations_rejected(self):
        with tempfile.TemporaryDirectory(prefix='taper-negative-') as folder:
            root=Path(folder)
            for n in set(self.r['publicFilePins'])|{RECEIPT}:
                p=root/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,p)
            d=json.loads((root/DATA).read_bytes())
            cases=[]
            for name in ['conditions','references','historical','coverage','research-completion']:
                x=copy.deepcopy(d)
                if name=='conditions':x['marketAnalysis']['sections'][0]['deepDive']['expectationTimeline'][0]['text']='deleted condition'
                if name=='references':x['sources'][0]['url']='https://example.org/'
                if name=='historical':x['localReview']['strictHistoricalEligible']=True
                if name=='coverage':x['priorityCoverage']['monthly'][0]['quotaAccepted']=True
                if name=='research-completion':x['localReview']['fullStageReady']=True
                cases.append((DATA,json.dumps(x,ensure_ascii=False).encode()))
            for n in ['src/App.tsx','src/historyReplay.tsx','src/data/historyReplayRenewedEasingQtEnd.json',PREVIOUS,AUTH]:cases.append((n,(root/n).read_bytes()+b'\n '))
            for n,raw in cases:
                original=(root/n).read_bytes();(root/n).write_bytes(raw);r=copy.deepcopy(self.r);r['publicFilePins'][n]=sha(raw)
                with self.assertRaises(ValueError,msg=n):verify(r,root=root)
                (root/n).write_bytes(original)
    def test_asset_removal_and_replacement(self):
        with tempfile.TemporaryDirectory(prefix='taper-assets-') as folder:
            dist=Path(folder)
            with self.assertRaises(ValueError):verify_assets(dist,self.r,ROOT)
            for n in self.r['distPins']:
                p=dist/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'bad')
            with self.assertRaises(ValueError):verify_assets(dist,self.r,ROOT)
if __name__=='__main__':unittest.main()
