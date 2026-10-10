import { useState } from 'react'
import replayData from './data/historyReplay.json'
import { US_MACRO_PAGES } from './usMacroConfig'
import { formatReplayDate, formatReplayText } from './replayDateFormat'
import './historyReplay.css'

export interface ReplaySource {
  id: string; title: string; publisher: string; date: string; url: string; kind: string; status: string; note: string
  historicalAsOfEligible?: boolean; dateBasis?: string; retrospectiveOnly?: boolean
  firstAvailableDate?: string | null; availableFrom?: string | null
}
export interface ReplayEvent {
  id: string; date: string; title: string; observationPeriod: string
  availableFrom?: string; historicalAsOfEligible?: boolean
  expectation: string; expectationSourceIds: string[]; reality: string; realitySourceIds: string[]
  interpretation: string; marketResponse: string; confidence: string
}
export interface ReplayReport {
  id?: string; title: string; date?: string | null; publicationDate?: string | null
  postDate?: string | null; dateBasis?: string; provider: string; path: string
  filenameDate?: string | null; dateConflict?: boolean; historicalAsOfEligible?: boolean
  firstAvailableDate?: string | null; availableFrom?: string | null
  scope?: string; note?: string; geography?: string; topics?: string[]
  accountActual?: string; authors?: string[] | string; researchOrigin?: string; distributionType?: string
}
export interface ReplayResearchEvidence {
  id?: string
  reportId: string; eventId?: string | null; expressedAt: string | null; dateBasis: string
  actor: string; claim: string; scope: string; value?: number | string | Record<string, unknown> | unknown[] | null; unit?: string | null
  observationPeriod?: string | null; pages: (string | number)[]; evidenceExcerpt: string | null
  limitations?: string[] | string; reportTitle?: string; localPath?: string
  reality?: string | null; eventDate?: string | null; status?: string
  claimType?: string; firstAvailableDate?: string | null; historicalAsOfEligible?: boolean
  conditions?: unknown; forecastHorizon?: { literalResearchWindow?: string; effectiveDeadline?: string | null; deadlineMonth?: string; start?: string | null; end?: string | null; basis?: string }
  realitySourceIds?: string[]
}
export interface ReplayMarketObservation {
  date: string; value: number | null; releaseDate: string | null; historicalAsOfEligible: boolean
  missingReason?: string | null; availableBy?: string | null
  observationPeriod?: string; datePrecision?: string; dateRole?: string; isPrehistory?: boolean
}
export interface ReplayMarketSeries {
  id: string; title: string; unit: string; sourceUrl: string; observations: ReplayMarketObservation[]
  status: string; limitations: string[] | string; derivedIntervalChange?: unknown
  frequency?: string | null; sourceGeneratedAt?: string | null
  sourceMetadata?: { provider?: string | null; institution?: string | null; code?: string | null; name?: string | null; rawUnit?: string | null; sourceUpdateDate?: string | null; updateDate?: string | null; inheritedTransformation?: string | null }
}
export interface ReplayMarketPaths {
  series: ReplayMarketSeries[]; sources?: unknown; eventWindows?: unknown
  cmeHistoricalImpliedPath?: { status?: string; observations?: unknown[]; limitations?: string[] | string }
}
export interface ReplayAnalysisEntry {
  id: string; date: string | null; title: string; text: string
  sourceIds: string[]; reportIds: string[]; evidenceRefs: string[]; dateNote?: string
  supportingEvidence?: { id: string; reportId?: string | null; actor?: string | null; publicationDate?: string | null; locatorLabel: string; evidenceBasis?: string | null }[]
}
export interface ReplayDeepDive {
  expectationTimeline?: ReplayAnalysisEntry[]; realityTimeline?: ReplayAnalysisEntry[]
  mechanism?: ReplayAnalysisEntry[]; divergence?: ReplayAnalysisEntry[]
  implicationTimeline?: ReplayAnalysisEntry[]; examples?: ReplayAnalysisEntry[]; validation?: ReplayAnalysisEntry[]
}
export interface ReplayPeriodSummary {
  paragraphs: string[]; sourceIds: string[]; reportIds: string[]; evidenceRefs: string[]
}
export interface ReplayAspectSummary {
  text: string; sourceIds: string[]; reportIds: string[]; evidenceRefs: string[]
}
export interface ReplayFrameworkEvidence {
  id: string; moduleSlugs: string[]; title: string; explanation: string; sourceVintageNote: string
  series: ReplayMarketSeries[]; datasetPins: unknown[]; retrospectiveOnly: boolean
  researchWindow?: { start: string; end: string; finiteObservationCount?: number; note?: string }
}
export interface ReplayMarketAnalysis {
  title: string; conclusion: string
  sections: {
    id: string; title: string; judgement: string; expectation: string; reality: string
    mechanism: string; divergence: string; implication: string; validation: string
    sourceIds: string[]; reportIds: string[]; deepDive?: ReplayDeepDive; frameworkEvidence?: ReplayFrameworkEvidence[]; periodSummary?: ReplayPeriodSummary; aspectSummaries?: Partial<Record<keyof ReplayDeepDive, ReplayAspectSummary>>
  }[]
  limitations: string[]
}
export interface ReplayWechatCoverage {
  requestedAccounts: {
    accountRequested: string; officialIdentityChecked: boolean; bodyObtainedCount: number
    status: string; limitations: string
  }[]
  actualAccounts: { accountActual: string; articleCount: number }[]
  totalArticles: number; totalOpinions: number; limitations: string[]
}
export interface ReplayRealityComparison {
  id: string; reportId: string; actor: string; expressedAt: string | null
  expectation: string; observationPeriod: string | null; pages: (string | number)[]
  reality: string | null; realitySourceIds: string[]; status: string; limitation: string
}
export interface ReplayMonthlyCoverage {
  requiredCells: number; coveredCells: number; acceptedCells: number; complete: boolean; basis: string
  rows: { month: string; channels: Record<string, {
    bodyCount: number; archiveEntries: number; searchExecuted: boolean; status: string; reason: string
    archives: { path: string; sha256: string; date: string; title: string; reportId?: string | null }[]
  }> }[]
}
export interface HistoryReplayData {
  title: string; startDate: string; asOf: string; summary: string[]
  endDate?: string; workbenchLabel?: string; eyebrow?: string
  sources: ReplaySource[]; events: ReplayEvent[]
  hypotheses: { title: string; test: string; invalidator: string; status: string }[]
  acquisition: { provider: string; status: string; detail: string }[]
  reports: ReplayReport[]
  researchEvidence?: ReplayResearchEvidence[]
  localResearchEvidence?: ReplayResearchEvidence[]
  windResearchEvidence?: ReplayResearchEvidence[]
  wechatResearchEvidence?: ReplayResearchEvidence[]
  wechatCoverage?: ReplayWechatCoverage
  marketPaths?: ReplayMarketPaths
  marketAnalysis?: ReplayMarketAnalysis
  realityComparisons?: ReplayRealityComparison[]
  archiveCoverage?: { channelEntries: number; uniqueDocuments: number; sharedDocuments: number; textVerifiedAliasCount?: number }
  monthlyCoverage?: ReplayMonthlyCoverage
  monthlyReplay?: (ReplayMarketAnalysis['sections'][number] & { month: string; opinionIds: string[]; factIds: string[]; dynamicConvergence: string; marketPath?: { startDate: string; endDate: string; twoYearChangeBp: number; tenYearChangeBp: number; spreadChangeBp: number; broadUSDChangePct: number; dxy: null } })[]
  revisionChains?: { id: string; label: string; description: string; opinionIds: string[]; limitation: string }[]
  readingTextOverrides?: { rawText: string; displayText: string; sourceTextSHA256: string }[]
}

