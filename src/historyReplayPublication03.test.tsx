import { render, screen, cleanup } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { HistoryReplay } from './historyReplay'
import data from './data/historyReplayRenewedEasingQtEnd.json'
afterEach(cleanup)
it('publishes limited research without claiming full-stage or upgrading the four reference sources', () => {
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(screen.getByLabelText('有限研究发布说明')).toHaveTextContent('有限研究呈现')
  expect(data.experimentStatus.publication).toBe(true)
  expect(data.experimentStatus.fullStageReady).toBe(false)
  expect(data.experimentStatus.wechatAcceptedTotal).toBe(23)
  expect(data.experimentStatus.libraryReviewedCandidateCount).toBe(4)
  expect(data.experimentStatus.wechatPendingAnalysis).toBe(0)
  const nodes = data.marketAnalysis.sections.flatMap(s => Object.values(s.deepDive).flat())
  const added = nodes.filter(n => n.id.startsWith('local03-') || n.id.startsWith('local02-WP'))
  expect(added).toHaveLength(7)
  for (const n of added) {
    expect(container.querySelector(`[data-analysis-entry="${n.id}"] [data-analysis-text]`)?.textContent).toBe(n.text)
    expect(n.firstAvailableDate).toBeNull()
    expect(n.historicalAsOfEligible).toBe(false)
  }
  expect(container.textContent).toContain('未接入CME概率数据')
  expect(container.textContent).toContain('旧中邮相关观点待单独复核')
  expect(data.monthlyCoverage.rows.map(r => r.channels.Wind.bodyCount)).toEqual([15,15,15,14])
  expect(data.monthlyCoverage.rows[3].channels.Wind).toMatchObject({ requiredCount:15, defaultQuotaAccepted:false, effectiveQuotaAccepted:true, quantityException:{acceptedByUser:true,qualityReviewWaived:false} })
}, 30000)
