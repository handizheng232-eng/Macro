"""Authorized monthly monetary-policy reality release; old contracts remain immutable."""
import argparse
from contextlib import contextmanager
import hashlib, io, json, os, re, subprocess, sys, tempfile, zipfile
from pathlib import Path
from verify_comments_publish import safe, public_commands
ROOT=Path(__file__).resolve().parents[1]
RECEIPT='release/policy-reality-publication-01.json'
INVERSE='release/snapshots/policy-reality-inverse-01.zip'
INVERSE_SHA='4611893eb0cf6be829e749f418140dbbac8b26ecddeb20d5c4b0cccb485ebc89'
DATA='src/data/historyReplayAggressiveHikesQt.json'
REVIEWED_SHA='32a2f9da9b13eb91e4e80a790c4e36a71373657da7eb7ebc7f9d38f747cc7bd1'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(ok,message):
    if not ok:raise ValueError(message)

def contract(root=ROOT):
    raw=(root/INVERSE).read_bytes();need(sha(raw)==INVERSE_SHA,'inverse binding differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist();need(len(names)==len(set(names)),'duplicate inverse members')
        for n in names:safe(n)
        m=json.loads(z.read('__manifest__.json'))
        need(set(names)=={'__manifest__.json'}|{'files/'+n for n in m['replaced']},'inverse scope')
        originals={n:z.read('files/'+n) for n in m['replaced']}
    return m,originals

def verify(root=ROOT,dist=None):
    m,originals=contract(root);r=json.loads((root/RECEIPT).read_bytes())
    need(r.get('publicationAuthorized') is True and r.get('scope')=='policy-reality-monthly-01','authorization/scope')
    need(r.get('historicalResearchAuthorizationExpanded') is False,'research authorization')
    need(r.get('inverseSHA256')==INVERSE_SHA,'receipt inverse')
    need(set(r['sourcePins'])==set(m['allowedChanges']),'source pin scope')
    for n,h in m['approvedPins'].items():need(sha((root/safe(n)).read_bytes())==h,'approved source differs: '+n)
    for n,h in r['sourcePins'].items():need(sha((root/safe(n)).read_bytes())==h,'source pin differs: '+n)
    for n,h in m['baselinePins'].items():
        raw=originals[n] if n in originals else (root/safe(n)).read_bytes()
        need(sha(raw)==h,'immutable baseline differs: '+n)
    expected=set(m['baselinePins'])|set(m['allowedChanges'])|{RECEIPT,INVERSE}
    for directory in ('src','scripts','docs','public','release','.github','comments-worker','buildPlugins'):
        for p in (root/directory).rglob('*'):
            if p.is_file() and not any(x in p.parts for x in ('node_modules','__pycache__','.wrangler')) and p.suffix!='.pyc':
                need(p.resolve().is_relative_to(root.resolve()) and p.relative_to(root).as_posix() in expected,'unapproved public file')
    raw=(root/DATA).read_bytes();d=json.loads(raw)
    for c in m['publicationProjection']:
        _,parent,key=c['path'].split('/')
        need(d[parent][key]==c['old'],'publication state differs')
        old=(json.dumps(key)+': '+json.dumps(c['old'],ensure_ascii=False)).encode()
        new=(json.dumps(key)+': '+json.dumps(c['new'],ensure_ascii=False)).encode()
        need(raw.count(old)==1,'publication state ambiguous');raw=raw.replace(old,new)
    need(sha(raw)==REVIEWED_SHA,'reviewed candidate differs')
    need(not d['localReview']['fullStageReady'] and not d['localReview']['strictHistoricalEligible'] and not d['reviewProjection']['fullStageReady'],'eligibility upgrade')
    months=d['marketAnalysis']['sections'][0]['deepDive']['realityTimeline']
    e=json.loads((root/'src/data/policyRealityExpected.fixture.json').read_bytes())
    need(months==e['months'] and len(months)==6,'monthly approved fixture differs')
    ps=[p for month in months for p in month['reviewedParagraphs']]
    need(len(ps)==35 and sum(len(p['sourceIds']) for p in ps)==54,'paragraph/citation count')
    for month in months:need('\n\n'.join(p['text'] for p in month['reviewedParagraphs'])==month['text'],'month text differs')
    need(len(d['sources'])==116,'bibliography count')
    workflow=(root/'.github/workflows/deploy.yml').read_text(encoding='utf8')
    need('VITE_CUSTOM_COMMENTS_ENABLED: "true"' in workflow and 'VITE_COMMENTS_API: https://macro-replay-comments.handizheng232.workers.dev' in workflow,'production flags')
    result={'status':'PASS_POLICY_REALITY_01','researchInverseBound':True,'reviewedCandidateSHA256':REVIEWED_SHA,'paragraphs':35,'citations':54,'bibliography':116}
    if dist is not None:
        files={p.relative_to(dist).as_posix():p for p in dist.rglob('*') if p.is_file()}
        need(set(files)==set(r['distPins']),'asset scope differs')
        for n,p in files.items():
            raw=p.read_bytes();need(sha(raw)==r['distPins'][n],'asset pin differs: '+n)
            need(p.suffix in ('.html','.js','.css','.svg'),'private asset type')
            need(not re.search(r'(?<![A-Za-z0-9])[A-Z]:[\\/]|unicodeStart|rawLiteral|rawHorizon|typedSupport',raw.decode()),'private support in dist')
            if p.suffix=='.svg':need(raw==(root/'public'/n).read_bytes(),'chart bytes differ')
        html=(dist/'index.html').read_text(encoding='utf8')
        linked={n.removeprefix('/Macro/') for n in re.findall(r'(?:src|href)="(/Macro/assets/[^"]+)"',html)}
        need(len(linked)==2 and linked<=set(files),'HTML asset coverage')
        assets={n for n in files if n.startswith('assets/')};lazy=assets-linked
        need(len(lazy)==1 and all(re.fullmatch(r'assets/giscus-[A-Za-z0-9_-]+\.js',n) for n in lazy),'lazy assets')
        js=b''.join(p.read_bytes() for p in dist.rglob('*.js'))
        need(b'https://macro-replay-comments.handizheng232.workers.dev' in js,'API missing')
        result['distFilesScanned']=len(files)
    return result

@contextmanager
def previous_root(root=ROOT):
    m,originals=contract(root)
    with tempfile.TemporaryDirectory(prefix='policy-reality-exact-shared-') as folder:
        target=Path(folder)
        for n,h in m['baselinePins'].items():
            raw=originals[n] if n in originals else (root/safe(n)).read_bytes()
            need(sha(raw)==h,'inverse baseline differs: '+n)
            dest=target/safe(n);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        yield target

def legacy(root=ROOT):
    with previous_root(root) as prior:
        source=(root/'node_modules').resolve();link=prior/'node_modules'
        if os.name=='nt':subprocess.run(['cmd','/c','mklink','/J',str(link),str(source)],check=True,stdout=subprocess.DEVNULL)
        else:link.symlink_to(source,target_is_directory=True)
        env=dict(os.environ,VITE_CUSTOM_COMMENTS_ENABLED='true',VITE_COMMENTS_API='https://macro-replay-comments.handizheng232.workers.dev')
        try:
            subprocess.run(['node',str(source/'vite/bin/vite.js'),'build'],cwd=prior,env=env,check=True)
            for cmd in public_commands((prior/'.github/workflows/deploy.yml').read_text()):
                if cmd[0]=='python':cmd[0]=sys.executable
                print('INHERITED COMMAND '+json.dumps(cmd),flush=True);subprocess.run(cmd,cwd=prior,check=True)
        finally:
            if os.name=='nt':os.rmdir(link)
            else:link.unlink()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dist',type=Path);p.add_argument('--legacy-tests',action='store_true');a=p.parse_args()
    result=verify(dist=a.dist)
    if a.legacy_tests:legacy();result['completePredecessorGateReplayed']=True
    print(json.dumps(result))
