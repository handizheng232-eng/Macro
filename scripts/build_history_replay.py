"""Build one scoped replay from archived source evidence and checked local reports.

No credential access and no online calls. Preserve public/source artifacts separately.
"""
import json
import re
import hashlib
from datetime import datetime
from pathlib import Path
from replay_monthly_coverage import build_monthly_coverage, load_monthly_audits
from replay_public_export import public_snapshot
from replay_reviewed_analysis import reviewed_analysis

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '美国宏观复盘/降息起步后的双向政策时代/2026-09_至今'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def star_filename_date(filename):
    """Parse a complete terminal date token; never repair malformed identifiers."""
    match = re.search(r'(?<!\d)(20\d{6}|\d{6})(?:_原文|_纪要)?\.pdf$', filename, re.IGNORECASE)
    if not match:
        return None
    token = match.group(1)
    try:
        return datetime.strptime(token if len(token) == 8 else '20' + token, '%Y%m%d').date().isoformat()
    except ValueError:
        return None


def build():
    public = load(STAGE / '资料/公开来源/public-evidence.json')
    manifest = load(STAGE / '核验/长江宏观/manifest.json')
    local = load(STAGE / '核验/长江宏观/页面结论.json')
    wind = load(STAGE / '资料/Wind新闻/manifest.json')
    zsxq_path = STAGE / '报告/知识星球/manifest.json'
    zsxq = load(zsxq_path) if zsxq_path.exists() else None
    zsxq_status = (f'PDF已归档·{zsxq.get("verifiedPdfCount", 0)}份' if zsxq and zsxq.get('status') == 'download_complete'
                  else '检索完成·PDF保存待核验' if zsxq and zsxq.get('status') == 'search_complete_download_unverified'
                  else '自动检索受阻' if zsxq and zsxq.get('status') == 'blocked'
                  else '自动下载链路待核验')
    zsxq_detail = (zsxq.get('reason', '渠道状态未提供说明。') if zsxq
                  else '只有实际检索和PDF核验通过后才标记完成；不将未知匹配数量写为0。')
    events_by_id = {e['id']: e for e in public['events']}
    descriptions = {
        1: ('FOMC会议日历', 'Federal Reserve', '2026-10-01', '动态官方日历；不是会前市场预期来源。'),
        2: ('9月FOMC官方声明', 'Federal Reserve', '2026-09-16', '美国东部时间14:00发布；北京时间9月17日凌晨。全票12–0加息25bp至3.75%–4.00%。'),
        3: ('9月SEP经济预测摘要', 'Federal Reserve', '2026-09-16', '年末政策中点、Q4/Q4通胀与GDP、Q4平均失业率口径不同；官方条件预测不是现实或承诺。'),
        4: ('9月FOMC记者会全文', 'Federal Reserve', '2026-09-16', '日期指讲话发生日。当前FINAL文稿于9月24日生成/修改，首次上网日未知；只用于当前追溯，不倒填9月16日或其他历史信息截面。'),
        5: ('8月个人收入与支出/PCE', 'BEA', '2026-09-30', '观测期8月；本次含2021年起年度修订，不将最新值回填会前信息集。'),
        6: ('二季度GDP第三次估计及年度更新', 'BEA', '2026-09-30', 'GDP环比折年率与私人国内最终销售；这是统计修订，不是9月增长或预测误差。'),
        7: ('二季度GDP第二次估计', 'BEA', '2026-08-26', '区间前背景：GDP环比折年1.5%的旧版本。'),
        8: ('H.15美债收益率', 'Federal Reserve', '2026-09-30', '仅归档9月23–29日5个交易日的恒定期限名义收益率，单位%。不代表全月。'),
        9: ('H.10广义贸易加权美元', 'Federal Reserve', '2026-09-28', '仅9月21–25日5日快照；2006年1月=100，不是ICE DXY。'),
        10: ('8月就业官方发布（搜索摘录）', 'BLS', '2026-09-04', '官方全文访问403，仅取得官方URL搜索摘录；与长江9月5日报告交叉核对。'),
        11: ('8月CPI官方发布（搜索摘录）', 'BLS', '2026-09-11', '官方全文访问403，仅取得官方URL搜索摘录；与长江9月12日报告交叉核对。'),
    }
    sources = []
    for s in public['sources']:
        title, publisher, date, note = descriptions[s['source_id']]
        sources.append({'id': f'public-{s["source_id"]}', 'title': title, 'publisher': publisher, 'date': date, 'url': s['url'], 'kind': '官方搜索摘录' if s.get('fulltext_status') else '官方一手', 'status': '摘录核验·非全文' if s.get('fulltext_status') else '全文已归档', 'note': note})
        if s['source_id'] == 4:
            sources[-1].update({'historicalAsOfEligible': False,
                                'dateBasis': '讲话发生日；FINAL版9月24日生成，首次发布时间未核实'})
    selected = sorted((r for r in manifest['records'] if r['classification'] == 'interval_us'), key=lambda r: r['publication_date'])
    reports = []
    for i, (r, findings) in enumerate(zip(selected, local['reports']), 1):
        assert r['publication_date'] == findings['publicationDate']
        sid = f'changjiang-{i}'
        sources.append({'id': sid, 'title': findings['title'], 'publisher': '长江证券', 'date': r['publication_date'], 'url': '', 'kind': '授权研报', 'status': '正文日期/复制散列已核验', 'note': f'正文日期证据第{findings["dateEvidencePage"]}页；观点定位第'+ '、'.join(map(str, findings['pages']))+'页。研究观点不等于官方归因。'})
        reports.append({'title': findings['title'], 'date': r['publication_date'], 'provider': '长江证券', 'path': Path(r['archive_path']).relative_to(ROOT).as_posix(), 'scope': '区间内·美国宏观', 'note': findings['keyFinding'] + f'（PDF第{"、".join(map(str, findings["pages"]))}页）'})
    bg = load(STAGE / '核验/长江宏观/证据摘记.json')['background_only'][0]
    sources.append({'id': 'changjiang-background', 'title': local['backgroundOnly'][0]['title'], 'publisher': '长江证券', 'date': bg['publication_date'], 'url': '', 'kind': '区间前背景', 'status': '正文日期/复制散列已核验', 'note': '8月29日研究观点仅作起点背景，不计入区间内5篇。'})
    reports.append({'title': local['backgroundOnly'][0]['title'], 'date': bg['publication_date'], 'provider': '长江证券', 'path': Path(bg['background_archive_path']).relative_to(ROOT).as_posix(), 'scope': '区间前背景·不计入区间报告', 'note': local['backgroundOnly'][0]['keyFinding']})
    for i, item in enumerate(wind['items'], 1):
        sources.append({'id': f'wind-{i}', 'title': item['title'], 'publisher': 'Wind新闻/原文发布者', 'date': item['date'], 'url': item['url'], 'kind': '新闻二手转述', 'status': '已获取正文·非研报PDF', 'note': '相关性top5检索并非完整全集。预期需标明被转述者；概率/盘中行情未获原始盘口核验，不作为一手量化证据。'})
    news_start_id = next(f'wind-{i}' for i, item in enumerate(wind['items'], 1) if item['date'] == '2026-09-01')
    news_late_id = next(f'wind-{i}' for i, item in enumerate(wind['items'], 1) if item['date'] == '2026-09-24' and 'LSEG' in item['content'])
    news22_id = next(f'wind-{i}' for i, item in enumerate(wind['items'], 1) if item['date'] == '2026-09-22')

    def event(eid, expectation, expectation_ids, reality, reality_ids, interpretation, market='完整事件窗口价格与隐含政策路径缺失，暂不做量化归因。'):
        e = events_by_id[eid]
        return {'id': eid, 'date': e['release_date'], 'title': e['title'], 'observationPeriod': e['observation_period'], 'expectation': expectation, 'expectationSourceIds': expectation_ids, 'reality': reality, 'realitySourceIds': reality_ids, 'interpretation': interpretation, 'marketResponse': market, 'confidence': '官方全文' if 'fulltext' in e['verification_status'] else '官方搜索摘录·待补全文'}

    replay_events = [
        event('august-nonfarm', '未取得9月4日发布前的预测原始快照；9月5日报告事后引用的5.5万共识不冒充本页已核验的事前盘口。', [], '8月新增非农16.2万人、失业率4.1%。BLS仅取得官方搜索摘录，前月修订与完整行业表待补原文。', ['public-10'], '就业改善降低即时衰退担忧，但总量改善、供给收缩与需求全面过热不是同一个命题。9月5日长江报告指出新增就业集中于休闲酒店和地方教育、季调影响不可忽略；这是事后结构解读，不应倒填9月4日事前判断。'),
        event('august-cpi', '长江证券9月5日报告第2页，在CPI发布前引用的市场一致预期为：8月总CPI同比3.4%、核心同比2.4%；这是可追溯研报转述，并非原始调查快照。该报告认为即便数据落地，政策分歧未必消除。', ['changjiang-2'], '8月总CPI同比3.4%、环比0.4%；核心同比2.4%、环比0.3%。官方搜索摘录核验，完整分项表待补。此前研报引用的两个同比预测与公布值相符。', ['public-11'], '核心同比放缓与当月核心环比抬升可以并存；总同比持平，不笼统称通胀同比全面放缓。9月12日长江报告将部分环比上行归于酒店/无线电话等扰动，主张短期偏鹰、持续加息仍取决于扩散；这是机构判断，不是官方既定归因。'),
        event('fomc-statement', '预期并非单一共识：9月1日Wind新闻转述高盛倾向年内维持3.50%–3.75%；9月12日长江报告第2页则认为9月加息25bp较优，但持续加息必要性有限。前者是二手转述，后者为已归档研报。', [news_start_id, 'changjiang-3'], '9月16日14:00 EDT（北京时间9月17日凌晨），FOMC以12–0加息25bp至3.75%–4.00%，并维持充裕准备金框架。官方称支出有韧性、生产率和资本投资强，通胀仍偏高。', ['public-2'], '9月加息验证了9月12日偏鹰方向判断，否定了“年内始终不加不降”的路径；但一次方向验证不等于未来累计幅度已确认。未取得会前原始概率，不称超预期加息。'),
        event('sep', '', [], '9月SEP对2026年预测中位数：GDP 2.3%（Q4/Q4）、失业率4.1%（Q4均值）、PCE 3.7%、核心PCE 3.4%（Q4/Q4）、年末政策利率中点4.1%。同表回列6月值分别为2.2%、4.3%、3.6%、3.3%、3.8%；2027年政策中点由3.6%上调至4.1%。', ['public-3'], '这是条件预测分布上移而非已实现增长/通胀。6月数值来自9月表回列，不能在9月16日前截面伪装成已独立归档的6月原版；年底结果仍待兑现。主席未提交个人预测，不把点阵图当承诺。'),
        event('press-conference', '', [], '主席强调趋势而非单点、撤除部分宽松、不预判未来决定；记者会第2页估计8月总PCE同比约3.6%，核心PCE近况约3.2%。该估计早于9月30日BEA发布，构成后续可检验预期。', ['public-4'], '把政策反应函数和未来路径区分：反通胀约束明确，不代表加息次数或时间被承诺。记者提问中的市场概率不替代原始期货报价。'),
        {'id': 'labor-supply', 'date': '2026-09-21', 'title': '劳动参与率：需求叙事的供给侧校验', 'observationPeriod': '2026年初以来，研究估算', 'expectation': '', 'expectationSourceIds': [], 'reality': '长江9月21日报告第2、5–8页将劳动参与率下行拆为技术调整、老龄化、移民驱逐和就业信心等因素。这是报告估算，不是官方无误差分解。', 'realitySourceIds': ['changjiang-5'], 'interpretation': '较低失业率可能同时受供给收缩影响，不能单独推出需求过热。工资、工时、行业广度与招聘指标须联合校验。', 'marketResponse': '该材料是机制研究，不构造发布日期市场因果效应。', 'confidence': '授权研报·估算归因'},
        {'id': 'next-hike-pricing', 'date': '2026-09-24', 'title': '加息后：分歧转向下一次行动的时点', 'observationPeriod': '9月22–24日新闻中的市场路径转述', 'expectation': 'Wind 9月22日简报转述摩根士丹利与KKR押注12月及次年3月进一步加息；这是具名机构预测，不是已兑现政策。', 'expectationSourceIds': [news22_id], 'reality': '9月24日Wind新闻转述，官员偏鹰讲话后货币市场对10月再加息的押注抬升。LSEG原始盘口/采样时点未归档，本页不把文中概率或盘中价当已核验序列。', 'realitySourceIds': [news_late_id], 'interpretation': '会议后争论由是否反转，转到加息节奏、终点和持久性；新闻可显示叙事变化，不能替代政策期货隐含路径。', 'marketResponse': '二手新闻定性描述；量化概率与日内收益率仍待一手验证。', 'confidence': '新闻二手转述'},
        event('usd-broad', '', [], '美联储H.10广义名义美元指数（2006年1月=100，非DXY）：9/21 119.4014；9/22 119.5933；9/23 120.1169；9/24 120.5521；9/25 120.3300。发布日9月28日，只覆盖5日。', ['public-9'], '局部美元快照可用于观察金融条件，不能证明9月全月涨跌；广义贸易加权美元与ICE DXY不可互换。'),
        event('treasury-yields', '', [], 'H.15恒定期限名义美债收益率，单位%：9/23 2Y 4.85 / 10Y 5.11；9/24 4.87 / 5.18；9/25 4.81 / 5.17；9/28 4.92 / 5.24；9/29 4.89 / 5.26。数据发布于9月30日，仅局部快照。', ['public-8'], '政策利率、预期短率路径和期限溢价不能混为一谈。长江9月3日报告强调期限溢价/融资分流，但本页没有独立分解模型，不能据此断定长端变化全部由期限溢价贡献。'),
        event('august-pce', '9月16日主席在记者会第2页明确估计：8月总PCE同比约3.6%。核心PCE近况约3.2%的措辞未再次明确8月，故不当作严格同观测期预测。不是市场一致预期。', ['public-4'], '9月30日BEA公布8月PCE：总同比3.4%、核心同比3.0%；环比分别0.3%、0.2%；实际消费环比+0.6%、实际可支配收入持平、储蓄率4.1%。总PCE较主席先前估计低0.2个百分点；本次含年度修订，误差不全等于经济意外。', ['public-5'], '通胀信息比主席此前总PCE估计温和，但实际消费仍有韧性；“更温和的通胀”与“较强需求”并存，下一次政策时点需再评估。不能把9月30日公布值反向用于解释9月16日决定。'),
        event('q2-gdp', '8月26日BEA第二次估计：二季度GDP环比折年1.5%，私人国内最终销售4.2%。这是旧统计版本，不是预测。', ['public-7'], '9月30日第三次估计将二季度GDP环比折年上修至2.2%（+0.7个百分点），私人国内最终销售上修至4.6%；一季度修订后2.5%。三季度GDP仍未公布。', ['public-6'], '月底可见增长图景更强，但这是二季度版本修订，不是“9月增长2.2%”，也不是“预测误差0.7个百分点”。实时回放保留旧版与新版。'),
    ]
    ids = {s['id'] for s in sources}
    for e in replay_events:
        assert set(e['expectationSourceIds'] + e['realitySourceIds']) <= ids
        assert '2026-09-01' <= e['date'] <= '2026-10-01'
        assert all(next(s['date'] for s in sources if s['id'] == i) < e['date'] for i in e['expectationSourceIds'])
    # Bibliographic acquisition dates do not manufacture publication dates.
    bibliography = load(STAGE / '研究/zsxq-bibliography.json')
    evidence = load(STAGE / '研究/zsxq-expectation-evidence.json')
    supplement = load(STAGE / '研究/changjiang-supplement-bibliography.json')
    market_paths = load(STAGE / '研究/market-paths.json')
    wechat = load(STAGE / '资料/微信公众号/manifest.json')
    book_by_id = {r['id']: r for r in bibliography['items']}
    star_dates = {}
    for item in bibliography['items']:
        report_path = (STAGE / item['path']).relative_to(ROOT).as_posix()
        assert (ROOT / report_path).is_file()
        filename_date = star_filename_date(Path(report_path).name)
        star_dates[item['id']] = filename_date
        conflict = bool(filename_date and item['postDate'] and filename_date != item['postDate'])
        basis = ('filename_date_user_preferred · 按用户指定的文件名日期归档，平台日仅备查；正文发布日期和历史首次可得时间未确认'
                 if filename_date else 'filename_date_unresolved · 文件名日期标记不符合完整有效日期格式，不擅自修正；平台日仅备查')
        reports.append({'id': item['id'], 'title': item['title'], 'date': filename_date,
                        'filenameDate': filename_date, 'publicationDate': item['publicationDate'],
                        'dateConflict': conflict, 'historicalAsOfEligible': False,
                        'postDate': item['postDate'], 'dateBasis': basis,
                        'provider': item['provider'] or '机构未确认', 'path': report_path,
                        'scope': ('区间前背景·文件名日期·' if filename_date and filename_date < '2026-09-01'
                                  else '区间内·文件名日期·' if filename_date else '日期待核·') + item['geography'],
                        'topics': item['topics'],
                        'note': item['note'] + (' 文件名与平台日有冲突，采用文件名日。' if conflict else '')
                                + ' 文件名日期用于本研究归档，不冒充已核正文发布日期；首次可得时间未确认，不进入严格历史信息截面。'})
    for item in supplement['items']:
        assert (ROOT / item['path']).is_file()
        reports.append({**item, 'scope': '区间内·背景关联·' + item['scope']})
    examined_events = {e['id']: e for e in evidence['events']}
    reality_by_id = {e['id']: e for e in replay_events}
    research_evidence = []
    for item in evidence['items']:
        report = book_by_id[item['reportId']]
        reality = reality_by_id.get(item['eventId'])
        examined = examined_events.get(item['eventId'], {})
        filename_date = star_dates[item['reportId']]
        limitations = item['limitations']
        if item['reportId'] == 'zsxq-121':
            limitations = limitations.replace('不能把后者当正文日期。', '本研究按用户指定采用文件名2026-08-31归档；这不等同于核验正文发布日期或首次可得时间。')
        if item['reportId'] == 'zsxq-048':
            limitations = limitations.replace('文件名260919不能覆盖该日期', '按用户指定以文件名260919，即2026-09-19归档；平台2026-09-20保留备查，不将归档日冒充核验的正文发表日')
        research_evidence.append({**item, 'reportTitle': report['title'],
                                 'expressedAt': filename_date, 'platformExpressedAt': item['expressedAt'],
                                 'dateBasis': 'filename_date_user_preferred · 按文件名日期优先归档；原平台日期仅备查，正文发表日及首次可得时间未独立确认。' if filename_date else 'filename_date_unresolved · 文件名日期标记异常，观点日期待核；不自动以平台日补齐。',
                                 'limitations': limitations,
                                 'localPath': (STAGE / report['path']).relative_to(ROOT).as_posix(),
                                 'eventDate': examined.get('date'),
                                 'reality': reality['reality'] if reality else '截止日尚无经核验的对应现实；不预填后续结果。',
                                 'status': '现实已落地·发表时间待核' if reality else '待后续验证或官方原文核验'})
    for window in market_paths['eventWindows']:
        matching = reality_by_id.get(window['eventId'])
        if matching:
            values = []
            for key, label in [('treasury2yChangeBp', '2Y'), ('treasury10yChangeBp', '10Y')]:
                if window.get(key) is not None:
                    values.append(f'{label} {window[key]:+.2f}bp')
            if window.get('broadUsdPercentChange') is not None:
                values.append(f'广义美元 {window["broadUsdPercentChange"]:+.3f}%（非DXY）')
            matching['marketResponse'] = (f'当前官方快照追溯：{window["fromObservationDate"]} → {window["toObservationDate"]}；'
                                         + '；'.join(values) + '。日终近似窗口，不是瞬时冲击或因果归因；美债首次发布日期未确认，历史截面不可用。')
    wind_reports_path = STAGE / '报告/Wind/manifest.json'
    wind_reports = load(wind_reports_path) if wind_reports_path.exists() else None
    if wind_reports:
        for item in wind_reports.get('reports', wind_reports.get('items', [])):
            if item.get('path'):
                report_path = Path(item['path'])
                if not report_path.is_absolute():
                    report_path = STAGE / report_path
                report_path = report_path.relative_to(ROOT).as_posix()
                assert (ROOT / report_path).is_file()
                printed_date = item.get('verified_publication_date')
                day_date = printed_date if item.get('date_precision') == 'day' and re.fullmatch(r'\d{4}-\d{2}-\d{2}', printed_date or '') else None
                relevance = item.get('title_body_relevance', '')
                scope = ('区间内·中美贸易/地缘背景·非美元汇率专题' if 'trade/geopolitics background' in relevance
                         else '区间内·美国货币政策/全球宏观')
                if item.get('scope'):
                    scope = '区间内·' + item['scope']
                if not day_date:
                    scope = '刊期关联·期刊论文·正文日未确认'
                topics = list(item.get('themes_verified', [])) + [theme['keyword'] + '（检索归属）' for theme in wind_reports.get('themes', [])
                          if any(Path(p).name == Path(report_path).name for p in theme.get('direct_saved_paths', []))]
                reports.append({'id': 'wind-pdf-' + item['sha256'][:16], 'title': item['title'],
                                'date': day_date, 'dateBasis': ('封面正文日期·文本及截图复核' if day_date
                                     else f'仅确认刊期{item.get("verified_publication_month") or printed_date or "未知"}；文件名日期不当正文发布日期'),
                                'provider': item.get('institution', '机构未确认') + ' · Wind',
                                'path': report_path, 'scope': scope, 'topics': topics,
                                'note': f'正常终端下载PDF，{item["pages"]}页；检索归属不等于该主题实质覆盖。'
                                        + (f'低文本页面{item["empty_text_pages"]}未OCR，图表解析不完整。' if item.get('empty_text_pages') else '文本层已逐页提取，未声称图表全部解析。')})
    wind_evidence_path = STAGE / '研究/wind-expectation-evidence.json'
    wind_evidence = load(wind_evidence_path)['items'] if wind_evidence_path.exists() else []
    market_analysis = reviewed_analysis(STAGE, load(STAGE / '研究/market-analysis.json'))
    sources.extend(market_analysis.pop('additionalSources', []))
    wechat_bibliography_path = STAGE / '研究/wechat-bibliography.json'
    wechat_evidence_path = STAGE / '研究/wechat-expectation-evidence.json'
    wechat_access_path = STAGE / '资料/微信公众号/正常访问补充.json'
    wechat_bibliography = load(wechat_bibliography_path)['items'] if wechat_bibliography_path.exists() else []
    wechat_evidence = load(wechat_evidence_path)['items'] if wechat_evidence_path.exists() else []
    for filename, destination in [('wechat-expanded-bibliography.json', wechat_bibliography),
                                  ('wechat-expanded-expectation-evidence.json', wechat_evidence)]:
        expanded_path = STAGE / '研究' / filename
        if expanded_path.exists():
            destination.extend(load(expanded_path)['items'])
    wechat_access = load(wechat_access_path) if wechat_access_path.exists() else {}
    wechat_by_id = {}
    for item in wechat_bibliography:
        assert re.fullmatch(r'wechat-[0-9a-f]{16}', item['id'])
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', item['date']) and '2026-09-01' <= item['date'] <= '2026-10-01'
        assert item['id'] not in wechat_by_id
        assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256']
        wechat_by_id[item['id']] = item
        reports.append({**item, 'scope': '区间内·微信公众号原文·' + item['scope'],
                        'historicalAsOfEligible': False,
                        'dateBasis': item['dateBasis'] + '；当前读取版本不等于历史逐版存档。'})
        sources.append({'id': item['id'], 'title': item['title'], 'publisher': item['provider'],
                        'date': item['date'], 'url': '', 'kind': '微信公众号原文',
                        'status': '官方页头/文字正文已核验·非含图全文', 'note': item['note'],
                        'historicalAsOfEligible': False, 'dateBasis': item['dateBasis']})
    for item in wechat_evidence:
        report = wechat_by_id[item['reportId']]
        assert item['expressedAt'] == report['date']
        assert item['localPath'] == report['path'] and item['reportTitle'] == report['title']
        assert not item.get('sourceUrl')  # No transient signed/session URLs in the public artifact.
        paragraphs = load((ROOT / report['path']).with_suffix('.paragraphs.json'))['paragraphs']
        paragraphs_by_id = {p['paragraph']: p['text'] for p in paragraphs}
        assert all(p in paragraphs_by_id for p in item['pages'])
        assert item['evidenceExcerpt'] in ''.join(paragraphs_by_id[p] for p in item['pages'])
        if item['eventId']:
            event = reality_by_id[item['eventId']]
            assert item['eventDate'] == event['date'] and item['eventDate'] > item['expressedAt']
            assert item['reality'] == event['reality']
        else:
            assert item['eventDate'] is None and item['reality'] is None
    for report_id in wechat_by_id:
        assert sum(len(i['evidenceExcerpt']) for i in wechat_evidence if i['reportId'] == report_id) <= 25
    coverage_path = STAGE / '核验/微信公众号/扩展来源检索.json'
    coverage_audit = load(coverage_path) if coverage_path.exists() else {'items': []}
    actual_accounts = {}
    for item in wechat_bibliography:
        account = item.get('accountActual') or item['provider'].removesuffix(' · 微信公众号')
        actual_accounts[account] = actual_accounts.get(account, 0) + 1
    requested_accounts = []
    for row in coverage_audit['items']:
        assert row['bodyObtainedCount'] == actual_accounts.get(row['accountRequested'], 0)
        requested_accounts.append({key: row[key] for key in
                                   ('accountRequested', 'officialIdentityChecked', 'bodyObtainedCount',
                                    'status', 'limitations')})
    wechat_coverage = {
        'requestedAccounts': requested_accounts,
        'actualAccounts': [{'accountActual': account, 'articleCount': count}
                           for account, count in actual_accounts.items()],
        'totalArticles': len(wechat_bibliography), 'totalOpinions': len(wechat_evidence),
        'limitations': [
            '检索池开放扩展，候选名称与实际发布账号分别记录；中金点睛不强配为中金宏观。未取得正文不等于没有相关文章，检索不是穷尽归档。',
            '首席经济学家论坛是分发渠道，非独立研究机构；其文章按华创张瑜、华福陈兴/陈琦归属。同一研究跨渠道传播不增加独立证据数量。',
            '正文为2026-10-02当前可读文字版本，图片未OCR；研究仍截至2026-10-01。当前版本不能证明历史未编辑，严格历史模式隐藏本轮覆盖及观点。',
        ],
    }
    wind_by_id = {'wind-pdf-' + r['sha256'][:16]: r for r in wind_reports['reports']} if wind_reports else {}
    for item in wind_evidence:
        report = wind_by_id[item['reportId']]
        assert item['sha256'] == report['sha256']
        assert item['expressedAt'] == report['verified_publication_date']
        assert (ROOT / item['localPath']).resolve() == Path(report['path']).resolve()
        assert all(1 <= page <= report['pages'] for page in item['pages'])
        assert not item['eventId'] or item['eventId'] in reality_by_id
        assert set(item['realitySourceIds']) <= ids
        assert not item['eventDate'] or item['eventDate'] > item['expressedAt']
    data = {
        'title': '重启加息：政策反转', 'startDate': '2026-09-01', 'asOf': '2026-10-01',
        'summary': [
            '主线：就业改善与通胀约束 → 9月加息落地 → 分歧转向加息节奏与终点 → 月末PCE/GDP新信息重新校准政策路径。开放时期仍未形成终点。',
            '预期不是单一共识：月初新闻转述的按兵不动、9月12日研报的短鹰长鸽、9月16日SEP的利率路径上移必须按主体和发布时间分开。已验证一次加息，不宣称持续紧缩已获确认。',
            '明确可检验的收敛链：主席9月16日估计8月总PCE同比约3.6%，BEA9月30日公布3.4%，差为−0.2个百分点。这不是市场共识误差，且包含年度修订影响。',
            '当前官方快照已补入9月21个交易日的2Y/10Y美债收益率、18日广义美元指数及事件窗口对照。观测日不冒充首次发布日期，缺失不补值；CME历史隐含概率、ICE DXY与事件瞬时冲击仍缺，日终变动不作因果收益。',
        ],
        'sources': sources, 'events': replay_events,
        'researchEvidence': research_evidence, 'windResearchEvidence': wind_evidence, 'marketPaths': market_paths,
        'marketAnalysis': market_analysis,
        'wechatResearchEvidence': wechat_evidence,
        'wechatCoverage': wechat_coverage,
        'hypotheses': [
            {'title': '宽松回撤，而非已确认的持续紧缩周期', 'test': '追踪核心PCE短期年化、通胀扩散、实际消费、薪资及下一次FOMC行动。一次加息与累计幅度分开。', 'invalidator': '若核心通胀连续广泛加速、预期抬升且多次加息落地，则“有限回撤”解释失效；若增长就业快速失速，路径也需重估。', 'status': '进行中·开放工作假说'},
            {'title': '总量就业改善不等于需求全面过热', 'test': '联查行业就业广度、季调前后、参与率、工时、时薪与职位空缺；区分需求改善和供给收缩。', 'invalidator': '若就业广度、工资及招聘持续同步走强，需提高需求过热权重；反之总量改善可能不可持续。', 'status': '需持续数据验证'},
            {'title': '长端与美元不能仅沿加息单轴解释', 'test': '比较预期短率、实际收益率、盈亏平衡通胀、期限溢价、相对增长与资金配置；补齐会前和会后价格序列。', 'invalidator': '若跨源分解显示长端变化主要由预期短率推动，应削弱期限溢价叙事；美元反向需检查风险偏好与其他央行。', 'status': '机制待检验·不作量化归因'},
        ],
        'acquisition': [
            {'provider': '长江宏观本地PDF', 'status': '完成·美国与背景分层', 'detail': f'扫描210份/2824页；区间美国专题5份、另补{len(supplement["items"])}份国内/全球背景、区间前背景1份。文件名2026-09-28是下载批次，不当发布日期；国内材料不冒充美国直接证据。'},
            {'provider': '公开官方资料', 'status': '完成但有缺口', 'detail': 'FOMC/SEP/记者会/BEA/H.15/H.10有原文；BLS全文403，仅官方搜索摘录。当前公开来源证据9个事件、11个来源。'},
            {'provider': '知识星球·默认六主题', 'status': zsxq_status, 'detail': zsxq_detail + f' 当前按用户指定优先使用文件名日期：{sum(d is not None for d in star_dates.values())}份完整有效日期，{sum(r.get("dateConflict", False) for r in reports)}份与平台日冲突；异常标记不修补。首次可得时间未核，仍不纳入严格历史信息截面。'},
            {'provider': 'Wind', 'status': ('已保存样本·非全量' if wind_reports.get('full_collection_complete') else '部分PDF已归档·六主题未全量') if wind_reports else '正常终端下载已打通·批次核验中',
             'detail': (f'已核验{wind_reports["unique_saved_pdf_count"]}个PDF/{wind_reports["total_pdf_pages"]}页；'
                        + '；'.join(f'{t["keyword"]}：候选{t["candidate_count"]} / 直存{t["direct_saved_pdf_count"]}' for t in wind_reports['themes'])
                        + '。' + '；'.join(f'{t["keyword"]}：正文实质样本{t["substantive_verified_pdf_count"]}' for t in wind_reports['themes'])
                        + '。非全量采集；候选可能含非PDF且集合重叠，不相加；直存按产生下载包的检索主题归属，不等于实质覆盖。'
                        + wind_reports['summary'] + ' 数据来源于万得Wind金融数据服务。') if wind_reports
                       else f'正常研报平台已有首批2份PDF落盘，六主题检索与解析仍在进行；另有{len(wind["items"])}条top5新闻，新闻不计作报告。数据来源于万得Wind金融数据服务。'},
            {'provider': '微信公众号', 'status': '多来源官方文字正文已补充·有限样本' if wechat_bibliography else '原文链接已定位·正文访问受阻',
             'detail': (f'用户正常认证的活跃会话读取并保存{len(wechat_bibliography)}篇官方公众号文字正文，形成{len(wechat_evidence)}条具名观点；页头日期、作者、逐段引用和SHA256已核验。'
                        + '实际发布账号：' + '、'.join(f'{account}{count}篇' for account, count in actual_accounts.items()) + '。'
                        + f'本轮逐项检索{len(requested_accounts)}个候选公众号，未取得候选自身正文不等于没有相关文章；中金相关材料按实际发布账号中金点睛记录。论坛分发非独立研究机构。'
                        + f'原清单其余{wechat_access.get("counts", {}).get("other_manifest_articles_not_read_this_pass", "待核")}篇本轮未读取；未OCR图内文字，不宣称含图全文或全量采集。'
                        + '本次采集于2026-10-02，研究仍截至2026-10-01；当前页面版本不证明历史正文未编辑。同篇长江研究跨PDF与公众号收录不作为两个独立观点。'
                        + '旧manifest仅保留此前访问失败记录，当前成功状态以正常访问补充清单为准；未提取凭据或保存临时签名链接。') if wechat_bibliography
                       else f'核对{wechat["counts"]["wechat_articles_checked"]}篇，定位{wechat["counts"]["wechat_original_url_discovered"]}条公开原文链接，实际正文保存{wechat["counts"]["wechat_original_bodies_saved"]}篇。正常访问返回环境异常/验证码；不绕过，不将本地PDF或第三方摘要冒充微信原文。'},
        ], 'reports': reports,
    }
    data['monthlyCoverage'] = build_monthly_coverage(data['startDate'], data['asOf'], reports, ROOT, STAGE,
                                                    load_monthly_audits(STAGE))
    return data


if __name__ == '__main__':
    data = build()
    target = ROOT / 'src/data/historyReplay.json'
    target.write_text(json.dumps(public_snapshot(data, ROOT), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    study = STAGE / '研究'
    study.mkdir(parents=True, exist_ok=True)
    (study / 'replay-data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'events': len(data['events']), 'sources': len(data['sources']), 'interval_reports': sum(r['scope'].startswith('区间内') for r in data['reports']), 'background_reports': sum(r['scope'].startswith('区间前') for r in data['reports']), 'asOf': data['asOf'], 'target': str(target)}, ensure_ascii=False))
