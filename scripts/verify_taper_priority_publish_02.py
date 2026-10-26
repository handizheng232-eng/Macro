"""Scoped partial Taper release; immutable prior chain via exact inverse blocks."""
import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from verify_taper_priority_publish import verify as verify_pandemic, RECEIPT as PREVIOUS
from verify_renewed_easing_publish import require
ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'release/taper-priority-publication-02.json'
AUTH = 'release/taper-priority-authorization-02.json'
INVERSE = 'release/taper-priority-inverse-02.json'
AUTH_SHA = '8dce4783116ae2c8f54302068d68507fa9cce6e68a43eeab8ed69124f254783f'
CANDIDATE_SHA = '878356b97ab16d51615bfaddc692f9c4be3d5acd4e37c8998d837ebfd697d3c4'
DATA = 'src/data/historyReplayTaper.json'
def sha(b): return hashlib.sha256(b).hexdigest()
def digest(d): return sha(json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
def safe(n):
    p=Path(n)
    require(not p.is_absolute() and '..' not in p.parts and ':' not in n and '\\' not in n, 'unsafe path')
    return p

def authorization(root):
    raw=(root/AUTH).read_bytes()
    require(sha(raw)==AUTH_SHA, 'authorization external anchor differs')
    a=json.loads(raw)
    require(a['publicationAuthorized'] is True and a['fullStageReady'] is False and a['candidateSHA256']==CANDIDATE_SHA, 'authorization scope differs')
    return a

def restore(name,root):
    a=authorization(root); inv=json.loads((root/INVERSE).read_bytes())
    require(sha((root/INVERSE).read_bytes())==a['inverseSHA256'], 'inverse contract differs')
    require(set(inv)==set(a['replacedExistingFiles']), 'inverse scope differs')
    r=inv[name]; raw=(root/name).read_bytes()
    require(sha(raw)==r['currentSHA256'], 'inverse input differs')
    lines=raw.decode().splitlines(keepends=True); end=0
    for op in r['operations']:
        require(0<=end<=op['start']<=op['end']<=len(lines), 'inverse span differs')
        require(sha(''.join(lines[op['start']:op['end']]).encode())==op['currentSHA256'], 'inverse block differs')
        end=op['end']
    for op in reversed(r['operations']): lines[op['start']:op['end']]=[op['baselineText']]
    raw=''.join(lines).encode()
    require(sha(raw)==r['baselineSHA256']==a['baselinePins'][name], 'inverse baseline differs')
    return raw

@contextmanager
def previous_root(root=ROOT):
    a=authorization(root)
    with tempfile.TemporaryDirectory(prefix='taper-priority-prior-') as folder:
        target=Path(folder)
        for name, expected in a['baselinePins'].items():
            p=target/safe(name); p.parent.mkdir(parents=True,exist_ok=True)
            raw=restore(name,root) if name in a['replacedExistingFiles'] else (root/name).read_bytes()
            require(sha(raw)==expected, 'immutable baseline changed: '+name)
            p.write_bytes(raw)
        yield target

def verify_assets(dist,receipt,root):
    require(dist.is_dir(), 'dist missing')
    actual={p.relative_to(dist).as_posix() for p in dist.rglob('*') if p.is_file()}
    require(actual==set(receipt['distPins']), 'asset scope differs')
    for n,h in receipt['distPins'].items():
        raw=(dist/safe(n)).read_bytes()
        # HTML follows explicit LF text contract; deployed readback is raw CI bytes.
        require(sha(raw.replace(b'\r\n',b'\n') if n=='index.html' else raw)==h, 'asset bytes differ: '+n)
        require(Path(n).suffix in ('.js','.css','.html','.svg'), 'private filetype')
        require(not re.search(r'(?<![A-Za-z0-9])[A-Z]:[\\/]|unicodeStart|rawLiteral|rawHorizon|typedSupport',raw.decode()), 'private path/support in dist')
    html=(dist/'index.html').read_text(encoding='utf-8')
    linked={n.removeprefix('/Macro/') for n in re.findall(r'(?:src|href)="(/Macro/assets/[^"]+)"',html)}
    require(linked=={n for n in actual if n.startswith('assets/')}, 'HTML asset set differs')
    for n in actual:
        if n.startswith('taper-charts/'):
            require((dist/n).read_bytes()==(root/'public'/n).read_bytes(), 'chart source bytes differ')
    return len(actual)

def verify(receipt,root=ROOT,dist=None):
    a=authorization(root)
    require(receipt.get('schemaVersion')=='taper-priority-publication-02' and receipt.get('publicationAuthorized') is True, 'publication authorization absent')
    require(receipt.get('fullStageReady') is False and receipt.get('scope')==a['scope'], 'research scope upgraded')
    require(receipt.get('authorizationSHA256')==AUTH_SHA, 'authorization binding differs')
    names=set(a['baselinePins'])|set(a['allowedChanges'])
    require(set(receipt['publicFilePins'])==names, 'pin coverage differs')
    for n,h in receipt['publicFilePins'].items():require(sha((root/safe(n)).read_bytes())==h, 'public file changed: '+n)
    for n,h in a['approvedChangedPins'].items():require(sha((root/n).read_bytes())==h, 'approved change differs: '+n)
    require(sha((root/PREVIOUS).read_bytes())==a['previousReceiptSHA256'], 'previous receipt changed')
    raw=(root/DATA).read_bytes();d=json.loads(raw)
    require(sha(raw)==a['publishedSHA256'], 'approved payload differs')
    restored=raw
    for c in reversed(a['metadataChanges']):
        old=json.dumps(c['old'],ensure_ascii=False).encode();new=json.dumps(c['new'],ensure_ascii=False).encode()
        require(restored.count(new)==1, 'metadata replacement differs');restored=restored.replace(new,old)
    require(sha(restored)==CANDIDATE_SHA, 'economic content differs from reviewed candidate')
    pc=d['priorityCoverage']
    require(pc['fullStageReady'] is False and pc['publishAuthorized'] is False and pc['formalQuotaQualifiedCount'] is None, 'research inner state upgraded')
    require(d['localReview']['fullStageReady'] is False and d['candidateMetadata']['publicReleaseAllowed'] is False, 'historical contract rewritten')
    require((pc['originalAcquired'],pc['originalUsed'],pc['repostUsed'])==(63,60,2), 'coverage differs')
    require([m['originalAcquired'] for m in pc['monthly']]==[15,22,16,10] and all(m['quotaAccepted'] is False for m in pc['monthly']), 'monthly admission upgraded')
    require(digest(d)==a['publishedObjectDigest'], 'complete candidate object differs')
    with previous_root(root) as prev:result=verify_pandemic(json.loads((prev/PREVIOUS).read_bytes()),root=prev)
    if dist is not None:result['distFilesScanned']=verify_assets(dist,receipt,root)
    result.update(status='PASS_AUTHORIZED_PARTIAL_TAPER_PRIORITY_02',fullStageReady=False,publicationAuthorized=True,candidateSHA256=CANDIDATE_SHA,rawOriginalReadbackPerformed=False)
    return result

def legacy_tests(root=ROOT):
    with previous_root(root) as prev:
        subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','scripts','-p','test_verify_taper_priority_publish.py','-v'],cwd=prev,check=True)
        subprocess.run([sys.executable,'-B','scripts/verify_taper_priority_publish.py','--legacy-tests'],cwd=prev,check=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--dist',type=Path);p.add_argument('--legacy-tests',action='store_true');args=p.parse_args()
    try:
        result=verify(json.loads((ROOT/RECEIPT).read_bytes()),dist=args.dist)
        if args.legacy_tests:legacy_tests()
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,KeyError,OSError,TypeError,subprocess.CalledProcessError) as e:
        print(json.dumps({'status':'INVALID_PARTIAL_TAPER_PRIORITY','reason':str(e)},ensure_ascii=False));return 2
if __name__=='__main__':raise SystemExit(main())
