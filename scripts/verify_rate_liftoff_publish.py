"""Explicitly authorized partial release; no private research runtime dependencies."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from verify_taper_priority_publish_02 import verify as previous_verify, verify_assets as previous_assets, RECEIPT as PREVIOUS
from verify_renewed_easing_publish import require
ROOT=Path(__file__).resolve().parents[1]
RECEIPT='release/rate-liftoff-publication-01.json'
AUTH='release/rate-liftoff-authorization-01.json'
INVERSE='release/rate-liftoff-inverse-01.json'
AUTH_SHA='2f3bb1dd7d28fb36e62736ee3b50618a03e267362e6c2ed34fbacf791ba4bab7'
CANDIDATE_SHA='696ad1ba35f56f19cc415fcb5efe6916ad9468bb106eb375abf9d11a98f4b656'
DATA='src/data/historyReplayRateLiftoffQtGuidance.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def safe(n):
 p=Path(n)
 require(not p.is_absolute() and '..' not in p.parts and ':' not in n and '\\' not in n,'unsafe path')
 return p
def authorization(root):
 raw=(root/AUTH).read_bytes()
 require(sha(raw)==AUTH_SHA,'authorization external anchor differs')
 a=json.loads(raw)
 require(a['publicationAuthorized'] is True and a['fullStageReady'] is False and a['candidateSHA256']==CANDIDATE_SHA,'authorization scope differs')
 return a
def restore(name,root,a):
 raw=(root/INVERSE).read_bytes();require(sha(raw)==a['inverseSHA256'],'inverse contract differs');inv=json.loads(raw)
 require(set(inv)==set(a['replacedExistingFiles']),'inverse scope differs')
 r=inv[name];raw=(root/name).read_bytes();require(sha(raw)==r['currentSHA256'],'inverse input differs')
 lines=raw.decode().splitlines(keepends=True);end=0
 for op in r['operations']:
  require(0<=end<=op['start']<=op['end']<=len(lines),'inverse span differs')
  require(sha(''.join(lines[op['start']:op['end']]).encode())==op['currentSHA256'],'inverse block differs');end=op['end']
 for op in reversed(r['operations']):lines[op['start']:op['end']]=[op['baselineText']]
 raw=''.join(lines).encode();require(sha(raw)==r['baselineSHA256']==a['baselinePins'][name],'inverse baseline differs');return raw
@contextmanager
def previous_root(root=ROOT):
 a=authorization(root)
 with tempfile.TemporaryDirectory(prefix='rate-prior-public-') as folder:
  target=Path(folder)
  for n,h in a['baselinePins'].items():
   raw=restore(n,root,a) if n in a['replacedExistingFiles'] else (root/safe(n)).read_bytes()
   require(sha(raw)==h,'immutable baseline changed: '+n)
   p=target/safe(n);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  yield target

def check_semantics(d,a):
 require((d['title'],d['startDate'],d['endDate'])==('加息启动与缩表定调','2022-03-16','2022-05-31'),'stage months differ')
 lr=d['localReview']
 require(all(lr[k] is False for k in ['fullStageReady','publicReleaseAllowed','strictHistoricalEligible']),'research inner state upgraded')
 require([m['month'] for m in lr['coverage']]==['2022-03','2022-04','2022-05'],'coverage months differ')
 require(lr['coverage']==a['reviewedCoverage'],'quota or source coverage changed')
 require([s['id'] for s in d['sources']]==a['sourceIds'] and [r['id'] for r in d['reports']]==a['reportIds'],'held/unapproved source admitted')
 def walk(x):
  if isinstance(x,dict):
   for k,v in x.items():
    if k in ['historicalAsOfEligible','strictHistoricalEligible','fullStageReady','parentAccepted']:require(v is False,'strict or parent eligibility upgraded')
    if k in ['firstAvailableDate','availableFrom']:require(v is None,'unknown availability manufactured')
    walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(d)
 text=json.dumps(d,ensure_ascii=False)
 require(not re.search(r'(?<![A-Za-z0-9])[A-Z]:[\\/]|file://|unicodeStart|rawLiteral|rawHorizon|typedSupport|completeOriginalSupport',text),'private source content')
 require(len(d['marketPaths']['approvedCharts'])==6,'chart count differs')
 for pin in a['publicTextPins']:
  ptr=pin['pointer']
  if '#paragraph/' in ptr:value=d['marketAnalysis']['conclusion'].split('\n\n')[int(ptr.split('/')[-1])]
  else:
   value=d
   for k in ptr[1:].split('/'):value=value[int(k)] if isinstance(value,list) else value[k]
  require(sha(value.encode())==pin['sha256'],'reviewed economic projection differs: '+pin['id'])

def reviewed_inverse(raw,a):
 for c in reversed(a['metadataChanges']):
  old=json.dumps(c['old'],ensure_ascii=False).encode();new=json.dumps(c['new'],ensure_ascii=False).encode()
  require(raw.count(new)==1,'publication metadata differs');raw=raw.replace(new,old)
 require(sha(raw)==CANDIDATE_SHA,'economic content differs from reviewed raw candidate')
 return raw

def verify_assets(dist,receipt,root):
 # Preserve predecessor's complete type, privacy and HTML/asset checks.
 count=previous_assets(dist,receipt,root)
 charts={n for n in receipt['distPins'] if n.startswith('replay-rate-liftoff/')}
 require(charts=={'replay-rate-liftoff/'+s for s in ['01-nominal.svg','02-real-bei.svg','03-spreads.svg','04-dollar.svg','05-bei.svg','06-event-window.svg']},'six chart set differs')
 a=authorization(root)
 for n in charts:
  raw=(dist/safe(n)).read_bytes()
  require(raw==(root/'public'/n).read_bytes() and sha(raw)==a['approvedChangedPins']['public/'+n],'approved SVG changed')
 return count

def verify(receipt,root=ROOT,dist=None):
 a=authorization(root)
 require(receipt.get('schemaVersion')=='rate-liftoff-publication-01' and receipt.get('publicationAuthorized') is True,'publication authorization absent')
 require(receipt.get('scope')==a['scope'] and receipt.get('fullStageReady') is False,'release scope changed')
 require(receipt.get('authorizationSHA256')==AUTH_SHA,'authorization binding differs')
 # Semantic guard runs BEFORE outer hashes; negative tests rehash mutations.
 raw=(root/DATA).read_bytes();check_semantics(json.loads(raw),a);reviewed_inverse(raw,a)
 names=set(a['baselinePins'])|set(a['allowedChanges'])
 require(set(receipt['publicFilePins'])==names,'pin coverage differs')
 for n,h in receipt['publicFilePins'].items():require(sha((root/safe(n)).read_bytes())==h,'public file changed: '+n)
 for n,h in a['approvedChangedPins'].items():require(sha((root/safe(n)).read_bytes())==h,'approved change differs: '+n)
 require(sha((root/PREVIOUS).read_bytes())==a['previousReceiptSHA256'],'previous receipt changed')
 with previous_root(root) as prior:previous_result=previous_verify(json.loads((prior/PREVIOUS).read_bytes()),root=prior)
 result={'previousGate':previous_result,'legacyGateReplayed':True,'nodes':203,'publicTextProjections':283,'deepNodes':142,'monthlySummaryMirrors':15}
 if dist is not None:result['distFilesScanned']=verify_assets(dist,receipt,root)
 result.update(status='PASS_AUTHORIZED_PARTIAL_RATE_LIFTOFF_01',fullStageReady=False,publicationAuthorized=True,reviewedCandidateSHA256=CANDIDATE_SHA,publishedSHA256=sha(raw),rawOriginalReadbackPerformed=False)
 return result

def legacy_tests(root=ROOT):
 with previous_root(root) as prior:
  subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','scripts','-p','test_verify_taper_priority_publish_02.py','-v'],cwd=prior,check=True)
  subprocess.run([sys.executable,'-B','scripts/verify_taper_priority_publish_02.py','--legacy-tests'],cwd=prior,check=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--dist',type=Path);p.add_argument('--legacy-tests',action='store_true');args=p.parse_args()
 try:
  result=verify(json.loads((ROOT/RECEIPT).read_bytes()),dist=args.dist)
  if args.legacy_tests:legacy_tests()
  print(json.dumps(result,ensure_ascii=False));return 0
 except (ValueError,KeyError,OSError,TypeError,subprocess.CalledProcessError) as e:
  print(json.dumps({'status':'INVALID_PARTIAL_RATE_LIFTOFF','reason':str(e)},ensure_ascii=False));return 2
if __name__=='__main__':raise SystemExit(main())
