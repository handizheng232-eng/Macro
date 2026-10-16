import { fireEvent, render, screen } from '@testing-library/react'
import { HistoryReplay, type HistoryReplayData } from './historyReplay'

// Display-only fixture: no empirical observations or forecasts.
it('开篇小标题与各段一一对应，正文不变，历史模式连同标题卸载', () => {
  const data = fixture('测试政策原因。\n\n测试市场定价。')
  Object.assign(data.marketAnalysis!, { conclusionHeadings: ['政策原因｜主要矛盾', '市场定价｜预期调整'] })
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(Array.from(container.querySelectorAll('.replay-analysis-conclusion h3'), node => node.textContent)).toEqual(['政策原因｜主要矛盾', '市场定价｜预期调整'])
  expect(Array.from(container.querySelectorAll('.replay-analysis-conclusion > p'), node => node.textContent)).toEqual(['测试政策原因。', '测试市场定价。'])
  expect(container.querySelector('.replay-analysis-conclusion h3')!.nextElementSibling).toHaveTextContent('测试政策原因。')
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '1999-01-02' } })
  expect(screen.queryByText('政策原因｜主要矛盾')).not.toBeInTheDocument()
})

function fixture(conclusion: string): HistoryReplayData {
  return {
    title: '测试阶段', startDate: '1999-01-01', asOf: '1999-01-31',
    summary: [], sources: [], reports: [], events: [], acquisition: [], hypotheses: [],
    marketAnalysis: { title: '测试综合分析', conclusion, limitations: [], sections: [] },
  }
}

it('开篇总述按空行显示独立段落，完整保留顺序与原始数据', () => {
  const paragraphs = ['测试主要矛盾及其变化原因。', '测试政策风险权衡与工具。', '测试市场定价及有条件的资产传导。']
  const data = fixture(paragraphs.join('\n\n'))
  const before = JSON.stringify(data)
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(Array.from(container.querySelectorAll('.replay-analysis-conclusion > p'), (node) => node.textContent)).toEqual(paragraphs)
  expect(JSON.stringify(data)).toBe(before)
})

it.each(['测试旧单段总结。', '测试第一段。\r\n\r\n测试第二段。', '测试第一段。\n\n  \n\n测试第二段。'])('兼容单段、Windows换行及空白段，不生成空段落', (conclusion) => {
  const { container } = render(<HistoryReplay data={fixture(conclusion)} onBack={() => {}} />)
  const paragraphs = Array.from(container.querySelectorAll('.replay-analysis-conclusion > p'), (node) => node.textContent)
  expect(paragraphs).toEqual(conclusion.split(/\r?\n\s*\r?\n/).filter(text => text.trim()))
  expect(paragraphs.every(text => text?.trim())).toBe(true)
})

it('完整开篇总述在严格历史截面卸载，恢复后按原顺序出现', () => {
  const data = fixture('测试背景。\n\n测试资产传导。')
  const { container } = render(<HistoryReplay data={data} onBack={() => {}} />)
  expect(container.querySelector('.replay-analysis-conclusion')).toHaveTextContent('测试背景。')
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '1999-01-02' } })
  expect(container.querySelector('.replay-analysis-conclusion')).toBeNull()
  expect(screen.queryByText('测试资产传导。')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '恢复资料截止日' }))
  expect(Array.from(container.querySelectorAll('.replay-analysis-conclusion > p'), node => node.textContent)).toEqual(['测试背景。', '测试资产传导。'])
})
