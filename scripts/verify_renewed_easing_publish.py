"""Read-only public publication gate for the separately approved third stage.
Reuses the accepted DTO invariants; never imports private archives or writes receipts.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SLUG = 'renewed-easing-qt-end'
H = lambda raw: hashlib.sha256(raw).hexdigest()

def require(ok,message):
    if not ok:raise ValueError(message)

def public_stats(data):
    require((data['title'],data['startDate'],data['endDate'],data['asOf'])==('再降息与QT收官','2025-09-01','2025-12-31','2025-12-31'),'third explicit stage boundary mismatch')
    sections=data['marketAnalysis']['sections']
    entries=[e for s in sections for es in s['deepDive'].values() for e in es]
    views=[o for k in ('researchEvidence','windResearchEvidence','wechatResearchEvidence') for o in data[k]]
    cards=[c for s in sections for c in s['frameworkEvidence']]
    stats={'nodes':len(entries),'views':len(views),'topics':len(sections),'periodSummaries':sum('periodSummary' in s for s in sections),'aspectSummaries':sum(len(s['aspectSummaries']) for s in sections),'frameworkCards':len(cards),'approvedFrameworkInstances':sum(len(c['series']) for c in cards),'reports':len(data['reports']),'sources':len(data['sources']),'acceptedCells':data['monthlyCoverage']['acceptedCells']}
    require(stats=={'nodes':232,'views':81,'topics':5,'periodSummaries':5,'aspectSummaries':35,'frameworkCards':26,'approvedFrameworkInstances':48,'reports':143,'sources':204,'acceptedCells':12},'third actual dataset counts mismatch')
    require(len({e['id'] for e in entries})==232 and len({o['id'] for o in views})==81,'third duplicate node/view identities')
    return stats

def public_privacy(data):
    forbidden=re.compile(r'(^_|sha256|hash|unicode(Start|End)|context(Start|End|Radius)|offset|^literal$|rawLiteral|typedSupport|contact|email|phone|locatorReference|artifactPin|textPath|localPath|rawPath|bodyText|fullText|rawHTML|renderedHTML|sourcePin|textPin|rawHorizon|originalExcerpt)',re.I)
    bad=[]
    def walk(x,path=''):
        if isinstance(x,dict):
            for k,v in x.items():
                if forbidden.search(k) and k not in ('literalResearchWindow','literalHorizonUnknown'):bad.append(path+'/'+k)
                walk(v,path+'/'+k)
        elif isinstance(x,list):
            for n,v in enumerate(x):walk(v,path+'/'+str(n))
        elif isinstance(x,str):
            if re.search(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]|/Users/|/home/|/mnt/|\\\\|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|https?:[^\s]*[?&](?:token|signature|access_token|sign|auth|X-Amz-Signature)=',x,re.I):bad.append(path+':private-value')
    walk(data)
    require(not bad,'public private fields/value leak: '+str(bad[:10]))
    require(all(o.get('evidenceExcerpt') is None for k in ('researchEvidence','windResearchEvidence','wechatResearchEvidence') for o in data[k]),'paid excerpt not null')
    return {'privateFields':0,'paidExcerpts':0}

def validate_public(data,raw,receipt):
    stats=public_stats(data);privacy=public_privacy(data)
    require(receipt['schemaVersion']=='renewed-easing-qt-end-local-candidate-1' and receipt['stageSlug']==SLUG and receipt['receiptScope']=='local-candidate-not-publication','not a third local candidate receipt')
    require(receipt['datasetSHA256']==H(raw),'actual dataset SHA differs from local candidate receipt')
    require(receipt['privateOriginalReadback'] is True and receipt['rawOriginalsCheckedOnlyLocally'] is True and receipt['publicationAuthorized'] is False and receipt['published'] is False,'local candidate receipt scope mismatch')
    require(all(receipt[k]==v for k,v in stats.items()),'receipt declared counts disagree with actual artifact')
    reports=data['reports'];sources=data['sources'];rm={r['id']:r for r in reports};sm={s['id']:s for s in sources}
    require(len(rm)==143 and len(sm)==204,'bibliographic ID collision')
    for r in reports:
        require(r['sourceId'] in sm,'bibliographic report source absent')
        if r['channel']=='知识星球':
            require(r['publicationDate'] is None and r['firstAvailableDate'] is None and r['historicalAsOfEligible'] is False,'star availability upgraded')
    roles=('expectationTimeline','realityTimeline','mechanism','divergence','implicationTimeline','examples','validation')
    for s in data['marketAnalysis']['sections']:
        require(set(s['deepDive'])==set(roles) and set(s['aspectSummaries'])==set(roles),'seven role schema mismatch')
        allnodes={e['id']:e for es in s['deepDive'].values() for e in es}
        for role,es in s['deepDive'].items():
            for e in es:
                require(set(e['sourceIds'])<=sm.keys() and set(e['reportIds'])<=rm.keys() and e['evidenceRefs'],'unregistered or empty node support')
                require(e.get('historicalAsOfEligible') is False and e.get('firstAvailableDate') is None,'current research historical upgrade')
                require(set(ref['id'] for ref in e.get('supportingEvidence',[]))<=set(e['evidenceRefs']),'supporting evidence ID mismatch')
            if role in ('expectationTimeline','realityTimeline','implicationTimeline'):
                ds=[e['date'] for e in es if e['date']];require(ds==sorted(ds),'timeline ordering differs')
        for summary,allowed in [(s['periodSummary'],allnodes)]+[(s['aspectSummaries'][role],{e['id']:e for e in s['deepDive'][role]}) for role in roles]:
            require(summary['evidenceRefs'] and set(summary['evidenceRefs'])<=allowed.keys(),'summary support crosses topic or role')
            selected=[allowed[id] for id in summary['evidenceRefs']]
            for key in ('sourceIds','reportIds'):require(set(summary[key])=={v for e in selected for v in e[key]},'summary reference closure differs')
    views=[v for k in ('researchEvidence','windResearchEvidence','wechatResearchEvidence') for v in data[k]]
    for v in views:
        require(v['reportId'] in rm and set(v.get('realitySourceIds',[]))<=sm.keys(),'opinion support source/report absent')
        require(v['historicalAsOfEligible'] is False and v['firstAvailableDate'] is None and v['evidenceExcerpt'] is None,'opinion information-boundary/paid excerpt violation')
        if rm[v['reportId']]['channel']=='知识星球':require(v['expressedAt'] is None and not v.get('institutionVotes') and not v.get('independentInstitutionVote'),'transcript timestamp or institution vote upgraded')
    rows=data['monthlyCoverage']['rows'];require([r['month'] for r in rows]==['2025-09','2025-10','2025-11','2025-12'],'monthly matrix exact four months required')
    quotas={'知识星球':20,'Wind':10,'微信公众号':5};matrix=[]
    for row in rows:
        counts={}
        require(set(row['channels'])==set(quotas),'monthly channel set mismatch')
        for channel,minimum in quotas.items():
            docs=[r for r in reports if r['channel']==channel and r['date'][:7]==row['month']]
            count=len({r['id'] for r in docs});cell=row['channels'][channel]
            require(count==cell['bodyCount']==cell['verifiedBodyCount'] and count>=minimum and cell['quotaAccepted'] is True and cell['accepted'] is True,'public bibliography does not meet monthly cell quota')
            if channel=='微信公众号':require(len({r.get('accountActual') or r['provider'] for r in docs})>=2,'wechat monthly account diversity absent')
            if channel=='知识星球':require(cell['searchExhaustive'] is False and cell['actualEligibleTotal'] is None,'quota mislabeled as exhaustive website total')
            counts[channel]=count
        matrix.append({'month':row['month'],'counts':counts})
    require(data['monthlyCoverage']['complete'] is True and data['monthlyCoverage']['requiredCells']==12,'incomplete current matrix')
    return {**stats,'scope':'public-dataset-bibliography-quota-privacy','rawOriginalReadbackPerformed':False,'rawOriginalClaimOnlyFromBoundLocalCandidateReceipt':True,'publicSHA256':H(raw),'monthlyRows':matrix,'privacy':privacy,'publicationAuthorized':False,'published':False,'pageQAComplete':False,'fullStageReady':False}

def verify_publication(data, raw, receipt):
    require(receipt.get('schemaVersion') == 'renewed-easing-qt-end-publication-1', 'not the dedicated third publication receipt')
    require(receipt.get('stageSlug') == SLUG and receipt.get('routeHash') == '#history/easing-to-tightening/' + SLUG, 'wrong publication stage')
    require(receipt.get('publicationAuthorized') is True and receipt.get('authorization') == 'OK，上线', 'no user publication authorization')
    require(receipt.get('privateChecksPassed') is True and receipt.get('verificationMode') == 'local-private-archive-readback-then-approved-public-dataset', 'private source readback not bound')
    require(receipt.get('datasetSHA256') == H(raw), 'publication exact approved bytes mismatch')
    require(receipt.get('pageQAComplete') is True and receipt.get('pageQADatasetSHA256') == H(raw), 'page QA bound to different bytes')
    result = validate_public(data, raw, receipt['localCandidateReceipt'])
    require(receipt['counts'] == {key: result[key] for key in public_stats(data)}, 'publication counts differ from actual snapshot')
    require(receipt['monthlyRows'] == result['monthlyRows'], 'publication monthly counts differ')
    scan = receipt['paidLiteralScan']
    require(scan['originalLiteralMatches'] == 0 and scan['allPaidLiteralComparisons'] == 231 and scan['newPaidQuoteAuthorization'] == 0, 'paid original scan not bound')
    result.update(scope='approved-third-publication-snapshot-bibliography-quotas-privacy', publicationAuthorized=True, pageQAComplete=True, fullStageReady=True, rawOriginalReadbackPerformed=False, originalReadbackClaimOnlyFromBoundLocalReceipt=True)
    return result

def check_dist(directory):
    scanned = 0
    require(directory.is_dir(), 'dist missing')
    for path in directory.rglob('*'):
        if not path.is_file():
            continue
        require(path.suffix.lower() in ('.js', '.css', '.html'), 'non-public filetype in dist')
        text = path.read_text(encoding='utf-8')
        require(not re.search(r'E:[\\/]+HermesProject|C:[\\/]+(?:Users|HermesData)|unicodeStart|rawLiteral|rawHorizon|typedSupport', text), 'private audit leaked into dist')
        scanned += 1
    require(scanned > 0, 'empty dist')
    return scanned

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=ROOT / 'src/data/historyReplayRenewedEasingQtEnd.json')
    parser.add_argument('--receipt', type=Path, default=ROOT / 'release/replay-renewed-easing-publication.json')
    parser.add_argument('--dist', type=Path)
    args = parser.parse_args(argv)
    try:
        raw = args.dataset.read_bytes()
        result = verify_publication(json.loads(raw), raw, json.loads(args.receipt.read_bytes()))
        if args.dist:
            result['distFilesScanned'] = check_dist(args.dist)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(json.dumps({'status': 'INVALID_THIRD_PUBLICATION', 'reason': str(error), 'rawOriginalReadbackPerformed': False}, ensure_ascii=False))
        return 2

if __name__ == '__main__':
    sys.exit(main())