const safeUrl = (url: string) => /^https?:\/\//i.test(url)
const knownBy = (date: string | null | undefined, cutoff: string) => Boolean(date && /^\d{4}-\d{2}-\d{2}$/.test(date) && cutoff && date <= cutoff)
// Explicit unknown availability is authoritative. Legacy absent fields retain
// their existing contract; new records never fall back from null to archive day.
const availableBy = (item: { firstAvailableDate?: string | null; availableFrom?: string | null }, cutoff: string) =>
  (item.firstAvailableDate === undefined || knownBy(item.firstAvailableDate, cutoff)) &&
  (item.availableFrom === undefined || knownBy(item.availableFrom, cutoff))
// Filename priority is a channel policy, not a property of every local filename.
// Legacy records retain authoritative publicationDate:null; never substitute postDate.
const filenameDatePreferred = (report: ReplayReport) => Boolean(report.dateBasis?.includes('filename_date_user_preferred'))
const reportDate = (report: ReplayReport) => report.filenameDate !== undefined && (!report.dateBasis || filenameDatePreferred(report)) ? report.filenameDate : report.publicationDate !== undefined ? report.publicationDate : report.date
const finiteObservation = (observation: ReplayMarketObservation) => typeof observation.value === 'number' && Number.isFinite(observation.value)
const limitationText = (value: string[] | string) => Array.isArray(value) ? value.join('；') : value
const conditionText = (value: unknown): string => Array.isArray(value) ? value.map(conditionText).join('；') : typeof value === 'string' ? value : value == null ? '' : JSON.stringify(value)
// Internal audit markers stay in the data; the adjacent source sections remain
// visible, while opaque IDs do not interrupt the reading copy of the new study.
const displayResearchText = (text: string, data: HistoryReplayData): string => {
  const readingText = data.readingTextOverrides?.find(item => item.rawText === text)?.displayText ?? text
  const ids = new Set([
    ...(data.monthlyReplay || []).flatMap(month => [...month.opinionIds, ...month.factIds, ...month.sourceIds, ...month.reportIds]),
    ...data.events.map(event => event.id),
    ...[...(data.researchEvidence || []), ...(data.windResearchEvidence || []), ...(data.wechatResearchEvidence || []), ...(data.localResearchEvidence || [])].flatMap(item => item.id ? [item.id] : []),
    ...(data.marketAnalysis?.sections.flatMap(section => Object.values(section.deepDive || {}).flat().flatMap(entry => [entry.id, ...entry.evidenceRefs])) || []),
    ...data.sources.map(source => source.id), ...data.reports.flatMap(report => report.id ? [report.id] : []),
    ...(data.marketAnalysis?.sections.flatMap(section => [...section.sourceIds, ...section.reportIds]) || []),
  ])
  return formatReplayText(readingText.replace(/\[([^\]]+)\]/g, (marker, id: string) => ids.has(id) ? '' : marker))
}
const marketColors = ['#1765ad', '#ad5c15', '#247a64', '#8b5a9f', '#bc3d4b', '#64748b', '#6d740c', '#1b8291']
const isRateUnit = (unit: string) => /^(%|percent|percent_per_annum|百分比)$/i.test(unit)
const chartUnit = (unit: string) => isRateUnit(unit) ? '%' : unit === 'index_Jan2006_100' ? '2006年1月=100' : unit

// Month/quarter technical positions are for the X coordinate only; their
// observation labels retain the original precision, never an invented day.
const observationTime = (date: string): number => {
  const quarter = /^(\d{4})-?Q([1-4])$/.exec(date)
  if (quarter) return Date.UTC(Number(quarter[1]), (Number(quarter[2]) - 1) * 3, 1)
  return formatReplayDate(date) !== date ? Date.parse(date) : NaN
}
const observationLabel = (observation: ReplayMarketObservation) => formatReplayDate(observation.observationPeriod || observation.date)

function MarketPathChart({ series, title, unit, researchWindow, valueLabel = '原始值，不归一化' }: { series: ReplayMarketSeries[]; title: string; unit: string; researchWindow?: ReplayFrameworkEvidence['researchWindow']; valueLabel?: string }) {
  const observations = series.flatMap((item) => item.observations).sort((a, b) => observationTime(a.date) - observationTime(b.date))
  const values = observations.filter(finiteObservation).map((item) => item.value as number)
  if (!values.length) return <p className="replay-empty">{title}：当前信息集内暂无可绘制观测。</p>
  const first = Math.min(...observations.map((item) => observationTime(item.date)))
  const last = Math.max(...observations.map((item) => observationTime(item.date)))
  const low = Math.min(...values), high = Math.max(...values)
  const padding = Math.max((high - low) * 0.12, Math.abs(high) * 0.01, 0.05)
  const min = low - padding, max = high + padding
  const x = (date: string) => 64 + (observationTime(date) - first) / (last - first || 1) * 590
  const y = (value: number) => 32 + (max - value) / (max - min) * 210
  return <figure className="replay-path-chart">
    <figcaption><h3>{title}</h3><span>纵轴：{unit} · {valueLabel}</span></figcaption>
    <div className="replay-chart-scroll"><svg viewBox="0 0 700 285" role="img" aria-label={`${title}（${unit}）`}>
      <title>{title} · 缺失值保留断点</title>
      {researchWindow && <rect data-research-window="" x={x(new Date(Math.min(last, Math.max(first, Date.parse(researchWindow.start)))).toISOString().slice(0, 10))} y="32" width={Math.max(0, x(new Date(Math.min(last, Date.parse(researchWindow.end))).toISOString().slice(0, 10)) - x(new Date(Math.min(last, Math.max(first, Date.parse(researchWindow.start)))).toISOString().slice(0, 10)))} height="210" fill="#e0ecfc"><title>蓝色背景：复盘研究窗口；窗口之前为明确前史。</title></rect>}
      {Array.from({ length: 5 }, (_, index) => { const value = max - (max - min) * index / 4; return <g key={index}><line x1="64" x2="654" y1={y(value)} y2={y(value)} className="replay-chart-grid" /><text x="56" y={y(value) + 4} textAnchor="end">{value.toFixed(2)}</text></g> })}
      <text x="64" y="271">{observationLabel(observations[0])}</text><text x="654" y="271" textAnchor="end">{observationLabel(observations.at(-1)!)}</text>
      {series.map((item, index) => {
        let drawing = false
        const path = item.observations.map((observation) => {
          if (!finiteObservation(observation)) { drawing = false; return '' }
          const command = `${drawing ? 'L' : 'M'} ${x(observation.date).toFixed(2)} ${y(observation.value!).toFixed(2)}`
          drawing = true
          return command
        }).join(' ')
        return <g key={item.id}><path data-series-id={item.id} d={path} fill="none" stroke={marketColors[index % marketColors.length]} strokeWidth="2" strokeDasharray={index === 1 ? '7 3' : undefined} />{item.observations.filter(finiteObservation).map((observation) => <circle key={observation.date} cx={x(observation.date)} cy={y(observation.value!)} r="3" fill={marketColors[index % marketColors.length]}><title>{item.title} · 观察期 {observationLabel(observation)}{observation.isPrehistory ? '（前史）' : ''} · {observation.value} {item.unit} · 发布日 {formatReplayDate(observation.releaseDate) || '首次发布日期未确认'}</title></circle>)}</g>
      })}
    </svg></div>
    <ul className="replay-chart-legend">{series.map((item, index) => <li key={item.id}><span style={{ borderColor: marketColors[index % marketColors.length], borderStyle: index === 1 ? 'dashed' : 'solid' }} />{item.title}</li>)}</ul>
  </figure>
}

