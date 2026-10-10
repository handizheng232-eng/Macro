import { render, screen } from '@testing-library/react'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'

// TEST ONLY provenance fixture; no empirical data or source quote is supplied.
it('新增原文引用可读到署名、原文日期与页段，不暴露私有提取编号或复制原文', () => {
  const entry = {
    id: 'private-test-entry', date: '2026-09-12', title: '测试日期节点', text: '测试条件性研究解释。',
    sourceIds: [], reportIds: ['test-report'], evidenceRefs: ['private-extract-id'],
    supportingEvidence: [{ id: 'private-extract-id', reportId: 'test-report', actor: '测试正式署名',
      publicationDate: '2026-09-12', locatorLabel: 'PDF物理第2、3页',
      evidenceBasis: '原文定位已核，首次历史可得仍未知' }],
  }
  const data: HistoryReplayData = {
    title: 'TEST ONLY 引用展示', startDate: '2026-09-01', asOf: '2026-10-09', summary: [], events: [], sources: [], hypotheses: [], acquisition: [],
    reports: [{ id: 'test-report', title: '测试原文报告', publicationDate: '2026-09-12', provider: '测试渠道', path: 'test-only.pdf' }],
    marketAnalysis: { title: '综合市场分析', conclusion: '测试综合判断', limitations: [], sections: [{
      id: 'test-topic', title: '测试主题', judgement: '测试判断', expectation: '', reality: '', mechanism: '', divergence: '', implication: '', validation: '',
      sourceIds: [], reportIds: ['test-report'], deepDive: { expectationTimeline: [entry] },
    }] },
  }
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(screen.getByRole('region', { name: '综合市场分析' })).toHaveTextContent('测试正式署名')
  expect(screen.getByRole('region', { name: '综合市场分析' })).toHaveTextContent('原文日期：2026年9月12日')
  expect(screen.getByRole('region', { name: '综合市场分析' })).toHaveTextContent('原文定位：PDF物理第2、3页')
  expect(container).not.toHaveTextContent('private-extract-id')
})

it('精确审校的阅读覆写规范旧日期，原研究文字与数值比不变', () => {
  const raw = '机构9/12给出条件判断，总体/核心为3.4/3.0，2/10年期利差。'
  const data = {
    title: 'TEST ONLY 阅读覆写', startDate: '2026-09-01', asOf: '2026-10-09', summary: [raw],
    events: [], sources: [], hypotheses: [], acquisition: [], reports: [],
    readingTextOverrides: [{ rawText: raw, displayText: '机构9月12日给出条件判断，总体/核心为3.4/3.0，2/10年期利差。', sourceTextSHA256: 'TEST-ONLY-no-empirical-source' }],
  }
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(container).toHaveTextContent('机构9月12日给出条件判断，总体/核心为3.4/3.0，2/10年期利差。')
  expect(data.summary[0]).toBe(raw)
})

it('辅助图的阅读层用正常研究说明，工程化版本记录仍可展开核查', () => {
  const technical = 'TEST ONLY generatedAt/updateDate/releaseDate/null audit metadata'
  const data: HistoryReplayData = { title: 'TEST ONLY 版本阅读', startDate: '1999-01-01', asOf: '1999-01-02', summary: [], events: [], sources: [], hypotheses: [], acquisition: [], reports: [],
    marketAnalysis: { title: '综合市场分析', conclusion: 'TEST ONLY', limitations: [], sections: [{ id: 'test-topic', title: '测试主题', judgement: '', expectation: '', reality: '', mechanism: '', divergence: '', implication: '', validation: '', sourceIds: [], reportIds: [],
      frameworkEvidence: [{ id: 'test-frame', moduleSlugs: [], title: '测试辅助图', explanation: '测试解释', sourceVintageNote: technical, series: [], datasetPins: [], retrospectiveOnly: true }],
    }] },
  }
  render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(screen.getByText(technical)).not.toBeVisible()
  expect(screen.getByText(/图值可能包含修订或加工/)).toBeVisible()
})

it('四条同单位图线有不同视觉标识，不让第四条与第一条重色同线型', () => {
  // TEST ONLY fabricated coordinates exercise styles, never research data.
  const series = Array.from({ length: 4 }, (_, index) => ({
    id: `test-only-series-${index}`, title: `TEST ONLY 系列${index}`, unit: '%', sourceUrl: '', status: 'TEST ONLY', limitations: [],
    observations: [1, 2].map(day => ({ date: `1999-01-0${day}`, value: index + day, releaseDate: null, historicalAsOfEligible: false })),
  }))
  const data: HistoryReplayData = { title: 'TEST ONLY 图线', startDate: '1999-01-01', asOf: '1999-01-02', summary: [], events: [], sources: [], hypotheses: [], acquisition: [], reports: [], marketPaths: { series } }
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  const paths = Array.from(container.querySelectorAll('path[data-series-id]'))
  expect(paths).toHaveLength(4)
  expect(new Set(paths.map(path => `${path.getAttribute('stroke')}|${path.getAttribute('stroke-dasharray')}`)).size).toBe(4)
})
