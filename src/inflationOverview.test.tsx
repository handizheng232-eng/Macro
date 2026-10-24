import { act, fireEvent, render, screen, within } from '@testing-library/react'
import App from './App'

const route = '#history/inflation-qt-repricing'
const title = '通胀反击、QT与利率体系重估'
const stages = [
  ['加息启动与缩表定调', '2022-03-16', '2022-05-31'],
  ['激进加息与QT并行', '2022-06-01', '2022-11-30'],
  ['加息降速与终点之争', '2022-12-01', '2023-02-28'],
  ['银行压力与紧缩权衡', '2023-03-01', '2023-06-30'],
  ['高利率维持与长端重估', '2023-07-01', '2023-10-31'],
  ['通胀降温与降息路径浮现', '2023-11-01', '2023-12-31'],
  ['通胀反复与降息等待', '2024-01-01', '2024-05-31'],
  ['QT减速与降息准备', '2024-06-01', '2024-09-17'],
]

it('直达八段分期方案，日期连续、全部待复盘且没有假详情入口', () => {
  window.history.replaceState(null, '', route)
  render(<App />)
  expect(screen.getByRole('heading', { level: 1, name: title })).toBeInTheDocument()
  const region = screen.getByRole('region', { name: '通胀反击阶段细分时段' })
  const cards = within(region).getAllByRole('article')
  expect(cards).toHaveLength(8)
  for (const [name, start, end] of stages) {
    const card = cards.find((node) => within(node).queryByRole('heading', { name }))!
    expect(card).toBeDefined()
    expect(card).toHaveTextContent(`${start}至${end}`)
    expect(within(card).getByText('待复盘')).toBeInTheDocument()
    expect(within(card).queryAllByRole('button')).toHaveLength(0)
    const links = within(card).getAllByRole('link')
    for (const link of links) expect(link.getAttribute('href')).toMatch(/^https:\/\/www\.federalreserve\.gov\//)
  }
  expect(screen.getByText(/非官方经济周期划分/)).toBeInTheDocument()
  expect(screen.getByText(/月界是研究组织边界/)).toBeInTheDocument()
  const ascending = [...cards].reverse()
  expect(ascending.map((card) => card.querySelector('h3')?.textContent)).toEqual(stages.map((s) => s[0]))
  for (let i = 1; i < stages.length; i++) expect(Date.parse(stages[i][1]) - Date.parse(stages[i - 1][2])).toBe(86400000)
})

it('一级入口、返回与兄弟时期在hash事件中保持正确层级', () => {
  window.history.replaceState(null, '', '#history')
  render(<App />)
  fireEvent.click(screen.getByRole('button', { name: `宏观阶段：${title}` }))
  fireEvent.click(screen.getByRole('button', { name: '进入通胀反击阶段细分复盘' }))
  expect(window.location.hash).toBe(route)
  expect(screen.getByRole('navigation', { name: '历史复盘层级' })).toHaveTextContent(title)
  fireEvent.click(screen.getByRole('button', { name: '下一时期：降息起步后的双向政策时代' }))
  expect(window.location.hash).toBe('#history/easing-to-tightening')
  expect(screen.getByRole('heading', { level: 1, name: '降息起步后的双向政策时代' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: `上一时期：${title}` }))
  expect(window.location.hash).toBe(route)
  fireEvent.click(screen.getByRole('button', { name: '返回宏观分期总览' }))
  expect(window.location.hash).toBe('#history')
  window.history.replaceState(null, '', route)
  act(() => window.dispatchEvent(new PopStateEvent('popstate')))
  expect(screen.getByRole('heading', { level: 1, name: title })).toBeInTheDocument()
  window.history.replaceState(null, '', '#history/easing-to-tightening')
  act(() => window.dispatchEvent(new HashChangeEvent('hashchange')))
  expect(screen.getByRole('button', { name: '进入再降息与QT收官研究工作台' })).toBeInTheDocument()
})