function MarketPaths({ paths, cutoff, historical }: { paths: ReplayMarketPaths; cutoff: string; historical: boolean }) {
  const eligible = (observation: ReplayMarketObservation) => observation.historicalAsOfEligible === true && knownBy(observation.releaseDate, cutoff)
  const series = paths.series.map((item) => ({ ...item, observations: item.observations
    .filter((observation) => knownBy(observation.date, cutoff) && Number.isFinite(Date.parse(observation.date)))
    .sort((a, b) => a.date.localeCompare(b.date))
    // Preserve a gap rather than connecting across a withheld observation. Never pass its value to SVG.
    .map((observation) => historical && !eligible(observation) ? { date: observation.date, value: null, releaseDate: null, historicalAsOfEligible: false } : observation) }))
  const rates = series.filter((item) => isRateUnit(item.unit))
  const others = series.filter((item) => !rates.includes(item))
  return <section className="replay-panel replay-market-paths" aria-label="真实行情路径">
    <header><h2>真实行情路径</h2><span>{historical ? '历史截面 · 仅已确认可得观测' : '当前取得的追溯路径 · 不等同于历史时点可得版本'}</span></header>
    {historical && <p className="replay-notice">historicalAsOfEligible 必须为 true，且 releaseDate 不晚于截止日。首次发布日期未确认的国债值不进入历史截面；当前取得时间不替代首次发布日期。</p>}
    <p className="replay-notice">利率 % 两线同轴；美元独立轴，贸易加权广义美元指数不是DXY。原始单位单独显示；null 不填补，不伪造首次发布日期，不将同期变化归因于单一事件。</p>
    <div className="replay-path-grid">{rates.length > 0 && <MarketPathChart series={rates} title="利率路径" unit="%" />}{others.map((item) => <MarketPathChart key={item.id} series={[item]} title={item.title} unit={chartUnit(item.unit)} />)}</div>
    <div className="replay-path-metadata">{series.map((item) => {
      const valid = item.observations.filter(finiteObservation)
      const latest = valid.at(-1)
      const rows = item.observations.filter((observation) => !historical || eligible(observation))
      return <article key={item.id}><h3>{item.title}</h3><p>{!historical && `${item.status} · `}{valid.length} 个有效观测 · 单位：{item.unit}</p><p>最新观测：{latest ? `${formatReplayDate(latest.date)} · ${latest.value} ${item.unit}` : '暂无'} · 发布日：{formatReplayDate(latest?.releaseDate) || '首次发布日期未确认'}</p>{!historical && <p className="replay-missing">{limitationText(item.limitations)}</p>}{safeUrl(item.sourceUrl) && <a href={item.sourceUrl} target="_blank" rel="noreferrer">{item.title} · 原始来源 ↗</a>}
        <details><summary>逐点日期与缺口 · {rows.length} 条记录</summary><div className="replay-table-wrap"><table aria-label={`${item.title}观测记录`}><thead><tr><th>观测日</th><th>原始值 / 单位</th><th>首次发布日期</th>{!historical && <th>当前取得 / 可得上界</th>}<th>缺口</th></tr></thead><tbody>{rows.map((observation) => <tr key={observation.date}><td>{formatReplayDate(observation.date)}</td><td>{finiteObservation(observation) ? `${observation.value} ${item.unit}` : '缺失（不填补）'}</td><td>{formatReplayDate(observation.releaseDate) || '首次发布日期未确认'}</td>{!historical && <td>{formatReplayDate(observation.availableBy) || '未注明'}</td>}<td>{observation.missingReason || '—'}</td></tr>)}</tbody></table></div></details>
      </article>
    })}</div>
  </section>
}

function WechatCoverage({ coverage }: { coverage: ReplayWechatCoverage }) {
  return <section className="replay-wechat-coverage" aria-label="微信公众号来源覆盖">
    <h3>公众号来源覆盖</h3>
    <p>已取得正文 {coverage.totalArticles} 篇 · 提取观点 {coverage.totalOpinions} 条</p>
    <p className="replay-wechat-accounts">实际发表账号：{coverage.actualAccounts.length ? coverage.actualAccounts.map((account) => <span key={account.accountActual}>{account.accountActual} · {account.articleCount} 篇</span>) : '暂无已取得正文的账号'}</p>
    <p className="replay-missing">检索清单不等于已取得正文；论坛不视为独立研究机构；同机构多个渠道不计为独立共识。实际发表账号与原始检索名分别登记，不强配账号身份。</p>
    {coverage.limitations.length > 0 && <p className="replay-missing">覆盖局限：{coverage.limitations.join('；')}</p>}
    <details className="replay-wechat-search-audit" aria-label="公众号候选检索审计">
      <summary>原始检索账号审计 · {coverage.requestedAccounts.length} 个（点击展开）</summary>
      <ul>{coverage.requestedAccounts.map((account) => <li key={account.accountRequested}>
        <strong>{account.accountRequested}</strong><span>{account.status} · 已取得正文 {account.bodyObtainedCount} 篇 · {account.officialIdentityChecked ? '官方身份已核验' : '官方身份未确认'}</span>
        {account.limitations && <p className="replay-missing">{account.limitations}</p>}
      </li>)}</ul>
    </details>
  </section>
}

function ReportProvenance({ report }: { report?: ReplayReport }) {
  if (!report) return null
  const authors = Array.isArray(report.authors) ? report.authors.join('、') : report.authors
  if (!report.accountActual && !authors && !report.researchOrigin && !report.distributionType) return null
  return <div className="replay-report-provenance">
    {report.accountActual && <p>发表账号：{report.accountActual}</p>}
    {authors && <p>作者：{authors}</p>}
    {report.researchOrigin && <p>研究来源：{report.researchOrigin}</p>}
    {report.distributionType && <p>分发类型：{report.distributionType}</p>}
  </div>
}

