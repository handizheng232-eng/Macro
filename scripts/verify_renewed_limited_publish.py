"""Versioned public-only gate for limited renewed-easing research release 03.
The original publication-1 verifier and receipt remain immutable contracts.
This verifies approved public bytes, references, quantity exception and bounds;
it does not claim public CI can read private originals or certify economic truth.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from verify_renewed_easing_publish import require, public_privacy, check_dist
ROOT = Path(__file__).resolve().parents[1]

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def verify(data, raw, receipt):
    require(receipt.get('schemaVersion')=='renewed-easing-limited-publication-03','wrong release contract')
    require(receipt.get('publicationAuthorized') is True and receipt.get('pageQAComplete') is True and receipt.get('fullStageReady') is False,'limited publication authorization/QA absent or scope upgraded')
    require(receipt.get('datasetSHA256')==hashlib.sha256(raw).hexdigest(),'approved payload bytes differ')
    require(json.loads(raw)==data,'decoded payload differs')
    require((data['title'],data['startDate'],data['endDate'],data['asOf'])==('再降息与QT收官','2025-09-01','2025-12-31','2025-12-31'),'stage boundary changed')
    state=data['experimentStatus']
    require(state['status']=='authorized-limited-research-publication-03' and state['publication'] is True and state['fullStageReady'] is False,'page publication status differs')
    for key,value in {'wechatAcceptedTotal':23,'libraryReviewedCandidateCount':4,'wechatLocalUsedCount':4,'wechatLocalNotUsedCount':0,'wechatPendingAnalysis':0,'windAcceptedTotal':59,'windRequiredPerMonth':15,'windQuantityException':True}.items():
        require(state.get(key)==value,'research count/scope differs: '+key)
    sections=data['marketAnalysis']['sections']
    nodes=[n for s in sections for ns in s['deepDive'].values() for n in ns]
    views=[v for key in ('researchEvidence','windResearchEvidence','wechatResearchEvidence') for v in data[key]]
    require(len(sections)==5 and len(nodes)==len({n['id'] for n in nodes})==240,'topic/node identity mismatch')
    require(len(views)==len({v['id'] for v in views})==88,'opinion identity mismatch')
    require(sum('periodSummary' in s for s in sections)==5 and sum(len(s['aspectSummaries']) for s in sections)==35,'summary structure mismatch')
    require(sum(len(s['frameworkEvidence']) for s in sections)==26 and sum(len(c['series']) for s in sections for c in s['frameworkEvidence'])==48,'framework scope differs')
    sm={s['id']:s for s in data['sources']};rm={r['id']:r for r in data['reports']}
    require(len(sm)==len(data['sources'])==228 and len(rm)==len(data['reports'])==167,'bibliography identity mismatch')
    require(all(r['sourceId'] in sm for r in rm.values()),'unregistered report source')
    for n in nodes:
        require(n['historicalAsOfEligible'] is False and n.get('firstAvailableDate') is None,'historical node upgrade')
        require(set(n['sourceIds'])<=sm.keys() and set(n['reportIds'])<=rm.keys(),'unregistered node support')
        if n['id']!='local02-cme-gap':require(bool(n['evidenceRefs']),'missing evidence references')
        require({r['id'] for r in n.get('supportingEvidence',[])}<=set(n['evidenceRefs']),'locator/evidence mismatch')
    for v in views:
        require(v['reportId'] in rm and v['firstAvailableDate'] is None and v['historicalAsOfEligible'] is False,'opinion support/history mismatch')
    for s in sections:
        local={n['id']:n for ns in s['deepDive'].values() for n in ns}
        for summary, allowed in [(s['periodSummary'],local)]+[(s['aspectSummaries'][role],{n['id']:n for n in ns}) for role,ns in s['deepDive'].items()]:
            require(bool(summary['evidenceRefs']) and set(summary['evidenceRefs'])<=allowed.keys(),'summary support mismatch')
            for field in ('sourceIds','reportIds'):
                require(set(summary[field])=={v for id in summary['evidenceRefs'] for v in allowed[id][field]},'summary closure differs')
        for role in ('expectationTimeline','realityTimeline','implicationTimeline'):
            dates=[n['date'] for n in s['deepDive'][role] if n['date']]
            require(dates==sorted(dates),'timeline order changed')
    new=[n for n in nodes if n['id'].startswith(('local02-WP','local03-'))]
    require(len(new)==7 and {n['id']:digest(n) for n in new}==receipt['approvedNodeDigests'],'full seven paragraphs/conditions/support differ')
    gap=next(n for n in nodes if n['id']=='local02-cme-gap')
    require(digest(gap)==receipt['cmeGapDigest'] and '未接入CME概率数据' in gap['text'],'CME gap suppressed or fabricated')
    require('旧中邮相关观点待单独复核' in json.dumps(data['marketAnalysis'],ensure_ascii=False),'old-source boundary suppressed')
    require(len(data['windIncrement'])==17 and digest(data['windIncrement'])==receipt['windIncrementDigest'],'17 accepted Wind paragraphs changed')
    require(digest(data['marketPaths'])==receipt['marketPathsDigest'],'market chart values changed')
    # Full baseline/current content binding is separate from the outer raw-file hash.
    require(digest(data['marketAnalysis'])==receipt['marketAnalysisDigest'],'research/summaries/framework changed')
    references=[r for r in rm.values() if r['id'].startswith('LR03-WX-')]
    require(len(references)==4 and all(r.get('parentAccepted') is False and r['firstAvailableDate'] is None and r['historicalAsOfEligible'] is False for r in references),'reference-only sources upgraded')
    rows=data['monthlyCoverage']['rows']
    require([r['month'] for r in rows]==['2025-09','2025-10','2025-11','2025-12'],'month set differs')
    expected={'知识星球':[20,20,20,21],'Wind':[15,15,15,14],'微信公众号':[5,6,6,6]}
    for i,row in enumerate(rows):
        require(set(row['channels'])==set(expected),'channel set differs')
        for channel,counts in expected.items():
            docs=[r for r in rm.values() if r['channel']==channel and r['date'][:7]==row['month'] and not r['id'].startswith('LR03-WX-')]
            cell=row['channels'][channel];count=counts[i]
            require(len(docs)==count==cell['bodyCount']==cell['verifiedBodyCount'],'actual accepted library count differs')
            require(cell['requiredCount']=={'知识星球':20,'Wind':15,'微信公众号':5}[channel],'default quota changed')
            require(cell['accepted'] is True and cell['quotaAccepted'] is True,'quantity acceptance absent')
            require(cell['searchExhaustive'] is False and cell['actualEligibleTotal'] is None,'quantity incorrectly upgraded to exhaustive')
            if channel=='Wind' and i==3:
                require(cell['defaultQuotaAccepted'] is False and cell['effectiveQuotaAccepted'] is True,'exception scope differs')
                require(cell['quantityException']=={'stage':'renewed-easing-qt-end','month':'2025-12','channel':'Wind','requiredCount':15,'acceptedCount':14,'acceptedByUser':True,'qualityReviewWaived':False},'quantity exception altered')
    require(data['monthlyCoverage']['acceptedCells']==12 and data['monthlyCoverage']['complete'] is False,'limited completeness changed')
    public_privacy(data)
    return {'status':'PASS_AUTHORIZED_LIMITED_RESEARCH_03','nodes':len(nodes),'newResearchParagraphs':len(new),'formalWechatLibrary':23,'additionalAnalyzedReferences':4,'windCounts':expected['Wind'],'fullStageReady':False,'rawOriginalReadbackPerformed':False}

def verify_files(receipt,root=ROOT):
    for relative,sha in receipt['publicFilePins'].items():
        path=Path(relative)
        require(not path.is_absolute() and '..' not in path.parts,'unsafe public pin path')
        require(hashlib.sha256((root/path).read_bytes()).hexdigest()==sha,'public component/other-stage changed: '+relative)

def verify_assets(directory, receipt):
    count=check_dist(directory)
    pins=receipt['distAssetPins']
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    require(actual==set(pins)|{'index.html'},'unreviewed or missing dist asset')
    for relative,sha in pins.items():
        require(hashlib.sha256((directory/relative).read_bytes()).hexdigest()==sha,'dist asset bytes differ: '+relative)
    html=(directory/'index.html').read_text(encoding='utf-8')
    linked={p.removeprefix('/Macro/') for p in re.findall(r'(?:src|href)="(/Macro/assets/[^"]+)"',html)}
    require(linked==set(pins),'HTML does not reference exactly the approved assets')
    return count

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dist',type=Path)
    a=p.parse_args()
    try:
        raw=(ROOT/'src/data/historyReplayRenewedEasingQtEnd.json').read_bytes()
        receipt=json.loads((ROOT/'release/replay-renewed-easing-publication-03.json').read_bytes())
        result=verify(json.loads(raw),raw,receipt);verify_files(receipt)
        if a.dist:result['distFilesScanned']=verify_assets(a.dist,receipt)
        print(json.dumps(result,ensure_ascii=False));return 0
    except (ValueError,KeyError,TypeError,OSError,StopIteration) as error:
        print(json.dumps({'status':'INVALID_LIMITED_PUBLICATION_03','reason':str(error)},ensure_ascii=False));return 2
if __name__=='__main__':raise SystemExit(main())
