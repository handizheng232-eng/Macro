import { fireEvent, render, screen, within } from '@testing-library/react'
import * as inflation from './usInflation'
import data from './data/usInflationData.json'
import fixture from '../scripts/fixtures/cpi_sa_bls_2026.json'

it('区分当期CPI季调环比、缺基期同比与PCE自身观察月', () => {
  expect(inflation).toHaveProperty('CpiReleaseStatus')
  render(<inflation.CpiReleaseStatus status={fixture.releaseStatus} audit={fixture.cpiAudit} />)
  const status = screen.queryByRole('complementary', { name: 'CPI本期发布状态' })
  expect(status).not.toBeNull()
  expect(status).toHaveTextContent('2026-10')
  expect(status).toHaveTextContent('0.4%')
  expect(status).toHaveTextContent('0.3%')
  expect(status).toHaveTextContent('2025年10月')
  expect(status).toHaveTextContent('基期')
  expect(status).toHaveTextContent('PCE')
  expect(status).toHaveTextContent('2026-09')
  expect(status).toHaveTextContent('2026-11-12')
  expect(status).toHaveTextContent('2026-11-14')
  expect(within(status!).getByRole('link', { name: 'BLS缺报说明' })).toHaveAttribute('href', fixture.releaseStatus.officialExplanationUrl)
})

it('温度表保留缺失同比，精确展示21SA及2NSA和Miscellaneous实体', () => {
  const { container } = render(<inflation.CpiHeatmapTable table={fixture.heatmapSlice} />)
  expect(container.querySelectorAll('thead th')).toHaveLength(5)
  expect(container.querySelector('tbody tr .heat-value')).toHaveTextContent('—')
  fireEvent.click(screen.getByRole('button', { name: '季调环比' }))
  expect(screen.getByRole('group', { name: 'CPI分项温度表口径' })).toHaveTextContent('除标记项目外')
  expect(screen.getAllByText('未季调', { exact: true })).toHaveLength(2)
  expect(container.querySelector('tbody tr .heat-value')).toHaveTextContent('0.4')
  const labels = container.querySelectorAll('tbody th[scope="row"]')
  expect(labels).toHaveLength(23)
  labels.forEach((label, i) => {
    expect(label).toHaveAttribute('title', expect.stringContaining(fixture.heatmapSlice.history.rows[i].source.momCode))
    expect(label).toHaveAttribute('title', expect.stringContaining('季调'))
    const nsa = ['food_away_yoy', 'personal_services_yoy'].includes(fixture.heatmapSlice.history.rows[i].id)
    expect(label).toHaveAttribute('title', expect.stringContaining(nsa ? 'NSA' : '（SA）'))
    if (nsa) expect(label).toHaveTextContent('未季调')
  })
  const misc = Array.from(labels).find(label => label.textContent?.includes('杂项个人服务'))!
  expect(misc).toHaveAttribute('title', expect.stringContaining('Miscellaneous personal services'))
  expect(misc.textContent).not.toContain('Miscellaneous')
  expect(container).toHaveTextContent('单一普通环比源')
  expect(container).toHaveTextContent('2026-10官方例外核对')
  expect(container).toHaveTextContent('未季调原值')
  expect(container).not.toHaveTextContent('两行本期未季调')
  expect(container).toHaveTextContent('未来发布')
  expect(container).toHaveTextContent('不外推至所有历史发布版本')
  expect(container).toHaveTextContent('旧权重仅参考，不用于贡献计算')
})

it('残余季节性柱图披露样本数，零样本不画伪造的零值柱', () => {
  expect(inflation).toHaveProperty('JanuaryEffectChart')
  const chart = { ...data.actual.januaryEffect, months: [1, 2], series: [
    { id: 'test', label: '测试样本', values: [0, null], sampleCounts: [1, 0], color: '#777' },
  ] }
  const { container } = render(<inflation.JanuaryEffectChart chart={chart} />)
  expect(screen.getByText('逐月有效样本数')).toBeInTheDocument()
  expect(container.querySelectorAll('svg rect')).toHaveLength(1)
  expect(container).toHaveTextContent('1月：1')
  expect(container).toHaveTextContent('2月：0')
})

it('正式页面使用当前数据状态，而不是把十月回归样本写死在页面上', () => {
  render(<inflation.UsInflationDetail onBack={() => undefined} />)
  const status = screen.getByRole('complementary', { name: 'CPI本期发布状态' })
  const period = data.actual.releaseStatus.period
  expect(status).toHaveTextContent(`${period.slice(0, 4)}-${period.slice(4, 6)}`)
  expect(status).toHaveTextContent(data.dataQuality.cpiSeasonality.checkedAt.slice(0, 10))
  expect(status).toHaveTextContent(data.actual.releaseStatus.cpiMomCode)
})

it('贡献图不把核算差额堆成第五项经济贡献，并披露历史未闭合区间', () => {
  const { container } = render(<inflation.UsInflationDetail onBack={() => undefined} />)
  const card = container.querySelector('.contribution-chart-card')!
  expect(card.querySelector('.contribution-legend')).not.toHaveTextContent('残差/未覆盖')
  expect(card.querySelectorAll('.contribution-legend > span')).toHaveLength(5)
  expect(card).toHaveTextContent(data.actual.cpiContributions.reconciliation.note)
  expect(card).toHaveTextContent('未核实')
})
