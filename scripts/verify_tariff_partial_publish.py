"""Public gate for user-authorized PARTIAL tariff-pause release; never certifies completeness."""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote
from verify_renewed_easing_publish import check_dist, public_privacy
ROOT=Path(__file__).resolve().parents[1]
def verify(data,raw,receipt):
    assert receipt['scope']=='explicitly-authorized-partial-publication'
    assert receipt['authorization']=='继续推进，并简单一些，我的Token不多了，尽快上线，待后续补充。'
    assert receipt['publicationAuthorized'] and receipt['pageQAComplete'] and not receipt['fullStageReady']
    assert hashlib.sha256(raw).hexdigest()==receipt['datasetSHA256']
    assert data['title']=='关税迷雾下的暂停' and data['startDate']=='2025-01-01' and data['asOf']==data['endDate']=='2025-08-31'
    assert data['partialRelease']['status']=='partial' and data['partialRelease']['fullStageReady'] is False
    assert '待补充' in data['partialRelease']['notice'] and '不代表完整阶段验收' in data['partialRelease']['notice']
    sections=data['marketAnalysis']['sections'];assert len(sections)==5
    assert sections[4]['id']=='dollar-relative' and not sections[4].get('deepDive')
    nodes=[n for s in sections for ns in s.get('deepDive',{}).values() for n in ns]
    assert len(nodes)==len({n['id'] for n in nodes})==151
    assert sum(len(s.get('periodSummary',{}).get('paragraphs',[])) for s in sections)==16
    assert sum(len(s.get('aspectSummaries',{})) for s in sections)==28
    sources={s['id'] for s in data['sources']};assert len(sources)==79
    for n in nodes:
        assert n['historicalAsOfEligible'] is False and n['firstAvailableDate'] is None
        assert set(n['sourceIds'])<=sources
    assert all(s['historicalAsOfEligible'] is False and s['firstAvailableDate'] is None for s in data['sources'])
    rows=data['monthlyCoverage']['rows'];assert [r['month'] for r in rows]==[f'2025-{m:02}' for m in range(1,9)]
    deficits=0
    for r in rows:
        assert set(r['channels'])=={'Wind','知识星球','微信公众号'}
        for ch,cell in r['channels'].items():
            assert cell['requiredCount']==(5 if ch=='微信公众号' else 20)
            assert cell['quotaAccepted']==(cell['bodyCount']>=cell['requiredCount'])
            deficits+=not cell['quotaAccepted']
    assert deficits==11 and data['monthlyCoverage']['complete'] is False
    assert data['monthlyCoverage']['acceptedCells']==13
    chart=sections[3]['approvedChart']['src'];assert chart.startswith('data:image/svg+xml;charset=utf-8,')
    svg=unquote(chart.split(',',1)[1]);assert hashlib.sha256(svg.encode()).hexdigest()==receipt['chartSHA256']
    assert not re.search(r'<script|href=',svg,re.I)
    public_privacy({**data, **{k:data.get(k,[]) for k in ('researchEvidence','windResearchEvidence','wechatResearchEvidence')}})
    return {'status':'PASS_AUTHORIZED_PARTIAL_ONLY','nodes':len(nodes),'topicsAdmitted':4,'quotaDeficitCells':deficits,'fullStageReady':False}
def main():
    p=argparse.ArgumentParser();p.add_argument('--dist',type=Path);p.add_argument('--full-gate',action='store_true');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    raw=(ROOT/'src/data/historyReplayTariffPause.json').read_bytes();d=json.loads(raw);r=json.loads((ROOT/'release/replay-tariff-partial-publication.json').read_bytes());result=verify(d,raw,r)
    if a.self_test:
        for mutation in ('complete','history','dollar'):
            x=copy.deepcopy(d)
            if mutation=='complete':x['partialRelease']['fullStageReady']=True
            if mutation=='history':x['sources'][0]['historicalAsOfEligible']=True
            if mutation=='dollar':x['marketAnalysis']['sections'][4]['deepDive']={'mechanism':[{'text':'unreviewed'}]}
            newraw=json.dumps(x,ensure_ascii=False).encode();rr={**r,'datasetSHA256':hashlib.sha256(newraw).hexdigest()}
            try:verify(x,newraw,rr)
            except AssertionError:continue
            raise AssertionError('mutation accepted: '+mutation)
        result['selfHashedMutationsRejected']=3
    if a.dist:result['distFilesScanned']=check_dist(a.dist)
    print(json.dumps(result,ensure_ascii=False))
    return 2 if a.full_gate and result['quotaDeficitCells'] else 0
if __name__=='__main__':raise SystemExit(main())
