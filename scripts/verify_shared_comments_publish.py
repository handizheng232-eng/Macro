"""Shared replay comments successor; replay all immutable predecessor gates."""
import argparse
from contextlib import contextmanager
import hashlib, io, json, os, re, subprocess, sys, tempfile, zipfile
from pathlib import Path
from verify_comments_publish import safe, public_commands
ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'release/shared-comments-publication-01.json'
INVERSE = 'release/snapshots/shared-comments-inverse-01.zip'
INVERSE_SHA = '924dc70d4d4cad73062a67cc3e12f9b9ad460f17f4aa6b795d0093629d209177'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def need(ok, message):
    if not ok: raise ValueError(message)
def contract(root=ROOT):
    raw = (root / INVERSE).read_bytes()
    need(sha(raw) == INVERSE_SHA, 'inverse binding differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        need(len(names) == len(set(names)), 'duplicate inverse members')
        for n in names: safe(n)
        m = json.loads(z.read('__manifest__.json'))
        need(set(names) == {'__manifest__.json'} | {'files/'+n for n in m['replaced']}, 'inverse scope')
        originals = {n:z.read('files/'+n) for n in m['replaced']}
    return m, originals
def verify(root=ROOT, dist=None):
    m, originals = contract(root)
    r = json.loads((root / RECEIPT).read_bytes())
    need(r.get('publicationAuthorized') is True and r.get('scope') == 'shared-replay-discussion-1', 'authorization/scope')
    need(r.get('historicalResearchAuthorizationExpanded') is False, 'research authorization')
    need(r.get('inverseSHA256') == INVERSE_SHA, 'receipt inverse')
    need(set(r['sourcePins']) == set(m['allowedChanges']), 'source pin scope')
    for n,h in r['sourcePins'].items(): need(sha((root/safe(n)).read_bytes()) == h, 'source pin differs: '+n)
    for n,h in m['baselinePins'].items():
        raw = originals[n] if n in originals else (root/safe(n)).read_bytes()
        need(sha(raw) == h, 'immutable baseline differs: '+n)
    expected=set(m['baselinePins']) | set(m['allowedChanges']) | {RECEIPT,INVERSE}
    for directory in ('src','scripts','docs','public','release','.github','comments-worker','buildPlugins'):
        for p in (root/directory).rglob('*'):
            if p.is_file() and not any(x in p.parts for x in ('node_modules','__pycache__','.wrangler')) and p.suffix != '.pyc':
                need(p.relative_to(root).as_posix() in expected, 'unapproved public file')
    ui=(root/'src/replayComments.tsx').read_text(encoding='utf8')
    need('UnboundCommentsPanel' not in ui and '复盘公共讨论' in ui and 'REPLAY_ROUTES.has(route)' in ui, 'shared channel contract')
    workflow=(root/'.github/workflows/deploy.yml').read_text(encoding='utf8')
    need('VITE_CUSTOM_COMMENTS_ENABLED: "true"' in workflow and 'VITE_COMMENTS_API: https://macro-replay-comments.handizheng232.workers.dev' in workflow, 'production flags')
    result={'status':'PASS_SHARED_REPLAY_COMMENTS_01','backendUnchanged':True,'researchUnchanged':True}
    if dist is not None:
        files={p.relative_to(dist).as_posix():p for p in dist.rglob('*') if p.is_file()}
        need(set(files)==set(r['distPins']), 'asset scope differs')
        for n,p in files.items():
            raw=p.read_bytes()
            need(sha(raw)==r['distPins'][n], 'asset pin differs: '+n)
            need(p.suffix in ('.html','.js','.css','.svg'), 'private asset type')
            need(not re.search(r'(?<![A-Za-z0-9])[A-Z]:[\\/]|unicodeStart|rawLiteral|rawHorizon|typedSupport',raw.decode()), 'private support in dist')
            if p.suffix=='.svg': need(raw==(root/'public'/n).read_bytes(), 'chart bytes differ')
        html=(dist/'index.html').read_text(encoding='utf8')
        linked={n.removeprefix('/Macro/') for n in re.findall(r'(?:src|href)="(/Macro/assets/[^"]+)"',html)}
        need(len(linked)==2 and linked<=set(files), 'HTML asset coverage')
        need(b'https://macro-replay-comments.handizheng232.workers.dev' in b''.join(p.read_bytes() for p in dist.rglob('*.js')), 'API missing')
        result['distFilesScanned']=len(files)
    return result
@contextmanager
def previous_root(root=ROOT):
    m,originals=contract(root)
    with tempfile.TemporaryDirectory(prefix='shared-exact-rr04-') as folder:
        target=Path(folder)
        for n,h in m['baselinePins'].items():
            raw=originals[n] if n in originals else (root/safe(n)).read_bytes()
            need(sha(raw)==h, 'inverse baseline differs: '+n)
            dest=target/safe(n);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        yield target
def legacy(root=ROOT):
    with previous_root(root) as prior:
        source=(root/'node_modules').resolve();link=prior/'node_modules'
        if os.name=='nt': subprocess.run(['cmd','/c','mklink','/J',str(link),str(source)],check=True,stdout=subprocess.DEVNULL)
        else: link.symlink_to(source,target_is_directory=True)
        env=dict(os.environ,VITE_CUSTOM_COMMENTS_ENABLED='true',VITE_COMMENTS_API='https://macro-replay-comments.handizheng232.workers.dev')
        try:
            subprocess.run(['node',str(source/'vite/bin/vite.js'),'build'],cwd=prior,env=env,check=True)
            for cmd in public_commands((prior/'.github/workflows/deploy.yml').read_text()):
                if cmd[0]=='python':cmd[0]=sys.executable
                print('INHERITED COMMAND '+json.dumps(cmd),flush=True)
                subprocess.run(cmd,cwd=prior,check=True)
        finally:
            if os.name=='nt':os.rmdir(link)
            else:link.unlink()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dist',type=Path);p.add_argument('--legacy-tests',action='store_true');a=p.parse_args()
    result=verify(dist=a.dist)
    if a.legacy_tests:legacy();result['completePredecessorGateReplayed']=True
    print(json.dumps(result))
