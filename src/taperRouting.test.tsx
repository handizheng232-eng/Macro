import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { afterEach, it, expect } from 'vitest'
import App from './App'
afterEach(cleanup)
it('opens the pandemic child with mature reading controls and unloads retrospective material', () => {
  window.history.replaceState(null, '', '#history/pandemic-policy-confluence/accelerated-taper-hawkish-preparation')
  const { container } = render(<App />)
  expect(screen.getByRole('heading', {name:'加速Taper与转鹰准备',level:1})).toBeInTheDocument()
  expect(container.querySelectorAll('[data-period-summary]')).toHaveLength(5)
  expect(container.querySelectorAll('img[data-approved-market-chart]')).toHaveLength(6)
  fireEvent.change(screen.getByLabelText('按日期截止查看'), {target:{value:'2022-02-01'}})
  expect(container.querySelector('[data-period-summary]')).toBeNull()
  expect(container.querySelector('img[data-approved-market-chart]')).toBeNull()
  expect(container.querySelector('[data-analysis-entry]')).toBeNull()
  expect(screen.getByText('本篇尚无获准的当时信息集；不以观察日或材料日期补造首次可得。')).toBeInTheDocument()
})
