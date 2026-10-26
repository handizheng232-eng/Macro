import copy,json,shutil,tempfile,unittest
from pathlib import Path
from verify_rate_liftoff_publish import ROOT,RECEIPT,AUTH,PREVIOUS,DATA,sha,verify,verify_assets
class PublicationTests(unittest.TestCase):
 def setUp(self):self.r=json.loads((ROOT/RECEIPT).read_bytes())
 def test_authorized_complete_inherited_chain(self):
  r=verify(self.r);self.assertTrue(r['legacyGateReplayed']);self.assertFalse(r['fullStageReady']);self.assertTrue(r['publicationAuthorized'])
 def test_absent_authorization_scope_missing_and_extra_pins(self):
  for k,v in [('publicationAuthorized',False),('scope','all-history'),('fullStageReady',True),('authorizationSHA256','0'*64)]:
   r=copy.deepcopy(self.r);r[k]=v
   with self.assertRaises(ValueError):verify(r)
  for extra in [True,False]:
   r=copy.deepcopy(self.r)
   if extra:r['publicFilePins']['../private']='0'*64
   else:del r['publicFilePins'][DATA]
   with self.assertRaises(ValueError):verify(r)
 def test_rehashed_semantic_out_of_scope_and_old_pin_mutations(self):
  with tempfile.TemporaryDirectory(prefix='rate-negative-public-') as folder:
   root=Path(folder)
   for n in set(self.r['publicFilePins'])|{RECEIPT}:
    p=root/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,p)
   d=json.loads((root/DATA).read_bytes())
   for case in ['strict','completion','availability','held','months','privacy','text','quota']:
    x=copy.deepcopy(d)
    if case=='strict':x['sources'][0]['historicalAsOfEligible']=True
    if case=='completion':x['localReview']['fullStageReady']=True
    if case=='availability':x['sources'][0]['firstAvailableDate']='2022-03-16'
    if case=='held':x['sources'].append({**x['sources'][0],'id':'held-unapproved-source'})
    if case=='months':x['localReview']['coverage'][0]['month']='2021-12'
    if case=='privacy':x['sources'][0]['note']='E:/HermesData/private/report.pdf'
    if case=='text':x['marketAnalysis']['sections'][0]['periodSummary']['paragraphs'][0]='deleted necessary conditions'
    if case=='quota':x['localReview']['coverage'][0]['wind']['target']=0
    raw=json.dumps(x,ensure_ascii=False).encode();original=(root/DATA).read_bytes();(root/DATA).write_bytes(raw)
    r=copy.deepcopy(self.r);r['publicFilePins'][DATA]=sha(raw);r['sourceSHA256']=sha(raw)
    with self.assertRaisesRegex(ValueError,'upgraded|manufactured|unapproved|months|private|projection|coverage',msg=case):verify(r,root)
    (root/DATA).write_bytes(original)
   for n in ['src/App.tsx','src/historyReplay.tsx','src/data/historyReplayRenewedEasingQtEnd.json',PREVIOUS,AUTH]:
    original=(root/n).read_bytes();raw=original+b'\n ';(root/n).write_bytes(raw);r=copy.deepcopy(self.r);r['publicFilePins'][n]=sha(raw)
    with self.assertRaises(ValueError,msg=n):verify(r,root)
    (root/n).write_bytes(original)
 def test_all_six_rehashed_svg_changes_and_private_dist(self):
  with tempfile.TemporaryDirectory(prefix='rate-assets-public-') as folder:
   dist=Path(folder)
   for n in self.r['distPins']:
    p=dist/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'dist'/n,p)
   for n in sorted(self.r['distPins']):
    if not n.startswith('replay-rate-liftoff/'):continue
    original=(dist/n).read_bytes();raw=original+b'<!-- changed -->';(dist/n).write_bytes(raw);r=copy.deepcopy(self.r);r['distPins'][n]=sha(raw)
    with self.assertRaisesRegex(ValueError,'SVG'):verify_assets(dist,r,ROOT)
    (dist/n).write_bytes(original)
   n=next(n for n in self.r['distPins'] if n.endswith('.js'));raw=(dist/n).read_bytes()+b' E:/private/report.pdf';(dist/n).write_bytes(raw);r=copy.deepcopy(self.r);r['distPins'][n]=sha(raw)
   with self.assertRaisesRegex(ValueError,'private'):verify_assets(dist,r,ROOT)
if __name__=='__main__':unittest.main()