function MonthlyCoverage({ coverage }: { coverage: ReplayMonthlyCoverage }) {
  return <section className="replay-monthly-coverage" aria-label="月份与渠道覆盖">
    <h3>月份 × 渠道覆盖</h3>
    <p><strong>{coverage.complete ? '逐月覆盖通过·有限样本，非全量' : '未满足逐月覆盖验收'}</strong> · 已有正文 {coverage.coveredCells} / {coverage.requiredCells} 格 · 月度原文配额已验收 {coverage.acceptedCells} / {coverage.requiredCells} 格</p>
    <p className="replay-missing">只计可核验的正文实物；标题、检索名单与其他渠道资料不能填格。档案按SHA去重；水印可使同文SHA不同，档案数量不等于独立作品或机构观点。</p>
    <p className="replay-swipe-hint">左右滑动表格，查看各渠道</p>
    <div className="replay-table-wrap"><table aria-label="逐月渠道正文覆盖表"><thead><tr><th>月份</th>{['知识星球', 'Wind', '微信公众号'].map(channel => <th key={channel}>{channel}</th>)}</tr></thead>
      <tbody>{coverage.rows.map(row => <tr key={formatReplayDate(row.month)}><th scope="row">{formatReplayDate(row.month)}</th>{['知识星球', 'Wind', '微信公众号'].map(channel => {
        const cell = row.channels[channel]
        return <td key={channel}><strong>{cell.bodyCount} 份正文档案</strong><p>{cell.status}</p>{cell.reason && <p className="replay-missing">{cell.reason}</p>}
          {cell.bodyCount > 0 && <details><summary>归档定位 · {cell.archiveEntries} 条渠道记录</summary><ul>{cell.archives.map(archive => <li key={archive.sha256}>{formatReplayDate(archive.date)} · {archive.title}<code>{archive.path}</code></li>)}</ul></details>}
        </td>
      })}</tr>)}</tbody></table></div>
    <p className="replay-missing">{coverage.basis}</p>
  </section>
}

function MonthlyReplayResearch({ data }: { data: HistoryReplayData }) {
  const months = data.monthlyReplay || []
  const chains = data.revisionChains || []
  const opinions = [...(data.researchEvidence || []), ...(data.windResearchEvidence || []), ...(data.wechatResearchEvidence || [])]
  const references = (ids: string[]) => ids.map(id => {
    const source = data.sources.find(item => item.id === id)
    return <span className="replay-source-ref" key={id}>{source && safeUrl(source.url) ? <a href={source.url} target="_blank" rel="noreferrer">{source.title} · {formatReplayDate(source.date)} ↗</a> : source?.title || '来源待核'}</span>
  })
  return <details className="replay-disclosure" aria-label="逐月预期现实与修订链">
    <summary>逐月预期 → 现实与修订链 · {months.length}个月 / {chains.length}条链（点击展开）</summary>
    <section className="replay-panel replay-monthly-research" aria-label="当前追溯逐月研究">
      <p className="replay-notice">仅当前追溯研究，非当时完整信息集或市场共识。月份按研究表述归档；后续验证仍保留发布版本、条件和未到期窗口，严格历史截面卸载本块。</p>
      {!months.length && <p className="replay-empty">暂无独立父方核验的逐月研究；不补造八月链。</p>}
      {months.map(month => <article className="replay-monthly-topic" data-replay-month={month.month} key={month.id}>
        <h3>{month.title}</h3><p className="replay-analysis-judgement">{displayResearchText(month.judgement, data)}</p>
        <dl>{[
          ['观点 / 事前预期', month.expectation], ['现实', month.reality], ['机制', month.mechanism],
          ['分歧 / 预期差', month.divergence], ['市场含义', month.implication], ['验证条件', month.validation],
        ].map(([label, text]) => <div key={label}><dt>{label}</dt><dd>{displayResearchText(text, data)}</dd></div>)}</dl>
        {month.marketPath && <p>实际路径窗口：{formatReplayDate(`${month.marketPath.startDate}—${month.marketPath.endDate}`)} · 2年 {month.marketPath.twoYearChangeBp}bp / 10年 {month.marketPath.tenYearChangeBp}bp · 利差变化 {month.marketPath.spreadChangeBp}bp · 广义美元 {month.marketPath.broadUSDChangePct.toFixed(2)}%（非DXY）；首末共同有效点，不是月收益或因果贡献。</p>}
        <p>动态收敛：{displayResearchText(month.dynamicConvergence, data)}</p>
        <div><h4>原文与官方依据</h4>{references(month.sourceIds)}{month.reportIds.map(id => <span className="replay-source-ref" key={id}>{data.reports.find(report => report.id === id)?.title || '研究原文待核'} · 不公开全文</span>)}</div>
      </article>)}
      {chains.map(chain => <article className="replay-monthly-topic" data-revision-chain={chain.id} key={chain.id}>
        <h3>{chain.label}</h3><p>{chain.description}</p><p className="replay-missing">{chain.limitation}</p>
        <ol>{chain.opinionIds.map(id => {
          const opinion = opinions.find(item => item.id === id)
          return <li key={id}>{opinion ? <><strong>{formatReplayDate(opinion.expressedAt) || '正文表述日未知'} · {opinion.actor}</strong><p>{opinion.claim}</p><p>期限：{opinion.forecastHorizon?.literalResearchWindow || opinion.observationPeriod || '未明确'} · 状态：{opinion.status || '待验'}</p><p>条件：{conditionText(opinion.conditions) || '未明确，不能按无条件预测评分'}</p></> : '观点待核'}</li>
        })}</ol>
      </article>)}
    </section>
  </details>
}

