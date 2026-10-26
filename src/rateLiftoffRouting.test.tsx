import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { afterEach, it, expect } from 'vitest'
import App from './App'
afterEach(cleanup)
it('registers the authorized partial inflation child and strict historical boundary', () => {
  window.history.replaceState(null, '', '#history/inflation-qt-repricing/rate-liftoff-qt-guidance')
  const { container } = render(<App />)
  expect(screen.getByRole('heading', { name: '加息启动与缩表定调', level: 1 })).toBeInTheDocument()
  expect(container.querySelectorAll('[data-analysis-entry]')).toHaveLength(142)
  expect(container.querySelectorAll('[data-period-summary]')).toHaveLength(5)
  expect(container.querySelectorAll('img[data-approved-market-chart]')).toHaveLength(6)
  expect(container.textContent).toContain('父方限定准入 · 阶段性研究发布')
  expect(container.textContent).not.toContain('81份PDF')
  expect(container.textContent).toContain('本版已获阶段性公网发布授权')
  fireEvent.change(screen.getByLabelText('按日期截止查看'), { target: { value: '2022-04-01' } })
  expect(container.querySelector('[data-analysis-entry]')).toBeNull()
  expect(container.querySelector('[data-period-summary]')).toBeNull()
  expect(container.querySelector('img[data-approved-market-chart]')).toBeNull()
  expect(screen.queryByRole('table', { name: '新标准逐月渠道状态' })).not.toBeInTheDocument()
})
it('opens only the authorized parent card as partial publication', () => {
  window.history.replaceState(null, '', '#history/inflation-qt-repricing')
  render(<App />)
  fireEvent.click(screen.getByRole('button', { name: '进入加息启动与缩表定调阶段性研究版' }))
  expect(window.location.hash).toBe('#history/inflation-qt-repricing/rate-liftoff-qt-guidance')
  expect(screen.getByRole('heading', { name: '加息启动与缩表定调', level: 1 })).toBeInTheDocument()
})
