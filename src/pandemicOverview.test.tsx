import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const title = '预防式降息、疫情冲击与政策合流'
afterEach(() => { cleanup(); window.history.replaceState(null, '', '#today') })

describe('pandemic policy overview', () => {
  it('opens from the primary period and preserves sibling and top-level navigation', async () => {
    window.history.replaceState(null, '', '#history')
    render(<App />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: `宏观阶段：${title}` }))
    await user.click(screen.getByRole('button', { name: '进入疫情政策合流阶段细分复盘' }))
    expect(window.location.hash).toBe('#history/pandemic-policy-confluence')
    await user.click(screen.getByRole('button', { name: '下一时期：通胀反击、QT与利率体系重估' }))
    expect(screen.getByRole('heading', { name: '通胀反击、QT与利率体系重估', level: 1 })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: `上一时期：${title}` }))
    expect(screen.getByRole('heading', { name: title, level: 1 })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '返回宏观分期总览' }))
    expect(window.location.hash).toBe('#history')
    expect(screen.queryByRole('heading', { name: title, level: 1 })).not.toBeInTheDocument()
  })
  it('direct-loads six pending periods with continuous precise boundaries and real official citations', () => {
    window.history.replaceState(null, '', '#history/pandemic-policy-confluence')
    const { container } = render(<App />)
    expect(screen.getByRole('heading', { name: title, level: 1 })).toBeInTheDocument()
    const cards = [...container.querySelectorAll('.subperiod-list > article')]
    expect(cards).toHaveLength(6)
    const periods = cards.map(card => card.querySelector('.subperiod-index small')!.textContent!.split('至')).reverse()
    expect(periods[0][0]).toBe('2019-07-31')
    expect(periods.at(-1)![1]).toBe('2022-03-15')
    for (let i = 1; i < periods.length; i++) expect(Date.parse(periods[i][0]) - Date.parse(periods[i - 1][1])).toBe(86400000)
    for (const card of cards) {
      expect(within(card as HTMLElement).getByText('待复盘')).toBeInTheDocument()
      const isAdmittedLocalChild = card.querySelector('h3')?.textContent === '加速Taper与转鹰准备'
      expect(card.querySelectorAll('button')).toHaveLength(isAdmittedLocalChild ? 1 : 0)
      if (isAdmittedLocalChild) expect(within(card as HTMLElement).getByRole('button', { name: '进入加速Taper与转鹰准备阶段性研究版' })).toBeInTheDocument()
      expect(card.querySelectorAll('a').length).toBeGreaterThan(0)
      for (const link of card.querySelectorAll('a')) expect(link.href).toMatch(/^https:\/\/www\.federalreserve\.gov\//)
    }
    expect(screen.getByText(/月界是研究组织边界/)).toBeInTheDocument()
    expect(screen.getByText(/Taper减慢净购债，不等于QT/)).toBeInTheDocument()
  })
})
