# Macro replay data contract

The user-approved template for all future replays is the second chapter, `#history/easing-to-tightening/hawkish-transition` (2026-01-01 through 2026-08-31). Its structure, five analytical themes, monthly expectation–reality paths, revision chains, three-channel archive quotas and historical boundaries are specified in `docs/macro-replay-template.md`. This replaces the previous first-chapter reference; it does not automatically rewrite the first chapter or authorize expansion to new periods.

Both this route and `#history/easing-to-tightening/policy-reversal` are implemented. The period-specific examples below describe the first chapter, not mandatory counts for later chapters. Build `historyReplay.json` from verified local archives with `python scripts/build_history_replay.py`; build the second chapter using explicit parent-source and reviewed-research manifests in `scripts/build_hawkish_replay.py`. Do not overwrite verified artifacts with placeholders. TypeScript interfaces are exported from `src/historyReplay.tsx`. Private archives remain excluded from public git and Pages; see `release/README.md` for local physical verification versus public CI receipt checks.

```ts
{
  title: string,
  startDate: string, // YYYY-MM-DD; provisional boundary
  asOf: string, // YYYY-MM-DD verification cutoff; "" only while preparing
  summary: string[],
  sources: [{ id: string, title: string, publisher: string, date: string,
    url: string, kind: string, status: string, note: string,
    historicalAsOfEligible?: boolean, dateBasis?: string }],
  events: [{ id: string, date: string, title: string, observationPeriod: string,
    expectation: string, expectationSourceIds: string[],
    reality: string, realitySourceIds: string[], interpretation: string,
    marketResponse: string, confidence: string }],
  hypotheses: [{ title: string, test: string, invalidator: string, status: string }],
  acquisition: [{ provider: string, status: string, detail: string }],
  reports: [{ id?: string, title: string, date?: string | null,
    publicationDate?: string | null, postDate?: string | null,
    filenameDate?: string | null, dateConflict?: boolean, historicalAsOfEligible?: boolean,
    dateBasis?: string, provider: string, path: string, scope?: string,
    geography?: string, topics?: string[], note?: string }],
  researchEvidence?: ReplayResearchEvidence[], // export defined in historyReplay.tsx
  windResearchEvidence?: ReplayResearchEvidence[], // separately audited Wind opinions
  wechatResearchEvidence?: ReplayResearchEvidence[], // only verified original article bodies
  wechatCoverage?: { requestedAccounts: [{ accountRequested: string,
    officialIdentityChecked: boolean, bodyObtainedCount: number, status: string, limitations: string }],
    actualAccounts: [{ accountActual: string, articleCount: number }],
    totalArticles: number, totalOpinions: number, limitations: string[] },
  marketAnalysis?: { title: string, conclusion: string,
    sections: [{ id: string, title: string, judgement: string, expectation: string,
      reality: string, mechanism: string, divergence: string, implication: string,
      validation: string, sourceIds: string[], reportIds: string[] }], limitations: string[] },
  marketPaths?: ReplayMarketPaths // three verified series, per-observation dates
}
```

Fields marked `?` are optional. Arrays may be empty. IDs must be unique; evidence source IDs must refer to existing sources. Event dates are release days, not observation periods. For star-platform archives, the user's requested filename-date priority determines the displayed archival date (`filenameDate` and `date`), not the verified body-publication date. Platform dates remain in `postDate`, with `dateConflict` when different; `publicationDate:null` remains authoritative for the unverified body date. There are 117 complete valid filename dates, eight platform conflicts and four unresolved malformed tokens; never repair a malformed identifier or fill it from a platform date. `historicalAsOfEligible:false` withholds star documents from strict historical cutoffs because a filename does not establish first availability. `source.date` requires an explicit date basis when it represents the event/speech date rather than the archived version's first-publication date. Do not invent probabilities, prices or dates.

Expectations display only when every cited source is published strictly BEFORE the event date. With day-only timestamps, same-day sources cannot prove ex ante availability and are conservatively withheld. Reality displays only when all sources are available by selected cutoff. Include source URLs as actual public http(s) URLs, or empty strings when none; local/file/other schemes never become links.

`reports.path` is only text, NEVER an href, public asset or mounted PDF. `acquisition` is current operational status, not historical evidence. The public library only lists http(s) sources. Authorized PDF bibliography lives in the adjacent report library. `researchEvidence` preserves actor, expression-date basis, short excerpt, physical pages, limitations and the associated reality/pending event; it is only displayed in current retrospective mode.

`windResearchEvidence` contains five audited, named post-September-16 opinions, separate from the twelve star-platform observations. Two future-policy results remain null; three later observations are limited context rather than complete prediction verification. The build checks PDF hash identity, publication date, exact local path, physical-page bounds, linked event/source IDs and report-before-reality chronology. Wind bibliography topics separate verified substantive coverage from retrieval-keyword ownership and preserve domestic/global geography. The current artifact has 176 channel-specific bibliographic entries; this is not a cross-channel deduplicated report count.