function ResearchEvidence({ items, reports, channel = '星球', coverage, sources = [], events = [] }: { items: ReplayResearchEvidence[]; reports: ReplayReport[]; channel?: '星球' | 'Wind' | '微信' | '本地研报'; coverage?: ReplayWechatCoverage; sources?: ReplaySource[]; events?: ReplayEvent[] }) {
  const pricingCount = channel === 'Wind' ? items.filter(item => item.claimType === 'market_pricing_snapshot').length : 0
  const countLabel = pricingCount ? `${items.length - pricingCount}条观点 + ${pricingCount}条市场定价描述` : `${items.length}`
  return <details className="replay-disclosure" aria-label={`${channel}观点明细`}>
    <summary>{channel}观点明细 · {countLabel}（点击展开）</summary>
    <section className="replay-panel replay-research-evidence" aria-label={`${channel}观点独立追溯`}>
    <header><h2>{channel}观点 → 现实 / 待验证 · {items.length}</h2><span>仅当前复盘 · 已审计材料独立追溯</span></header>
    {channel === '微信' && coverage && <WechatCoverage coverage={coverage} />}
    <p className="replay-notice">{channel === '星球' ? '平台发帖日不等同于正文发布日期；日期依据未核验或事件日期关联不明时，只作追溯线索。文件名归档日期不等同于已核正文发布日期或历史可得时间。这些作者观点不构成严格事前市场共识，也不是会前隐含定价。' : '正文发布日期与判断对象分开：事后报告不倒填会前预期；具名机构观点不等同于市场共识。首次可得日未核不进入历史截面；机构转述的市场定价不算独立预测。未发生的政策行动保留待验证。'}</p>
    {!items.length && <p className="replay-empty">暂无已核验的{channel}观点正文，尚未形成观点与现实对照。</p>}
    <div className="replay-audit-grid">{items.map((item, index) => {
      const report = reports.find((entry) => entry.id === item.reportId)
      return <article className="replay-audit-card" data-opinion-id={item.id} key={`${item.reportId}-${index}`}>
        <small>{item.claimType === 'market_pricing_snapshot' ? '市场定价描述 · 非机构预测' : item.status || '待验证'}</small><h3>{item.actor} · {item.scope}</h3>
        <ReportProvenance report={report} />
        <p className="replay-audit-claim">{item.claim}</p>
        <p>{item.dateBasis?.includes('filename_date_user_preferred') ? '观点归档日期（文件名优先）' : channel === '星球' ? '观点日期 / 平台日' : '观点日期'}：{formatReplayDate(item.expressedAt) || '未知'} · 日期依据：{item.dateBasis || '未核验'}</p>
        <p>观测期：{formatReplayText(formatReplayDate(item.observationPeriod) || '未注明')}</p>
        {item.forecastHorizon && <p>期限：{formatReplayText(item.forecastHorizon.literalResearchWindow || item.observationPeriod || '未明确')} · 截止：{formatReplayDate(item.forecastHorizon.effectiveDeadline || item.forecastHorizon.deadlineMonth || item.forecastHorizon.end) || '无精确截止日，不补造'}</p>}
        {item.conditions !== undefined && <p>条件：{conditionText(item.conditions) || '未明确，不能按无条件预测评分'}</p>}
        {item.value != null && <div className="replay-audit-value"><span>原文数值 / 条件情景 · {item.unit || '未注明单位'}</span><pre>{typeof item.value === 'object' ? JSON.stringify(item.value, null, 2) : String(item.value)}</pre></div>}
        <div className="replay-evidence-grid"><div><h4>原文证据</h4><p>{item.evidenceExcerpt || '无可引短摘录；页码与原文位置已核验'}</p><small>{channel === '微信' ? '证据段' : '证据页'}：{item.pages.join('、') || '未注明'}</small></div><div><h4>对应现实 / 待验证</h4><p>{item.reality || '尚无已核验的对应现实，待验证。'}</p><small>关联事件：{events.find(event => event.id === item.eventId)?.title || '关联未核'} · 事件日期：{formatReplayDate(item.eventDate) || '未知'}</small></div></div>
        <p className="replay-missing">局限：{Array.isArray(item.limitations) ? item.limitations.join('；') : item.limitations || '未注明'}</p>
        {item.realitySourceIds?.map(id => {
          const source = sources.find(entry => entry.id === id)
          return <span className="replay-source-ref" key={id}>{source && safeUrl(source.url) ? <a href={source.url} target="_blank" rel="noreferrer">对应现实原始来源：{source.title} · {formatReplayDate(source.date)} ↗</a> : '对应现实来源待核'}</span>
        })}
        <p>材料：{item.reportTitle || report?.title || '研究材料待核'}</p><code>{item.localPath || report?.path || '尚无本地文件'}</code>
      </article>
    })}</div>
  </section></details>
}

function FrameworkEvidence({ section, cutoff }: { section: ReplayMarketAnalysis['sections'][number]; cutoff: string }) {
  if (!section.frameworkEvidence?.length) return null
  return <section className="replay-framework-evidence" aria-label={`${section.title} · 框架辅助证据`}>
    <h4>宏观框架辅助图表</h4>
    {section.frameworkEvidence.map(evidence => {
      const series = evidence.series.map(item => ({ ...item, observations: item.observations.filter(observation => Number.isFinite(observationTime(observation.date))).sort((a, b) => observationTime(a.date) - observationTime(b.date)) }))
      const units = [...new Set(series.map(item => chartUnit(item.unit)))]
      return <article className="replay-framework-card" key={evidence.id}>
        <h4>{evidence.title}</h4><p>{formatReplayText(evidence.explanation)}</p>
        <p className="replay-notice">仅用于辅助回溯，不进入严格历史信息集。图值可能包含修订或加工，不代替当时初报，也不保证与当前在线模块相同。即使观察期落在复盘窗口内，也不代表数据当时已经公开；正文现实以已核官方原稿为准，未知发布时间不补造。</p>
        <details><summary>冻结版本与完整使用限制</summary><p>{formatReplayText(evidence.sourceVintageNote)}</p></details>
        {evidence.researchWindow && <p>复盘窗口：{formatReplayDate(`${evidence.researchWindow.start}—${evidence.researchWindow.end}`)} · 蓝色背景标记复盘窗口，此前观测标为前史。{evidence.researchWindow.note && formatReplayText(evidence.researchWindow.note)}</p>}
        {units.length > 1 && <p className="replay-missing">不同单位分轴展示，不作隐含换算或归一化。</p>}
        <div className="replay-framework-charts">{units.map(unit => <MarketPathChart key={unit} series={series.filter(item => chartUnit(item.unit) === unit)} title={units.length > 1 ? `${evidence.title} · ${unit}` : evidence.title} unit={unit} researchWindow={evidence.researchWindow} valueLabel="冻结图值，沿用所列口径；不追加归一化" />)}</div>
        <div className="replay-framework-series">{series.map(item => {
          const metadata = item.sourceMetadata
          const update = metadata?.sourceUpdateDate || metadata?.updateDate
          const periods = item.observations
          return <div key={item.id}>
            <h5>{item.title}</h5><p>{item.status} · 单位：{item.unit} · 频率：{item.frequency || '未注明'}</p>
            <p>来源：{[metadata?.provider, metadata?.institution, metadata?.name].filter(Boolean).join(' · ') || '见原始来源'} · 源原单位：{metadata?.rawUnit || item.unit}</p>
            <p>冻结数据版本：{formatReplayText(formatReplayDate(item.sourceGeneratedAt) || '取得时点未注明')} · 数据库源更新时间：{formatReplayText(formatReplayDate(update) || '未注明')}</p>
            {metadata?.inheritedTransformation && <p>沿用加工口径：{metadata.inheritedTransformation}</p>}
            <p>观察期：{periods.length ? `${observationLabel(periods[0])}至${observationLabel(periods.at(-1)!)}` : '暂无'} · 发布时钟与观察期分开，月／季度绘图锚点不视为某日观测或发布。</p>
            <details><summary>该序列的口径与缺口说明</summary><p className="replay-missing">{formatReplayText(limitationText(item.limitations))}</p></details>
            {safeUrl(item.sourceUrl) && <a href={item.sourceUrl} target="_blank" rel="noreferrer">{item.title} · 原始来源 ↗</a>}
            <details><summary>逐点观察期、发布钟与缺口 · {periods.length} 条记录</summary>
              <div className="replay-table-wrap"><table aria-label={`${item.title}辅助观察记录`}><thead><tr><th>观察期（原精度）</th><th>图值 / 单位</th><th>已记录发布日期（不认证该值初版）</th><th>窗口 / 缺口</th></tr></thead><tbody>{periods.map(observation => <tr key={observation.date}><td>{observationLabel(observation)}</td><td>{finiteObservation(observation) ? `${observation.value} ${item.unit}` : '缺失（不填补）'}</td><td>{formatReplayDate(observation.releaseDate) || '首次发布日期未确认'}{observation.releaseDate && observation.releaseDate > cutoff && ' · 晚于复盘截止'}</td><td>{observation.isPrehistory ? '明确前史' : '复盘窗口'}{observation.missingReason && ` · ${observation.missingReason}`}</td></tr>)}</tbody></table></div>
            </details>
          </div>
        })}</div>
        <div className="replay-framework-links">{evidence.moduleSlugs.map(slug => {
          const page = US_MACRO_PAGES.find(item => item.slug === slug)
          return page ? <a key={slug} href={`#framework/${page.slug}`}>{page.label} ↗</a> : null
        })}<p>链接进入实际框架模块，当前模块版本不等同于本图冻结版本或当时初值。</p></div>
      </article>
    })}
  </section>
}

