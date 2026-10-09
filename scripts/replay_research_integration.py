"""Independent parent original-reader and explicit hash-pinned research adapter.

Offline only. Never imports or reruns delegated validators. Original archives and
child research stay read-only; parent review receipts live in a separate folder.
"""
import csv
import copy
import hashlib
import json
import re
from collections import Counter
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone

RESEARCH = 'monthly-expectation-reality-20261009.json'
OPINIONS = 'channel-verified-opinions-20261009.json'
AUDIT = '核验/预期现实分析推进20261009'
THEME_IDS = ['policy-path', 'inflation-vintages', 'demand-supply', 'treasury-curve', 'dollar-relative']
BODY_FIELDS = ('judgement', 'expectation', 'reality', 'mechanism', 'divergence', 'implication', 'validation')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def resolve(path, stage, root):
    path = Path(path)
    if path.is_absolute():
        return path
    return root / path if (root / path).is_file() else stage / path

def text_digest(text):
    return digest(text.encode('utf-8'))

def compact(text):
    # Whitespace-only comparison plus documented WeChat invisible formatting.
    return re.sub(r'[\s\u200b\ufeff]', '', text)

class OriginalHTML(HTMLParser):
    """Extract text nodes and explicit ID containers, without executing a page."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.by_id = {}
        self.visible = []
        self.skip = 0
        self.meta = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[attrs.get('property', attrs.get('name', ''))] = attrs.get('content', '')
        if tag in ('script', 'style'):
            self.skip += 1
        if tag not in ('meta', 'img', 'br', 'hr', 'input', 'link', 'source', 'wbr', 'area', 'base', 'embed', 'param', 'track', 'col'):
            self.stack.append((tag, attrs.get('id')))
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        for index in range(len(self.stack)-1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break
    def handle_data(self, data):
        if self.skip:
            return
        self.visible.append(data)
        for _, identifier in self.stack:
            if identifier:
                self.by_id.setdefault(identifier, []).append(data)
    def container(self, identifier):
        return ''.join(self.by_id.get(identifier, []))

def require(condition, message):
    if not condition:
        raise ValueError(message)

def verify_fact_semantics(stage, root):
    """Parse headline values from original release clauses, not child numbers.

    Offsets in receipts address exact disk-decoded Unicode text. For qualitative
    claims, require their actual policy clauses; forecasts are never treated as
    realized GDP/PCE or independent market consensus.
    """
    stage, root = Path(stage), Path(root)
    study = read_json(stage/'研究'/RESEARCH)
    registry = read_json(stage/'研究/official-evidence.json')['sources']
    registry += read_json(stage/AUDIT/'official-increment-verified-facts.json')['sources']
    registry = {s['id']:s for s in registry}
    results, failures = [], []
    for fact in study['officialFacts']:
        sid = fact['sourceIds'][0]; source = registry[sid]
        t = resolve(source['textPath'],stage,root).read_bytes().decode('utf-8-sig')
        parsed, spans = {}, []
        def grab(pattern):
            match = re.search(pattern,t,re.I|re.S)
            require(match is not None, 'missing semantic clause: '+pattern)
            literal = match.group()
            spans.append({'sourceId':sid,'start':match.start(),'endExclusive':match.end(),'textSHA256':text_digest(t),'sha256':text_digest(literal),'text':literal})
            return match
        def block(needle, length=1700):
            match = re.search(re.escape(needle),t,re.I)
            require(match is not None,'missing semantic block: '+needle)
            start,end = match.start(), min(len(t),match.start()+length)
            spans.append({'sourceId':sid,'start':start,'endExclusive':end,'textSHA256':text_digest(t),'sha256':text_digest(t[start:end]),'text':t[start:end]})
            return re.sub(r'\s+',' ',t[start:end])
        def number(pattern):
            return float(grab(pattern).group(1))
        def percent_pair(needle):
            b = block(needle,700)
            matches = re.findall(r'(increased|decreased|rose|fell)\s+(\d+\.\d+)\s+percent',b,re.I)
            require(len(matches)>=2,'two actual percent clauses')
            return [(-1 if verb.lower() in ('decreased','fell') else 1)*float(n) for verb,n in matches[:2]]
        try:
            date = source.get('publicationDate') or source['date']
            dt = datetime.fromisoformat(date)
            grab(fr'{dt.strftime("%B")}\s+0?{dt.day},?\s+{dt.year}|{dt.strftime("%b")}\.?\s+0?{dt.day},?\s+{dt.year}')
            v = fact.get('value') or {}
            fid = fact['id']
            if 'realGDPSAAR' in v:
                parsed['realGDPSAAR'] = number(r'Real gross domestic product\s*\(GDP\)\s+increased at an annual rate of\s+(\d+\.\d+)\s+percent')
                parsed['privateDomesticFinalPurchasesSAAR'] = number(r'Real final sales to private domestic purchasers,.*?increased\s+(\d+\.\d+)\s+percent')
                grab(re.escape(v['releaseVersion'])+r' estimate')
                # Observation quarter is read from the GDP headline, not release
                # month; the archived vintage and release date remain separate.
                obs = fact['observationPeriod']; q={'Q1':'first','Q2':'second','Q3':'third','Q4':'fourth'}[obs[-2:]]
                grab(fr'Real gross domestic product.*?in the {q} quarter of {obs[:4]}')
            elif 'observations' in v:
                mom = percent_pair('From the preceding month')
                require(mom == [0.2,0.2],'Oct/Nov both months monthly PCE')
                b=block('From the same month one year ago',520)
                nums=[float(x) for x in re.findall(r'(\d+\.\d+) percent',b)[:4]]
                require(nums == [2.7,2.8,2.7,2.8],'Oct/Nov annual PCE order')
                block('using the geometric mean',260)
                parsed['observations']=[{'observationPeriod':'2025-10','headlineMoM':mom[0],'coreMoM':mom[1],'headlineYoY':nums[0],'coreYoY':nums[2]}, {'observationPeriod':'2025-11','headlineMoM':mom[0],'coreMoM':mom[1],'headlineYoY':nums[1],'coreYoY':nums[3]}]
            elif 'headlineMoM' in v and 'bea-' in sid:
                mom=percent_pair('From the preceding month'); yoy=percent_pair('From the same month one year ago')
                parsed.update(headlineMoM=mom[0],coreMoM=mom[1],headlineYoY=yoy[0],coreYoY=yoy[1])
            elif 'headlineMoM' in v:
                b=block('The Consumer Price Index for All Urban Consumers',900)
                match=re.search(r'\(CPI-U\)\s+(increased|decreased)\s+(\d+\.\d+)\s+percent',b)
                parsed['headlineMoM']=float(match[2])*(-1 if match[1]=='decreased' else 1)
                b=block('The index for all items less food and energy',700)
                match=re.search(r'(rose|increased)\s+(\d+\.\d+)\s+percent',b)
                parsed['coreMoM']=0.0 if re.search(r'^The index for all items less food and energy was unchanged',b) else float(match[2]) if match else None
                parsed['headlineYoY']=number(r'all items index\s+(?:rose|increased)\s+(\d+\.\d+)\s+percent\s+(?:for the 12 months|before seasonal adjustment)')
                parsed['coreYoY']=number(r'all items less food and energy index\s+(?:rose|increased)\s+(\d+\.\d+)\s+percent\s+over (?:the year|the last 12 months)')
                if 'energyMoM' in v:
                    parsed['energyMoM']=-number(r'index for energy fell\s+(\d+\.\d+)\s+percent')
            elif 'nonfarmPayrollChange' in v:
                b=block('THE EMPLOYMENT SITUATION',2200)
                match=re.search(r'nonfarm payroll employment.*?\(([+-]?[\d,]+)\)',b,re.I)
                if match is None:
                    match=re.search(r'nonfarm payroll employment\s+(?:increased|rose) by\s+([\d,]+)',b,re.I)
                require(match is not None,'headline payroll signed count')
                parsed['nonfarmPayrollChange']=int(match[1].replace(',',''))
                match=re.search(r'unemployment rate\s*(?:\(|,?\s*(?:was|at|changed little at|remained at|edged down to|was unchanged at)\s*)(\d+\.\d+)\s+percent',b,re.I)
                if match is None:
                    match=re.search(r'unemployment rate.{0,100}?(\d+\.\d+)\s+percent',b,re.I)
                require(match is not None,'headline unemployment rate')
                parsed['unemploymentRate']=float(match[1])
                if 'laborForceParticipationRate' in v:
                    b=block('labor force participation rate',500)
                    parsed['laborForceParticipationRate']=float(re.search(r'(?:at|to)\s+(\d+\.\d+)\s+percent',b)[1])
                if 'employmentPopulationRatio' in v:
                    parsed['employmentPopulationRatio']=number(r'employment-population ratio, at\s+(\d+\.\d+)\s+percent')
                if 'averageHourlyEarningsYoYPct' in v:
                    parsed['averageHourlyEarningsYoYPct']=number(r'Over the year, average hourly earnings have increased by\s+(\d+\.\d+)\s+percent')
                if 'revisions' in v:
                    b=block('The change in total nonfarm payroll employment',1000)
                    revisions={}
                    for month,pair in v['revisions'].items():
                        if isinstance(pair,dict):
                            match=re.search(fr'(?:employment for |change for ){month} was revised.*?from\s+\+?([\d,]+)\s+to\s+\+?([\d,]+)',b)
                            require(match is not None,'revision month scope '+month)
                            revisions[month]={'prior':int(match[1].replace(',','')),'revised':int(match[2].replace(',',''))}
                        else:
                            match=re.search(r'combined is\s+([\d,]+)\s+lower',b)
                            revisions[month]=int(match[1].replace(',',''))
                    parsed['revisions']=revisions
            elif fid.startswith('sep-'):
                for key,label in [('GDP','Change in real GDP'),('unemployment','Unemployment rate'),('PCE','PCE inflation'),('corePCE','Core PCE inflation'),('fedFunds','Federal funds rate')]:
                    parsed[key]=number(re.escape(label)+r'\d?\s+(\d+\.\d+)')
                block('Note: Projections of change in real gross domestic product',1800)
            elif fid.startswith('rate-decision-'):
                grab(r'maintain the target range for the federal funds rate at 3[-‑]1/2 to 3[-‑]3/4 percent')
                parsed.update(lower=3.5,upper=3.75)
                if date in ('2026-06-17','2026-07-29'):
                    match=grab(r'by a (\d+)\s*[–-]\s*(\d+) vote')
                    parsed['votes']=[int(match[1]),int(match[2])]
                    require(parsed['votes']==([12,0] if date=='2026-06-17' else [9,3]),'actual vote count')
                    if date=='2026-07-29':
                        grab(r'Voting against.*?Hammack.*?Kashkari.*?Logan.*?preferred to raise.*?1/4 percentage point')
                    else:
                        grab(r'The Committee will deliver price stability')
                        require('In considering the extent and timing' not in t,'June removed forward adjustment sentence')
                elif date=='2026-01-28':
                    grab(r'Voting against.*?Miran and Christopher J\. Waller.*?preferred to lower.*?1/4 percentage point')
                elif date=='2026-03-18':
                    grab(r'Voting against.*?Miran.*?preferred to lower.*?1/4 percentage point')
                    grab(r'Middle East.*?uncertain')
                else:
                    grab(r'Voting against.*?Miran.*?preferred to lower.*?Hammack.*?Kashkari.*?Logan.*?supported maintaining.*?did not support inclusion of an easing bias')
            elif fid.startswith('leadership-'):
                if fid.endswith('03-04'):
                    grab(r'President Donald J\. Trump nominated Mr\. Warsh on March 4, 2026')
                elif fid.endswith('05-12'):
                    grab(r'confirmed by the United States Senate to serve as a member of the Board on May 12')
                elif fid.endswith('05-13'):
                    grab(r'confirmed by the United States Senate.*?as chairman of the Board on May 13')
                else:
                    grab(r'Kevin Warsh on Friday took the oath of office as chairman and a member.*?unanimously selected Warsh as its chairman')
                parsed.update(reportedOn=date,earliestVerifiedPublication=date)
            elif fid.startswith('minutes-'):
                needles={'2026-02-18':['two-sided description','upward adjustments to the target range'], '2026-04-08':['a prolonged conflict in the Middle East','risks to both sides'], '2026-05-20':['One participant preferred to lower','Three members'], '2026-07-08':['preferred not to repeat','Most participants, however, also pointed to scenarios'], '2026-08-19':['Several participants favored an increase','if inflation']}
                for needle in needles[date]:
                    block(needle,1900)
            elif fid=='jackson-hole-2026':
                parsed['unemploymentMentioned']=number(r'jobless rate, at\s+(\d+\.\d+)\s+percent')
                parsed['PCE12MonthMentioned']=number(r'12-month change in the PCE price index, stands at\s+(\d+\.\d+)\s+percent')
                block('financial conditions',1600)
                block('Here is my standard',1800)
            else:
                raise ValueError('No parent semantic rule for '+fid)
            for key,actual in parsed.items():
                if key in v:
                    require(v[key]==actual,'claimed '+key+' not supported by actual release')
            results.append({'factId':fid,'accepted':True,'reparsed':parsed,'publicationDate':date,'observationPeriod':fact.get('observationPeriod'),'releaseVersion':fact.get('releaseVersion'),'semanticSpans':spans})
        except Exception as error:
            failures.append({'factId':fact['id'],'reason':str(error)})
            results.append({'factId':fact['id'],'accepted':False,'reparsed':parsed,'semanticSpans':spans,'reason':str(error)})
    return {'facts':results,'failures':failures}

def reviewed_projection(study, private):
    """Whitelist presentation data only, with at most 100 quote chars per work.

    September month-only targets remain ongoing at the August cutoff. Channels
    are distribution metadata, not extra institutional votes. Transcript labels
    retain their self-attribution instead of upgrading corporate identity.
    """
    source_uses = Counter(o['sourceId'] for o in private['opinions'])
    opinions = []
    for original in private['opinions']:
        o = original; pair = copy.deepcopy(o['realizationPair']); horizon=copy.deepcopy(o['horizon'])
        if horizon.get('deadlineMonth','') > study['asOf'][:7]:
            pair['status']='ongoing'
            pair['note']='9月目标尚未到期；原文没有精确会议日，条件与首次历史可得仍未核。'
        budget = 100 // source_uses[o['sourceId']]
        quote = o['quote'][:budget]
        ends=[m.end() for m in re.finditer(r'[。！？；]',quote)]
        if ends and ends[-1]>=min(20,budget):
            quote=quote[:ends[-1]]
        limits=list(o['limitations'])
        if len(quote)<len(o['quote']):
            limits.append('仅公开精确短摘录；未公开的上下文已在私人审计核验，完整原文不挂载。')
        if o['channel']=='知识星球':
            limits.append('转录的机构/姓名为原文自述，未核机构原版与录音完整性，不计独立机构票。')
        reality = pair['note']
        if pair.get('subwindows'):
            reality += ' 子窗口：' + '；'.join(s.get('note') or s.get('status','待验') for s in pair['subwindows'])
        opinions.append({'id':o['id'],'reportId':o['sourceId'],'channel':'微信' if o['channel']=='微信公众号' else o['channel'],
            'expressedAt':o['publicationDate'],'dateBasis':o['dateBasis'],'actor':o['actor'],'claim':o['claim'],
            'scope':o['scope'],'observationPeriod':horizon['literalResearchWindow'],
            'pages':[o['physicalPage'] or o['paragraphId']],'evidenceExcerpt':quote,
            'evidenceSha256':o['sourceSHA256'],'evidenceExcerptSha256Utf8':text_digest(quote),
            'excerptLocations':[{'physicalPage':o['physicalPage'],'paragraphId':o['paragraphId'],
                'start':o['locator']['start'],'endExclusive':o['locator']['start']+len(quote),'unit':'unicode_codepoints'}],
            'conditions':copy.deepcopy(o['conditions']),'forecastHorizon':horizon,'reality':reality,'eventId':None,'eventDate':None,
            'realitySourceIds':pair['realitySourceIds'],'status':pair['status'],'realizationPair':pair,
            'claimType':'transcript_forward_looking_clause' if o['channel']=='知识星球' else o['claimType'],
            'limitations':limits,'reportTitle':o['title'],'firstAvailableDate':None,'historicalAsOfEligible':False,
            'isMarketConsensus':False,'countsAsAdditionalOpinion':False,'countsAsIndependentDocument':False,
            'attributionStatus':'transcript_self_attribution_not_independently_verified' if o['channel']=='知识星球' else 'original_research_attribution_not_market_consensus'})
    section_fields=('id','title',*BODY_FIELDS,'sourceIds','reportIds')
    analysis={k:copy.deepcopy(study['marketAnalysis'][k]) for k in ('title','conclusion','limitations')}
    analysis['sections']=[{k:copy.deepcopy(s[k]) for k in section_fields} for s in study['marketAnalysis']['sections']]
    monthly=[]
    for m in study['months']:
        row={k:copy.deepcopy(m[k]) for k in (*section_fields,'month','opinionIds','factIds','marketPath','dynamicConvergence')}
        row.update(historicalAsOfEligible=False,availableFrom=None,retrospectiveOnly=True)
        monthly.append(row)
    chains=[]
    for chain in study['revisionChains']:
        row={k:copy.deepcopy(chain[k]) for k in ('id','label','description','opinionIds')}
        has_transcript=any(o['channel']=='知识星球' and o['id'] in row['opinionIds'] for o in private['opinions'])
        row['identityStatus']='attributed_theme_trace_including_unverified_transcripts' if has_transcript else 'same_attributed_formal_institution'
        row['limitation']='含转录自述，不能视为已独立证明的同机构实时修订或额外投票。' if has_transcript else '同机构修订链，不是多个独立机构或市场共识；首次历史可得未知。'
        row.update(historicalAsOfEligible=False,availableFrom=None,retrospectiveOnly=True)
        chains.append(row)
    sources=[]
    for source in study['sources']:
        row={k:copy.deepcopy(source[k]) for k in ('id','title','publisher','url','publicationDate','retrievedAt','sha256','snapshotAt','note') if k in source}
        row.update(date=source.get('publicationDate') or (source.get('retrievedAt') or '')[:10],
            kind='独立父方复核的官方原文 / 追溯序列',status='当前追溯证据·不进入严格历史信息集',
            note=row.get('note','首次历史可得未知；保留原发布日、观察期与版本，不以取得日代替。'),
            firstAvailableDate=None,historicalAsOfEligible=False,retrospectiveOnly=True)
        sources.append(row)
    aliases=[{k:a[k] for k in ('sourceId','sha256','aliasReason')} for a in study['sourceAliases']]
    facts=[]
    for f in study['officialFacts']:
        facts.append({k:copy.deepcopy(f[k]) for k in ('id','claim','sourceIds','date','observationPeriod','value','releaseVersion') if k in f})
    return {'schemaVersion':'parent-reviewed-public-research-1','asOf':study['asOf'],'marketAnalysis':analysis,
        'monthlyReplay':monthly,'revisionChains':chains,'opinions':opinions,'officialFacts':facts,'sources':sources,
        'sourceAliases':aliases,'marketStatistics':copy.deepcopy(study['marketStatistics']),
        'historicalAsOfEligible':False,'firstAvailableDate':None,'retrospectiveOnly':True}

def load_reviewed(manifest_path, stage, root):
    """Explicit admission capability; names, flags and directory globs grant none."""
    stage, root = Path(stage),Path(root)
    manifest_path=resolve(manifest_path,stage,root)
    manifest=read_json(manifest_path)
    require(manifest.get('schemaVersion')=='parent-reviewed-research-manifest-1','Unrecognized reviewed research manifest')
    require((manifest.get('stageStart'),manifest.get('stageEnd'))==('2026-01-01','2026-08-31'),'Reviewed research stage mismatch')
    loaded={}
    for field in ('verification','accepted'):
        descriptor=manifest[field];path=resolve(descriptor['path'],stage,root)
        require(digest(path.read_bytes())==descriptor['sha256'],'Reviewed research '+field+' SHA is stale')
        loaded[field]=read_json(path)
    receipt=loaded['verification']
    require(manifest['inputPins']==receipt['inputPins'],'Reviewed research input pin registry differs from receipt')
    for name,sha in manifest['inputPins'].items():
        path=resolve(name,stage,root)
        require(path.is_file() and digest(path.read_bytes())==sha,'Reviewed research input SHA is stale: '+name)
    accepted_opinions={o['opinionId'] for o in receipt['opinions'] if o['accepted']}
    accepted_facts={f['factId'] for f in receipt['semanticReview']['facts'] if f['accepted']}
    require(set(manifest['acceptedOpinionIds'])==accepted_opinions,'Unreviewed opinion admission')
    require(set(manifest['acceptedFactIds'])==accepted_facts,'Unreviewed official fact admission')
    study=read_json(stage/'研究'/RESEARCH);private=read_json(stage/'研究'/OPINIONS)
    expected=reviewed_projection(study,private)
    expected['opinions']=[o for o in expected['opinions'] if o['id'] in accepted_opinions]
    expected['officialFacts']=[f for f in expected['officialFacts'] if f['id'] in accepted_facts]
    require(loaded['accepted']==expected,'Reviewed public projection differs from pinned originals and whitelist')
    result=copy.deepcopy(expected)
    result['manifestSHA256']=digest(manifest_path.read_bytes())
    result['pending']=copy.deepcopy(manifest.get('pending',[]))
    return result

def integrate_reviewed(data, manifest_path, stage, root):
    """Adapt source IDs only after SHA matches an already admitted body."""
    reviewed=load_reviewed(manifest_path,stage,root)
    require(data['asOf']==reviewed['asOf'],'Reviewed research cutoff mismatch')
    remap={}
    opinion_by_source={o['reportId']:o for o in reviewed['opinions']}
    for alias in reviewed['sourceAliases']:
        sid=alias['sourceId'];opinion=opinion_by_source[sid]
        channel='微信公众号' if opinion['channel']=='微信' else opinion['channel']
        candidates=[r for r in data['reports'] if r.get('sha256')==alias['sha256'] and
                    ('微信公众号' if r.get('channel') in ('微信','微信公众号') else r.get('channel'))==channel and
                    r.get('sourceQuality',{}).get('parentLedgerVerified') is True]
        require(bool(candidates),'Reviewed source is not an admitted original: '+sid)
        exact=next((r for r in candidates if r['id']==sid),None)
        require(exact is not None or len(candidates)==1,'Ambiguous SHA-matched reviewed source: '+sid)
        target=exact or candidates[0]
        remap[sid]=target['id']
    def adapt(value):
        if isinstance(value,list):
            return [adapt(v) for v in value]
        if isinstance(value,dict):
            return {k:adapt(v) for k,v in value.items()}
        if isinstance(value,str):
            if value in remap:
                return remap[value]
            for old,new in remap.items():
                value=value.replace('['+old+']','['+new+']')
        return value
    reviewed=adapt(reviewed)
    source_registry={s['id']:s for s in data['sources']}
    for source in reviewed['sources']:
        prior=source_registry.get(source['id'])
        if prior:
            if prior.get('sha256'):
                require(prior['sha256']==source['sha256'],'Reviewed official source SHA conflict')
            prior.update(source)
        else:
            data['sources'].append(source);source_registry[source['id']]=source
    report_ids={r['id'] for r in data['reports']}
    source_ids=set(source_registry)
    for row in reviewed['monthlyReplay']+reviewed['marketAnalysis']['sections']:
        require(set(row['reportIds'])<=report_ids and set(row['sourceIds'])<=source_ids,'Reviewed analysis dangling references')
    opinion_ids={o['id'] for o in reviewed['opinions']}
    fact_ids={f['id'] for f in reviewed['officialFacts']}
    for opinion in reviewed['opinions']:
        require(opinion['reportId'] in report_ids and set(opinion['realitySourceIds'])<=source_ids,'Reviewed opinion dangling references')
        report=next(r for r in data['reports'] if r['id']==opinion['reportId'])
        opinion['sourceQuality']=copy.deepcopy(report['sourceQuality'])
    for chain in reviewed['revisionChains']:
        require(set(chain['opinionIds'])<=opinion_ids,'Reviewed chain pending opinion')
    for month in reviewed['monthlyReplay']:
        require(set(month['opinionIds'])<=opinion_ids and set(month['factIds'])<=fact_ids,'Reviewed month pending references')
    data['marketAnalysis']=reviewed['marketAnalysis']
    data['summary']=[data['marketAnalysis']['conclusion']]
    for field,channel in (('researchEvidence','知识星球'),('windResearchEvidence','Wind'),('wechatResearchEvidence','微信')):
        data[field]=[o for o in reviewed['opinions'] if o['channel']==channel]
    if data.get('wechatCoverage'):
        data['wechatCoverage']['totalOpinions']=len(data['wechatResearchEvidence'])
    data['monthlyReplay']=reviewed['monthlyReplay']
    data['revisionChains']=reviewed['revisionChains']
    data['reviewedResearch']={'manifestSHA256':reviewed['manifestSHA256'],'opinionIds':sorted(opinion_ids),
        'factIds':sorted(fact_ids),'sourceAliases':[{'sourceId':old,'reportId':new,'sha256':next(o['evidenceSha256'] for o in reviewed['opinions'] if o['reportId']==new)} for old,new in remap.items()],
        'historicalAsOfEligible':False,'firstAvailableDate':None,'retrospectiveOnly':True,'coverageGateIndependent':True,'pendingCount':len(reviewed['pending'])}
    data['reportIdAliases'].update(remap)
    # Conservative first-availability policy also applies to current research's
    # dependent event eligibility. Original source books/events are not edited.
    for event in data['events']:
        event['historicalAsOfEligible']=bool(event.get('historicalAsOfEligible')) and all(source_registry[sid].get('historicalAsOfEligible') is True for sid in event.get('realitySourceIds',[])+event.get('expectationSourceIds',[]))
    return data

def verify_originals(stage, root):
    """Recompute actual source bytes, all physical pages and exact Unicode anchors.

    Receipts are comparison inputs, not admission flags. Failures are individual
    records; an unrelated failure never erases accepted opinions.
    """
    import pymupdf
    from pypdf import PdfReader
    stage, root = Path(stage), Path(root)
    study = read_json(stage/'研究'/RESEARCH)
    private = read_json(stage/'研究'/OPINIONS)
    failures, sources, opinions, official_checks, fact_checks = [], [], [], [], []
    cache, pins = {}, {}
    def pin(path):
        path = Path(path)
        pins[str(path.relative_to(stage) if path.is_relative_to(stage) else path)] = digest(path.read_bytes())
    for name in (RESEARCH, OPINIONS):
        pin(stage/'研究'/name)
    for path in (stage/'研究/official-evidence.json',stage/'研究/market-paths.json',stage/AUDIT/'official-increment-verified-facts.json'):
        pin(path)
    for opinion in private['opinions']:
        sid, sha = opinion['sourceId'], opinion['sourceSHA256']
        if sha in cache:
            continue
        try:
            bookpath = resolve(opinion['parentBibliography'], stage, root)
            pin(bookpath)
            book = read_json(bookpath)
            record = next(r for r in book.get('articles', book.get('items', []))
                          if (r.get('sha256') or r.get('bodySHA256')) == sha)
            path = resolve(opinion['documentPath'], stage, root)
            data = path.read_bytes()
            require(digest(data) == sha, 'original file SHA')
            require(len(data) == (record.get('bytes') if opinion['physicalPage'] else record['bodyBytes']), 'original bytes')
            pin(path)
            containers, pages, printed_dates = {}, [], []
            if opinion['physicalPage']:
                require(opinion['parser'].startswith('PyMuPDF '+pymupdf.VersionBind), 'quote parser version')
                pdf = PdfReader(path, strict=True)
                with pymupdf.open(path) as secondary:
                    require(len(pdf.pages) == len(secondary) == record['pageCount'], 'all-page count')
                    auditpath = record.get('fullPageEvidence') or record.get('fullPageTextEvidence') or record.get('pageAuditPath') or record.get('auditPath')
                    audit = read_json(resolve(auditpath, stage, root)) if auditpath else record
                    if auditpath:
                        pin(resolve(auditpath, stage, root))
                    archived = audit.get('pages') or audit.get('pageChecks') or record.get('pageChecks')
                    require(len(archived) == len(pdf.pages), 'complete page audit required')
                    for number, page in enumerate(pdf.pages, 1):
                        raw = page.extract_text() or ''
                        raw2 = secondary[number-1].get_text('text')
                        expected = archived[number-1]
                        require(text_digest(raw) == expected['pypdfTextSHA256'], f'pypdf raw page {number}')
                        require(text_digest(raw2) == expected['pymupdfTextSHA256'], f'PyMuPDF raw page {number}')
                        if 'pypdfText' in expected:
                            require(raw == expected['pypdfText'] and raw2 == expected['pymupdfText'], f'raw page text {number}')
                        pages.append({'physicalPage': number, 'pypdfTextSHA256': text_digest(raw), 'pymupdfTextSHA256': text_digest(raw2)})
                        containers[number] = raw2
                if opinion['channel']=='Wind':
                    require(opinion['publicationDate']==record['publicationDate'],'printed/publication date identity')
                    year,month,day=map(int,opinion['publicationDate'].split('-'))
                    pattern=fr'{year}\s*年\s*0?{month}\s*月\s*0?{day}\s*日'
                    for number,raw in containers.items():
                        match=re.search(pattern,raw)
                        if match:
                            printed_dates.append({'physicalPage':number,'start':match.start(),'endExclusive':match.end(),'literal':match.group(),'containerSHA256':text_digest(raw),'excerptSHA256':text_digest(match.group())})
                    require(bool(printed_dates),'actual printed PDF publication date')
            else:
                pp = resolve(record['paragraphsPath'], stage, root)
                hp = resolve(record.get('rawHtmlPath') or record['rawHTMLPath'], stage, root)
                mp = resolve(record.get('metadataPath') or record['initialIntakeMetadataPath'], stage, root)
                for target in (pp,hp,mp):
                    pin(target)
                paragraphs = read_json(pp)
                require(len(paragraphs) == record['paragraphCount'], 'ordered paragraphs count')
                htmlbytes = hp.read_bytes()
                require(digest(htmlbytes) == record['rawHTMLSHA256'] and len(htmlbytes) == record['rawHTMLBytes'], 'raw HTML bytes')
                html = OriginalHTML(); html.feed(htmlbytes.decode('utf-8-sig'))
                metadata = read_json(mp)
                if 'renderedHTMLPath' in record:
                    rendered = resolve(record['renderedHTMLPath'], stage, root)
                    pin(rendered)
                    rb = rendered.read_bytes()
                    require(digest(rb) == record['renderedHTMLSHA256'], 'rendered original bytes')
                    html = OriginalHTML(); html.feed(rb.decode('utf-8-sig'))
                metadata = {**metadata, 'publicationHeader':metadata.get('publicationHeader') or metadata.get('publicationDisplay')}
                for identifier,key in [('activity-name','title'),('js_name','account'),('publish_time','publicationHeader')]:
                    require(compact(html.container(identifier)) == compact(metadata[key]), f'original header {identifier}')
                require(compact(metadata['title']) == compact(record['title']), 'title attribution')
                require(metadata['account'] == record['account'], 'original account')
                require(opinion['publicationDate'] == record['publicationDate'], 'publication date record')
                yy, mm, dd = map(int, record['publicationDate'].split('-'))
                require(re.search(fr'{yy}年0?{mm}月0?{dd}日', metadata['publicationHeader']) is not None, 'original date header')
                require(compact(html.container('js_content')) == compact(data.decode('utf-8')), 'actual original article body range')
                for index, p in enumerate(paragraphs, 1):
                    pid = p.get('id') or p['paragraphId']
                    require(pid == ('p'+str(index) if 'id' in p else f'p{index:04d}'), 'ordered paragraph identity')
                    require(text_digest(p['text']) == p['sha256'], 'paragraph UTF-8 hash')
                    containers[pid] = p['text']
                require(compact(''.join(p['text'] for p in paragraphs)) == compact(data.decode('utf-8')), 'all published body represented by paragraphs')
                if opinion.get('authorLiteral'):
                    require(compact(opinion['authorLiteral']) in compact(''.join(html.visible)), 'raw author header')
            cache[sha] = {'containers': containers, 'record': record}
            sources.append({'sourceId':sid,'sourceSHA256':sha,'bytes':len(data),'channel':opinion['channel'], 'pages':pages,'printedDateAnchors':printed_dates,'paragraphCount':len(containers) if not pages else None,'accepted':True})
        except Exception as error:
            failures.append({'kind':'source','id':sid,'reason':str(error)})
    fact_lookup = {f['id']:f for f in study['officialFacts']}
    for opinion in private['opinions']:
        try:
            item = cache[opinion['sourceSHA256']]
            t = item['containers'][opinion['physicalPage'] or opinion['paragraphId']]
            loc = opinion['locator']
            require(loc['unit'] == 'unicode_codepoints', 'offset unit')
            require(text_digest(t) == loc['containerTextSHA256'], 'raw container SHA')
            require(0 <= loc['contextStart'] <= loc['start'] < loc['endExclusive'] <= loc['contextEndExclusive'] <= len(t), 'Unicode offsets bounds')
            quote = t[loc['start']:loc['endExclusive']]
            context = t[loc['contextStart']:loc['contextEndExclusive']]
            require(quote == opinion['quote'] and text_digest(quote) == loc['excerptSHA256'], 'exact quote and SHA')
            require(context == opinion['context'] and text_digest(context) == loc['contextSHA256'], 'exact context and SHA')
            require(opinion.get('firstAvailableDate') is None and opinion.get('historicalAsOfEligible') is False, 'unknown historical eligibility')
            pair = opinion['realizationPair']; horizon = opinion['horizon']
            deadline = horizon.get('effectiveDeadline') or horizon.get('deadlineMonth')
            if deadline and deadline > study['asOf']:
                require(pair['status'] in ('ongoing','unobserved'), 'future horizon prematurely scored')
            require(pair['strictAsOfScoringAllowed'] is False, 'strict forecast scoring')
            for fid in pair['factIds']:
                require(fid in fact_lookup and fact_lookup[fid]['date'] <= study['asOf'], 'pair future/unknown fact')
            # Target dates must follow nominal report date, except explicit current
            # context facts used for forward-looking causal warning (not scoring).
            publication = opinion['publicationDate']
            if publication and pair['status'] not in ('ongoing','unobserved'):
                for fid in pair['factIds']:
                    fact = fact_lookup[fid]
                    require(fact['date'] >= publication or pair['status'] == 'direction_compatible_not_causally_identified', 'post-event report backfilled as forecast')
            opinions.append({'opinionId':opinion['id'],'sourceId':opinion['sourceId'],'accepted':True,'quoteSHA256':text_digest(quote),'contextSHA256':text_digest(context),'physicalPage':opinion['physicalPage'],'paragraphId':opinion['paragraphId'],'forecastHorizon':horizon,'status':pair['status']})
        except Exception as error:
            failures.append({'kind':'opinion','id':opinion['id'],'reason':str(error)})
            opinions.append({'opinionId':opinion['id'],'sourceId':opinion['sourceId'],'accepted':False,'reason':str(error)})
    official = read_json(stage/'研究/official-evidence.json')
    increments = read_json(stage/AUDIT/'official-increment-verified-facts.json')
    allofficial = [s for s in official['sources'] if s['id'] != 'fed-calendar'] + increments['sources']
    original_texts = {}
    for source in allofficial:
        try:
            path, tp = resolve(source['localPath'], stage, root), resolve(source['textPath'], stage, root)
            for target in (path,tp):
                pin(target)
            b, tb = path.read_bytes(), tp.read_bytes()
            require(digest(b) == source['sha256'] and digest(tb) == source['textSha256'], 'official original/text byte SHA')
            t = tb.decode('utf-8-sig')
            try:
                raw_html = b.decode('utf-8-sig')
                encoding = 'utf-8'
            except UnicodeDecodeError:
                # This archived BLS release contains a Windows-1252 dash byte.
                raw_html = b.decode('cp1252')
                encoding = 'cp1252'
            reader = OriginalHTML(); reader.feed(raw_html)
            raw_text = ''.join(reader.visible)
            # All meaningful text lines must occur in original HTML under only
            # whitespace equivalence. Text snapshots may add block separators.
            raw_compact = compact(raw_text)
            lines = [line for line in t.splitlines() if len(compact(line)) >= 30]
            require(all(compact(line) in raw_compact for line in lines), 'official text not derived from actual original HTML')
            original_texts[source['id']] = t
            original_url = source.get('originalURL') or source.get('originalUrl') or source.get('url','')
            require(any(host in original_url for host in ('federalreserve.gov','bea.gov','bls.gov')), 'official origin identity')
            date = source.get('publicationDate') or source.get('date')
            require(bool(date) and date <= study['asOf'], 'official publication date')
            official_checks.append({'sourceId':source['id'],'documentSHA256':digest(b),'textSHA256':digest(tb),'publicationDate':date,'originalURL':original_url,'snapshotAt':source.get('snapshotAt'),'accepted':True,'rawTextLinesMatched':len(lines),'originalEncoding':encoding})
        except Exception as error:
            failures.append({'kind':'official-source','id':source['id'],'reason':str(error)})
    for fact in study['officialFacts']:
        try:
            spans = []
            for evidence in fact['evidence']:
                t = original_texts[evidence['sourceId']]
                locs = evidence.get('locators', [])
                if 'start' in evidence:
                    locs = [evidence]
                if not locs and 'cpi-' in fact['id']:
                    # Child CPI regex produced no anchor. Recover actual original
                    # headline paragraphs; do not fabricate or modify its audit.
                    for needle in ('The Consumer Price Index for All Urban Consumers', 'The index for all items less food and energy', 'The all items index'):
                        match = re.search(re.escape(needle), t, re.I)
                        if match:
                            start = match.start(); end = min(len(t),start+1600)
                            locs.append({'start':start,'endExclusive':end,'sha256':text_digest(t[start:end]),'parentRecovered':True})
                require(bool(locs), 'fact has no exact original spans')
                for loc in locs:
                    q = t[loc['start']:loc['endExclusive']]
                    require(text_digest(q) == loc.get('sha256',loc.get('excerptSHA256')), 'official fact exact Unicode locator')
                    if 'supportStart' in loc:
                        support = t[loc['supportStart']:loc['supportEndExclusive']]
                        require(text_digest(support) == loc['supportSpanSHA256'], 'official support span SHA')
                        q = support
                    spans.append({'sourceId':evidence['sourceId'],'start':loc.get('supportStart',loc['start']),'endExclusive':loc.get('supportEndExclusive',loc['endExclusive']),'sha256':text_digest(q),'text':q})
            fact_checks.append({'factId':fact['id'],'accepted':True,'claim':fact['claim'],'value':fact.get('value'),'spans':spans})
        except Exception as error:
            failures.append({'kind':'fact','id':fact['id'],'reason':str(error)})
            fact_checks.append({'factId':fact['id'],'accepted':False,'reason':str(error)})
    market = read_json(stage/'研究/market-paths.json')
    lookup = {}
    for series in market['series']:
        if series['id'] not in ('DGS2','DGS10','DTWEXBGS'):
            continue
        path = resolve(series['localPath'], stage, root); pin(path)
        data = path.read_bytes(); require(digest(data) == series['sha256'], 'raw market SHA')
        rows = list(csv.DictReader(data.decode('utf-8-sig').splitlines()))
        require(list(rows[0]) == ['observation_date',series['id']], 'market series identity')
        values = {r['observation_date']:None if r[series['id']] in ('','.') else Decimal(r[series['id']]) for r in rows}
        require(all(values.get(r['date']) == (None if r['value'] is None else Decimal(str(r['value']))) for r in series['observations']), 'raw series observations')
        if series['id'] in ('DGS2','DGS10'):
            require(series['unit']=='%' and all(0 < v < 10 for v in values.values() if v is not None),'rates units/range')
        lookup[series['id']] = values
    calculations = []
    for row in study['marketStatistics']['monthly']:
        month = row['month']; days = sorted(d for d in lookup['DGS2'] if d.startswith(month) and lookup['DGS2'][d] is not None and lookup['DGS10'].get(d) is not None)
        start,end = days[0],days[-1]; a,b,c,d = lookup['DGS2'][start],lookup['DGS2'][end],lookup['DGS10'][start],lookup['DGS10'][end]
        usd = sorted(d for d,v in lookup['DTWEXBGS'].items() if d.startswith(month) and v is not None)
        actual = {'startDate':start,'endDate':end,'twoYearStartPct':float(a),'twoYearEndPct':float(b),'tenYearStartPct':float(c),'tenYearEndPct':float(d),'twoYearChangeBp':float((b-a)*100),'tenYearChangeBp':float((d-c)*100),'spreadStartBp':float((c-a)*100),'spreadEndBp':float((d-b)*100),'spreadChangeBp':float((d-b-c+a)*100),'broadUSDChangePct':float((lookup['DTWEXBGS'][usd[-1]]/lookup['DTWEXBGS'][usd[0]]-1)*100)}
        require(all(abs(row[k]-v)<1e-10 if isinstance(v,float) else row[k]==v for k,v in actual.items()), 'monthly financial statistic drift')
        require(row['dxy'] is None, 'broad USD cannot validate DXY')
        calculations.append({'month':month,**actual})
    all_source_hashes = []
    registry = {s['id']:s for s in allofficial+market['sources']}
    for reviewed_source in study['sources']:
        source=registry[reviewed_source['id']]
        path=resolve(source['localPath'],stage,root); pin(path)
        require(digest(path.read_bytes())==source['sha256']==reviewed_source['sha256'],'reviewed source raw SHA')
        all_source_hashes.append({'sourceId':source['id'],'sha256':source['sha256']})
    for sid,unit in (('DGS2-metadata','Percent'),('DGS10-metadata','Percent'),('DTWEXBGS-metadata','Index Jan 2006=100')):
        metadata_html=resolve(registry[sid]['localPath'],stage,root).read_text(encoding='utf-8-sig')
        require(sid.split('-')[0] in metadata_html and f'series-meta-value-units">{unit}</span>' in metadata_html,'archived FRED series identity/unit')
    boundaries=[]
    for sid,release,value in (('h10-20260831','August 31, 2026','118.7479'),('h10-20260908','September 8, 2026','118.5679')):
        html_text=resolve(registry[sid]['localPath'],stage,root).read_text(encoding='utf-8-sig')
        require('Release Date: '+release in html_text and 'JAN06=100' in html_text,'actual H10 publication date/unit')
        pos=html_text.find(value);require(pos>=0,'actual H10 broad USD endpoint')
        boundaries.append({'sourceId':sid,'publicationDate':datetime.strptime(release,'%B %d, %Y').date().isoformat(),'value':value,'rawHTMLStart':pos,'rawHTMLEndExclusive':pos+len(value),'sha256':text_digest(value),'strictHistoricalEligible':False})
    start,end=calculations[0]['startDate'],calculations[-1]['endDate']
    interval={'startDate':start,'endDate':end,'twoYearChangeBp':float((lookup['DGS2'][end]-lookup['DGS2'][start])*100),'tenYearChangeBp':float((lookup['DGS10'][end]-lookup['DGS10'][start])*100),'spreadChangeBp':float(((lookup['DGS10'][end]-lookup['DGS2'][end])-(lookup['DGS10'][start]-lookup['DGS2'][start]))*100),'broadUSDChangePct':float((lookup['DTWEXBGS'][end]/lookup['DTWEXBGS'][start]-1)*100)}
    require(all(abs(study['marketStatistics']['totalInterval'][k]-v)<1e-10 if isinstance(v,float) else study['marketStatistics']['totalInterval'][k]==v for k,v in interval.items()),'full interval statistic drift')
    treasury = next(s for s in market['sources'] if s['id']=='treasury-curve-2026')
    html=resolve(treasury['localPath'],stage,root).read_text(encoding='utf-8-sig')
    headers,treasury_rows=None,{}
    for rawrow in re.findall(r'<tr\b[^>]*>(.*?)</tr>',html,re.S|re.I):
        cells=[]
        for cell in re.findall(r'<t[hd]\b[^>]*>(.*?)</t[hd]>',rawrow,re.S|re.I):
            parser=OriginalHTML();parser.feed(cell)
            cells.append(re.sub(r'\s+',' ',''.join(parser.visible)).strip())
        if 'Date' in cells and '2 Yr' in cells and '10 Yr' in cells:
            headers=cells
        if headers and cells and re.fullmatch(r'\d\d/\d\d/\d{2,4}',cells[0]):
            day=datetime.strptime(cells[0],'%m/%d/%Y' if len(cells[0])==10 else '%m/%d/%y').date().isoformat()
            treasury_rows[day]={m:Decimal(cells[headers.index(m)]) for m in ('2 Yr','10 Yr')}
    require(headers is not None,'actual Treasury table identity/columns')
    comparisons=[]
    for row in calculations:
        for day in (row['startDate'],row['endDate']):
            for series,maturity in (('DGS2','2 Yr'),('DGS10','10 Yr')):
                difference=(treasury_rows[day][maturity]-lookup[series][day])*100
                require(difference==0,'same-date Treasury/FRED endpoint difference')
                comparisons.append({'date':day,'seriesId':series,'treasuryPct':float(treasury_rows[day][maturity]),'fredPct':float(lookup[series][day]),'differenceBp':float(difference)})
    require([s['id'] for s in study['marketAnalysis']['sections']] == THEME_IDS, 'five accepted theme anatomy')
    require([m['month'] for m in study['months']] == [f'2026-{m:02d}' for m in range(1,9)], 'eight-month range')
    ids = {o['id'] for o in private['opinions']}
    for chain in study['revisionChains']:
        require(set(chain['opinionIds']) <= ids, 'revision dangling opinion')
    return {'schemaVersion':'parent-independent-original-reader-1','checkedAt':datetime.now(timezone.utc).isoformat(),'method':'New parent implementation; no delegated validator imports; independently reread source bytes and every physical page with pypdf/PyMuPDF; original HTML, ordered paragraphs and exact codepoint hashes','parserVersions':{'pypdf':__import__('pypdf').__version__,'pymupdf':pymupdf.VersionBind},'counts':{'selectedSources':len(sources),'opinionsChecked':len(opinions),'opinionsAccepted':sum(o['accepted'] for o in opinions),'physicalPages':sum(len(s['pages']) for s in sources),'months':len(study['months']),'revisionChains':len(study['revisionChains']),'officialFactsChecked':len(fact_checks),'officialFactsAccepted':sum(f['accepted'] for f in fact_checks),'originalOfficialFiles':sum(not s['sourceId'].startswith('increment-') for s in official_checks),'newOfficialSnapshots':sum(s['sourceId'].startswith('increment-') for s in official_checks)},'h10PublicationBoundaryVerified':True,'h10PublicationBoundaries':boundaries,'intervalRecomputed':interval,'allResearchSourceHashCount':len(all_source_hashes),'researchSourceHashes':all_source_hashes,'treasuryFredComparisons':len(comparisons),'maximumTreasuryDifferenceBp':max(abs(c['differenceBp']) for c in comparisons),'treasuryComparisons':comparisons,'sources':sources,'opinions':opinions,'officialSources':official_checks,'officialFacts':fact_checks,'marketRecomputed':calculations,'inputPins':pins,'failures':failures}