`wechatResearchEvidence` contains 22 named opinions from 13 official article text bodies obtained through normally authenticated active sessions on October 2, 2026. The original five Changjiang bodies/six views remain unchanged; the expanded bibliography adds eight bodies/sixteen views from Guo Lei Macro (two), CICC Insights (three), Zeping Macro (one) and Chief Economists Forum (two). Preserve actual account identity, research origin and original/repost distribution separately; CICC Insights is not relabeled as the requested CICC Macro account, and the forum is not an extra independent research institution. Author, original article day, saved body SHA256, paragraph references and short excerpts are independently checked; images have not been OCRed. All sixteen added views retain null reality pairs rather than invented forecast outcomes. Unlike PDF evidence, references render as paragraphs rather than physical pages. Structured `value` fields may be arrays of conditions as well as scalar values or objects. The report/source URLs remain empty where publishing the retrieved link would retain an authorization query. The archive records the official account, original path and independent header screenshot instead. All three opinion collections are independently collapsed by default and are unmounted in strict historical mode; present captures do not establish historical first-availability or unchanged original versions.

`wechatCoverage` projects the ten requested names from the real acquisition audit and computes counts from verified bodies, not search hits. Actual publisher counts and requested-name coverage remain separate; seven requested accounts have no qualified own-account body in this sample, which does not prove an absence of relevant articles. The source pool is open and may expand beyond the requested names. Coverage and the nested candidate audit are current acquisition metadata, not a historical information set.

`marketPaths.series` contains Treasury 2Y/10Y (21 September trading observations each, `percent_per_annum`) and the broad nominal dollar index (18 available observations through September 25, `index_Jan2006_100`, not DXY). Nulls are never interpolated. Rates share one percent axis; the dollar uses a separate index axis. Every historical observation must have `historicalAsOfEligible:true` and a confirmed `releaseDate<=cutoff`; observation date or present retrieval date cannot substitute. Treasury first-release dates are unverified, so those values are withheld in historical mode. Event windows are daily comparisons, not instantaneous causal effects. The CME historical implied-policy path remains missing.

Historical cutoff applies to events, source library, and report library. Earlier cutoffs suppress current summaries, hypotheses, interpretations, confidence labels and market responses. This is conservative day-level evidence filtering, NOT a full vintage store. Source content must retain its original publication version. Current framework links explicitly warn that macro modules are not point-in-time vintages.

`marketAnalysis` integrates named star-platform, Wind and official WeChat opinions with official facts across policy, inflation, demand/labor supply, the Treasury curve and the dollar. Every topic carries expectation, reality, mechanism, disagreement, implication and validation fields with resolvable references. Each topic now cites its verified original WeChat body, without treating the same research distributed as a local PDF and an article as independent evidence. Its current full-window judgments are withheld in strict historical mode. Rate-endpoint changes, curve spreads and broad-dollar returns are checked against the actual archived series by the Python regression tests. Star-date decisions are recorded in the private `核验/知识星球/文件名日期优先审计.json`. A compact four-step method diagram starts the page; integrated analysis remains expanded before the event timeline. The three channel-detail disclosures and the source/report library default closed.

The artifact is populated with the verified 2026-09-01 through 2026-10-01 research snapshot. Test-only artificial fixtures live exclusively in the test source. The boundary remains open but the research cutoff does not advance automatically.

## Rebuild and verify

The private archive is under `美国宏观复盘/降息起步后的双向政策时代/2026-09_至今/` and is intentionally excluded from git/public hosting. Preserve it locally; the build script reads its public-source evidence, checked PDF manifest and sampled Wind news manifest. It performs no network calls or credential reads.

Run `python scripts/verify_changjiang_archive.py`, the archive's `资料/公开来源/verify_public_evidence.py`, `核验/微信公众号/verify_wechat_evidence.py` (unchanged original five) and `核验/微信公众号/verify-wechat-expanded.py` (eight additions), `python scripts/test_build_history_replay.py`, `python scripts/build_history_replay.py`, then `npm run test`, `npm run lint`, and `npm run build`. `scripts/verify_history_replay.mjs` checks the actual browser artifact: report/evidence/chart counts, default-closed native disclosures and actual expansion, framework/analysis placement, filename-priority/conflict labels, original WeChat paragraph evidence, multi-account coverage and candidate-audit toggling, dated cutoff eligibility, FINAL transcript exclusion, PDF privacy, navigation, console errors and desktop/mobile geometry. Its optional `PLAYWRIGHT_MODULE` and `CHROMIUM_EXE` variables select an already-installed QA browser, not a source session.

Source limitations are part of the artifact: BLS search excerpts are not full tables; Wind news are a relevance-ranked sample, not downloaded brokerage reports; subscription channels can be blocked independently of public sources. Confirm additional channel downloads before changing acquisition status.