const analysisBlocks: { key: keyof ReplayDeepDive; label: string; fallback?: keyof Pick<ReplayMarketAnalysis['sections'][number], 'expectation' | 'reality' | 'mechanism' | 'divergence' | 'implication' | 'validation'> }[] = [
  { key: 'expectationTimeline', label: '观点 / 事前预期', fallback: 'expectation' },
  { key: 'realityTimeline', label: '现实', fallback: 'reality' },
  { key: 'mechanism', label: '机制', fallback: 'mechanism' },
  { key: 'divergence', label: '分歧 / 预期差', fallback: 'divergence' },
  { key: 'implicationTimeline', label: '市场含义', fallback: 'implication' },
  { key: 'examples', label: '实例 / 原文与数据' },
  { key: 'validation', label: '验证条件', fallback: 'validation' },
]

function AnalysisEntries({ entries, data, sources, cutoff }: { entries: ReplayAnalysisEntry[]; data: HistoryReplayData; sources: ReplaySource[]; cutoff: string }) {
  const evidence = [...(data.researchEvidence || []), ...(data.windResearchEvidence || []), ...(data.wechatResearchEvidence || []), ...(data.localResearchEvidence || [])]
  return <ol className="replay-analysis-entries">{entries.map(entry => {
    const opinions = evidence.filter(item => item.id && entry.evidenceRefs.includes(item.id))
    const events = data.events.filter(item => entry.evidenceRefs.includes(item.id))
    const sourceIds = [...new Set([...entry.sourceIds, ...opinions.flatMap(item => item.realitySourceIds || []), ...events.flatMap(item => item.realitySourceIds)])]
    const reportIds = [...new Set([...entry.reportIds, ...opinions.map(item => item.reportId)])]
    return <li key={entry.id}>
      <div className="replay-entry-heading">{entry.date ? <time dateTime={entry.date}>{formatReplayDate(entry.date)}</time> : <span className="replay-date-unknown" title="资料未注明具体日期，保留未知，不补造日期精度。">日期未详</span>}<h5>{displayResearchText(entry.title, data)}</h5></div>
      {entry.dateNote && <p className="replay-missing">{formatReplayText(entry.dateNote)}</p>}
      {entry.text.split(/\n\s*\n|\n/).filter(Boolean).map((paragraph, index) => <p key={index}>{displayResearchText(paragraph, data)}</p>)}
      <div className="replay-entry-references" aria-label="节点研究依据">
        {sourceIds.map(id => {
          const source = sources.find(item => item.id === id)
          return <span className="replay-source-ref" key={id}>{source ? <>{safeUrl(source.url) ? <a href={source.url} target="_blank" rel="noreferrer">{source.title} ↗</a> : source.title} · {source.publisher} · {formatReplayDate(source.date) || '发布日期未核，不补造'}</> : '来源未在截止日前核验'}</span>
        })}
        {reportIds.map(id => {
          const report = data.reports.find(item => item.id === id && (!reportDate(item) || reportDate(item)! <= cutoff))
          return <div className="replay-source-ref" key={id}>{report ? <><p>{report.title} · {report.provider} · {formatReplayDate(reportDate(report)) || '刊期未核'} · 本地资料，不公开全文</p><ReportProvenance report={report} /></> : '研究原文尚未核验'}</div>
        })}
        {opinions.map((opinion, index) => <div className="replay-entry-conditions" key={opinion.id || index}>
          <p>观点归属：{opinion.actor} · 表述日：{formatReplayDate(opinion.expressedAt) || '未核'} · {opinion.status || '待验证'}</p>
          <p>条件：{formatReplayText(conditionText(opinion.conditions)) || '未明确，不能按无条件预测评分'}</p>
          <p>期限：{formatReplayText(opinion.forecastHorizon?.literalResearchWindow || opinion.observationPeriod || '未明确')}</p>
          <p>原文定位：{opinion.pages.map(page => typeof page === 'string' && /^p\d+$/.test(page) ? `第${page.slice(1)}段` : `第${page}页`).join('、') || '未注明'}</p>
        </div>)}
        {!!entry.supportingEvidence?.length && <ul className="replay-entry-conditions" aria-label="原文定位与署名">{entry.supportingEvidence.map(ref => <li key={ref.id}><p>观点归属：{ref.actor || '原文署名未核'} · 原文日期：{formatReplayDate(ref.publicationDate) || '未明确，不补造'}</p><p>原文定位：{ref.locatorLabel}{ref.evidenceBasis ? ` · ${ref.evidenceBasis}` : ''}</p></li>)}</ul>}
        {!sourceIds.length && !reportIds.length && <p className="replay-missing">本节点引用尚未接入，不视为独立已核证据。</p>}
      </div>
    </li>
  })}</ol>
}

function AnalysisDetails({ section, data, sources, cutoff }: { section: ReplayMarketAnalysis['sections'][number]; data: HistoryReplayData; sources: ReplaySource[]; cutoff: string }) {
  return <dl className={section.deepDive ? 'replay-deep-dive' : undefined}>{analysisBlocks.map(block => {
    const entries = section.deepDive?.[block.key]
    const summary = section.aspectSummaries?.[block.key]
    if (!block.fallback && !entries?.length && !summary?.text) return null
    return <div key={block.key}><dt>{block.label}</dt><dd>{summary?.text && <p className="replay-aspect-summary" data-aspect-summary={block.key}>{displayResearchText(summary.text, data)}</p>}{entries?.length ? <AnalysisEntries entries={entries} data={data} sources={sources} cutoff={cutoff} /> : displayResearchText(block.fallback ? section[block.fallback] || '尚无经核验结论' : '尚无经核验实例', data)}</dd></div>
  })}</dl>
}

export function HistoryReplay({ onBack, data = replayData }: { onBack: () => void; data?: HistoryReplayData }) {
  const [selectedCutoff, setSelectedCutoff] = useState(data.asOf)
  const [query, setQuery] = useState('')
  const cutoff = selectedCutoff && selectedCutoff <= data.asOf ? selectedCutoff : data.asOf
  const historical = Boolean(cutoff && cutoff < data.asOf)
  const hasMarketValues = Boolean(data.marketPaths?.series.some((series) => series.observations.some(finiteObservation)))
  const sources = data.sources.filter((source) => (knownBy(source.date, cutoff) || (!historical && source.retrospectiveOnly)) && (!historical || (source.historicalAsOfEligible !== false && availableBy(source, cutoff))))
  const matches = (values: string[]) => values.join(' ').toLowerCase().includes(query.trim().toLowerCase())
  const availableSources = sources.filter((source) => safeUrl(source.url) && matches([source.title, source.publisher, source.kind, historical ? '' : source.note, historical ? '' : source.status]))
  const events = data.events.filter((event) => knownBy(event.date, cutoff) && (!historical || (event.historicalAsOfEligible !== false && knownBy(event.availableFrom || event.date, cutoff) && [...event.expectationSourceIds, ...event.realitySourceIds].every(id => sources.some(source => source.id === id))))).sort((a, b) => a.date.localeCompare(b.date))
  const reports = data.reports.filter((report) => (historical ? report.historicalAsOfEligible !== false && knownBy(reportDate(report), cutoff) && availableBy(report, cutoff) : !reportDate(report) || knownBy(reportDate(report), cutoff)) && matches([report.title, report.provider, report.scope || '', report.geography || '', ...(report.topics || []), historical ? '' : report.note || '']))
  const sourceLinks = (ids: string[]) => ids.map((id) => {
    const source = sources.find((item) => item.id === id)
    return source ? <span key={id} className="replay-source-ref">{safeUrl(source.url) ? <a href={source.url} target="_blank" rel="noreferrer">{source.title} ↗</a> : <span>{source.title} · 无公开URL</span>}</span> : <span key={id} className="replay-missing">来源未在截止日前核验</span>
  })
  const evidenceText = (text: string, ids: string[], before?: string) => ids.length > 0 && ids.every((id) => sources.some((source) => source.id === id && (!before || source.date < before))) ? text || '未记录' : '缺少当时可得来源，暂不作结论'

  return <article className="history-replay" aria-label={data.workbenchLabel || '政策反转研究工作台'}>
    <header className="replay-heading">
      <div><button type="button" className="history-back" aria-label="返回父阶段复盘" onClick={onBack}>← 返回父阶段复盘</button><p className="eyebrow">{data.eyebrow || 'POLICY REVERSAL · RESEARCH WORKBENCH'}</p><h1>{data.title}</h1><p>{data.endDate ? `阶段区间：${formatReplayDate(`${data.startDate}—${data.endDate}`)}；阶段划分与判断均可修订。` : `开放时期：${formatReplayDate(data.startDate)} 起，终点未形成；阶段划分与判断均可修订。`}</p></div>
      <div className="replay-date"><span>资料核验截止</span><strong>{formatReplayDate(data.asOf) || '准备中 · 尚无核验日期'}</strong></div>
    </header>
    <figure className="replay-method-map" aria-label="复盘方法框架">
      <figcaption><h2>复盘方法框架</h2><span>预期与现实对照，持续验证</span></figcaption>
      <ol>{['事前预期', '数据 / 政策事件', '美债 / 美元重定价', '后续验证 / 修正'].map((step) => <li key={step}>{step}</li>)}</ol>
      <div className="replay-method-feedback">↶ 反馈：修正预期</div>
      <p>方法示意，不是确定的因果链；日频变化不等于因果，需结合信息发布时间与其他冲击验证。</p>
    </figure>
    <div className="replay-toolbar"><label htmlFor="replay-cutoff">按日期截止查看<input id="replay-cutoff" type="date" max={data.asOf || undefined} value={selectedCutoff} onChange={(event) => setSelectedCutoff(event.target.value)} /></label><button type="button" onClick={() => setSelectedCutoff(data.asOf)}>恢复资料截止日</button><span role="status">{historical ? '严格历史截面' : '当前完整资料视图'}：{formatReplayDate(cutoff) || '准备中'} · {events.length} 条事件</span></div>
    <p className="replay-notice">防后见偏差：按信息发布日期而非观测期筛选。历史截面隐藏当前总结、事后解释和判断；来源日期不明的材料不进入截面。未提供逐版本存档，不等同于完整的实时数据回放。</p>
    {!historical && (data.marketAnalysis ? <section className="replay-panel replay-market-analysis" aria-label="综合市场分析">
      <header><h2>{data.marketAnalysis.title}</h2><span>当前完整资料综合研究 · 非历史时点预期</span></header>
      <p className="replay-analysis-conclusion">{displayResearchText(data.marketAnalysis.conclusion, data)}</p>
      <nav className="replay-topic-directory" aria-label="综合分析主题目录">{data.marketAnalysis.sections.map((section, index) => <a key={section.id} href={`#replay-topic-${index}`} onClick={event => {
        // This dashboard uses hash routes. Local reading anchors must not navigate
        // away from the workbench or reset the selected stage.
        event.preventDefault()
        const target = document.getElementById(`replay-topic-${index}`)
        target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        target?.focus({ preventScroll: true })
      }}>{section.title}</a>)}</nav>
      {data.marketAnalysis.sections.map((section, index) => <article className="replay-analysis-topic" id={`replay-topic-${index}`} tabIndex={-1} key={section.id}>
        <h3>{section.title}</h3>
        {!!section.periodSummary?.paragraphs.length && <section className="replay-period-summary" data-period-summary={section.id} aria-label={`${section.title} · 阶段总结`}><h4>阶段总结</h4>{section.periodSummary.paragraphs.map((paragraph, summaryIndex) => <p key={summaryIndex}>{displayResearchText(paragraph, data)}</p>)}</section>}
        <p className="replay-analysis-judgement">{displayResearchText(section.judgement, data)}</p>
        <AnalysisDetails section={section} data={data} sources={sources} cutoff={cutoff} />
        <FrameworkEvidence section={section} cutoff={cutoff} />
        <div className="replay-analysis-references"><h4>研究依据</h4>{sourceLinks(section.sourceIds)}
          {section.reportIds.map((id) => {
            const report = data.reports.find((item) => item.id === id && (!reportDate(item) || knownBy(reportDate(item), cutoff)))
            return <span className="replay-source-ref" key={id}>{report ? `${report.title} · 本地研究资料，不公开挂载全文` : '研报未在截止日前核验'}</span>
          })}
        </div>
      </article>)}
      {data.marketAnalysis.limitations.length > 0 && <div className="replay-analysis-limitations"><h3>研究局限</h3><ul>{data.marketAnalysis.limitations.map((text) => <li key={text}>{text}</li>)}</ul></div>}
    </section> : <section className="replay-summary" aria-label="研究摘要"><h2>研究摘要</h2>{data.summary.length ? <ul>{data.summary.map((text) => <li key={text}>{displayResearchText(text, data)}</li>)}</ul> : <p>资料准备中：尚未填入经核验的事件与研究结论。</p>}</section>)}

    <section className="replay-panel" aria-label="判断与反证"><header><h2>判断与反证</h2><span>工作假说，不是既定结论</span></header>{historical ? <p className="replay-empty">历史截面不展示当前判断与反证状态。</p> : data.hypotheses.length ? data.hypotheses.map((hypothesis) => <article className="replay-hypothesis" key={hypothesis.title}><small>{hypothesis.status}</small><h3>{hypothesis.title}</h3><dl><dt>验证条件</dt><dd>{hypothesis.test}</dd><dt>反证 / 失效条件</dt><dd>{hypothesis.invalidator}</dd></dl></article>) : <p className="replay-empty">判断准备中，等待证据支持。</p>}<div className="replay-framework"><h3>宏观框架联查</h3><p>这些链接进入实际宏观模块，当前模块数据不代表历史时点版本。</p>{US_MACRO_PAGES.map((page) => <a key={page.slug} href={`#framework/${page.slug}`}>{page.label} ↗</a>)}</div></section>
    {!historical && <ResearchEvidence items={data.researchEvidence || []} reports={data.reports} sources={sources} events={events} />}
    {!historical && <ResearchEvidence items={data.windResearchEvidence || []} reports={data.reports} channel="Wind" sources={sources} events={events} />}
    {!historical && <ResearchEvidence items={data.wechatResearchEvidence || []} reports={data.reports} channel="微信" coverage={data.wechatCoverage} sources={sources} events={events} />}

    {hasMarketValues && <MarketPaths paths={data.marketPaths!} cutoff={cutoff} historical={historical} />}
    <section className="replay-panel" aria-label="市场路径对照"><header><h2>市场预期与现实路径对照</h2><span>定性证据与量化数据分开</span></header><p className="replay-notice">{hasMarketValues ? '真实序列已接入，逐点观测日、首次发布日期与缺口见上方；会前利率期货隐含路径仍缺失，不把政策目标或事后路径冒充会前市场共识。路径仅供对照，不计算单一事件归因。' : '完整事件窗口量化数据缺失：尚无经核验的会前利率期货隐含路径、全区间美元与美债序列。局部官方快照见事件现实字段；不绘制模拟曲线，不计算全月收益或单一事件归因。'}</p><div className="replay-table-wrap"><table><thead><tr><th>发布日期 / 事件</th><th>当时预期（不等同于市场共识）</th><th>落地现实</th><th>市场反应 / 验证状态</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}><th scope="row">{formatReplayDate(event.date)}<br />{event.title}</th><td>{formatReplayText(evidenceText(event.expectation, event.expectationSourceIds, event.date))}{sourceLinks(event.expectationSourceIds)}</td><td><p>观察期：{formatReplayText(formatReplayDate(event.observationPeriod) || '未注明')} · 不等同于发布日期</p>{formatReplayText(evidenceText(event.reality, event.realitySourceIds))}{sourceLinks(event.realitySourceIds)}</td><td>{historical ? '历史截面隐藏事后市场解释' : event.marketResponse || '缺少量化行情，待验证'}{!historical && event.interpretation && <p>研究解释（非事实）：{displayResearchText(event.interpretation, data)}</p>}</td></tr>)}</tbody></table>{!events.length && <p className="replay-empty">暂无可对照事件。</p>}</div></section>
    <details className="replay-disclosure" aria-label="来源库 / 研报库明细">
    <summary>来源库 / 研报库 · 公开来源 {availableSources.length} / 授权研报 {reports.length}（点击展开）</summary>
    {!historical && <MonthlyReplayResearch data={data} />}
    {!historical && <details className="replay-disclosure" aria-label="逐条预期现实对照">
      <summary>逐条预期 → 现实对照 · {data.realityComparisons?.length || 0}条（点击展开）</summary>
      <section className="replay-panel" aria-label="机构观点与现实逐条对照"><header><h2>机构观点与现实逐条对照</h2><span>保留条件、期限与未到期部分</span></header>
        <p className="replay-notice">原文日期不证明历史首次可得；这是当前追溯比较，不是实时预测胜率或市场共识。同SHA跨渠道不重复计为独立观点；没有核验的现实保持待验。</p>
        {!data.realityComparisons?.length && <p className="replay-empty">暂无独立配对；已核验的观点与现实见三渠道明细及市场路径对照。</p>}
        <div className="replay-table-wrap"><table><thead><tr><th>表述日 / 作者</th><th>预期 / 条件与期限</th><th>现实</th><th>验证状态 / 局限</th><th>原文定位</th></tr></thead><tbody>
          {(data.realityComparisons || []).map((pair) => <tr key={pair.id}><th scope="row">{formatReplayDate(pair.expressedAt) || '表述日未核'}<br />{pair.actor}</th>
            <td>{pair.expectation}<p>期限：{formatReplayText(pair.observationPeriod || '未确认')}</p></td>
            <td>{pair.reality || '尚无经核验现实，待验'}{sourceLinks(pair.realitySourceIds)}</td>
            <td><strong>{pair.status}</strong><p>{pair.limitation}</p></td>
            <td>{data.reports.find((report) => report.id === pair.reportId)?.title || '研究原文待核'}<p>PDF第{pair.pages.join('、')}页</p></td></tr>)}
        </tbody></table></div>
      </section>
    </details>}
    {!historical && <ResearchEvidence items={data.localResearchEvidence || []} reports={data.reports} channel="本地研报" events={events} />}
    {!historical && data.archiveCoverage && <p className="replay-notice">{data.archiveCoverage.channelEntries}条渠道记录，对应{data.archiveCoverage.uniqueDocuments}份不同归档文件（SHA去重）；{data.archiveCoverage.sharedDocuments}组同SHA跨渠道复用。另已核{data.archiveCoverage.textVerifiedAliasCount || 0}条异SHA同文关联；同文不重复计票，文件数不代表独立作品数。</p>}
    <section className="replay-panel replay-library" aria-label="来源与研报库"><header><h2>来源库 / 研报库</h2><label htmlFor="replay-search">检索资料<input id="replay-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="标题、机构、主题、状态" /></label></header><div className="replay-library-grid"><div><h3>公开来源 · {availableSources.length}</h3>{availableSources.map((source) => <article className="replay-source" key={source.id}><small>{formatReplayDate(source.date)} · {source.publisher} · {source.kind}{!historical && ` · ${source.status}`}</small><h4>{source.title}</h4>{source.dateBasis && <p>日期依据：{source.dateBasis}</p>}{!historical && <p>{source.note}</p>}{safeUrl(source.url) ? <a href={source.url} target="_blank" rel="noreferrer">打开原始来源 ↗</a> : <span className="replay-missing">无可用公开URL</span>}</article>)}{!availableSources.length && <p className="replay-empty">暂无匹配的已核验来源。</p>}</div><div><h3>授权研报 · {reports.length}</h3><p className="replay-notice">仅登记本地路径，不公开挂载PDF；需在授权环境中打开。</p>{reports.map((report) => <article className="replay-source" key={`${report.title}-${report.path}`}><small>{report.provider}</small><h4>{report.title}</h4>{!historical && <ReportProvenance report={report} />}<p>{filenameDatePreferred(report) ? '研究归档日期（文件名优先）' : '正文发布日期'}：{formatReplayDate(reportDate(report)) || '未知'}</p>{report.postDate && <p>平台发帖日：{formatReplayDate(report.postDate)}（{filenameDatePreferred(report) && '备查，'}不等同于正文发布日期）</p>}{report.dateConflict && <p className="replay-missing">{filenameDatePreferred(report) ? '日期冲突：文件名日期与平台日期不一致，以文件名归档日期优先；不证明历史可得。' : '日期冲突：原文件名日期与正文日期不一致，以正文发布日期为准；不证明历史首次可得。'}</p>}{report.dateBasis && <p>日期依据：{report.dateBasis}</p>}<p>对象：{report.geography || report.scope || '未注明'} · 主题：{report.topics?.join('、') || report.scope || '未注明'}</p>{!historical && <p>{report.note}</p>}<code>{report.path || '尚无本地文件'}</code></article>)}{!reports.length && <p className="replay-empty">暂无匹配的授权研报。</p>}</div></div></section></details>
    <section className="replay-panel" aria-label="下载渠道状态"><header><h2>下载渠道状态</h2><span>当前获取状态 · 不随历史截止回放</span></header>
      {!historical && data.monthlyCoverage && <MonthlyCoverage coverage={data.monthlyCoverage} />}
      <div className="replay-acquisition">{data.acquisition.map((channel) => <article key={channel.provider}><h3>{channel.provider}</h3><strong>{channel.status}</strong><p>{channel.detail}</p></article>)}{!data.acquisition.length && <p className="replay-empty">渠道核验准备中；不将全站接入状态视为本页已获取数据。</p>}</div></section>
  </article>
}
