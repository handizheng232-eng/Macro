import { render } from '@testing-library/react'
import { vi } from 'vitest'
import { queryReplayWorkbench, replayWorkbench, replayToolbar, replayHeading, replayDisclosure, replayRegion, replayNavigation, queryReplayRegion, queryReplayLabel } from './historyReplay.testHelpers'

it('indexes explicit labels once per DOM version without stale or missed duplicates', () => {
  const { rerender } = render(<><article aria-label="工作台" /><details aria-label="明细" /></>)
  const scan = vi.spyOn(document, 'querySelectorAll')
  try {
    replayWorkbench('工作台')
    replayDisclosure('明细')
    replayWorkbench('工作台')
    expect(scan.mock.calls.filter(([selector]) => selector.includes('aria-label'))).toHaveLength(1)
    // Attribute-only mutations do not produce childList records. Refresh the
    // candidate index for labels, but never cache role/name/visibility results.
    const workbench = replayWorkbench('工作台')
    workbench.setAttribute('aria-label', '改名工作台')
    expect(queryReplayWorkbench('工作台')).toBeNull()
    expect(replayWorkbench('改名工作台')).toBe(workbench)
    workbench.setAttribute('role', 'region')
    expect(() => replayWorkbench('改名工作台')).toThrow()
    workbench.removeAttribute('role')
    workbench.setAttribute('aria-hidden', 'true')
    expect(() => replayWorkbench('改名工作台')).toThrow()
    workbench.removeAttribute('aria-hidden')
    expect(replayWorkbench('改名工作台')).toBe(workbench)
    rerender(<><article aria-label="新工作台" /><details aria-label="明细" /><div aria-label="明细" /></>)
    expect(queryReplayWorkbench('工作台')).toBeNull()
    expect(replayWorkbench('新工作台')).toBeInTheDocument()
    expect(() => replayDisclosure('明细')).toThrow()
    rerender(<article aria-label="新工作台" aria-labelledby="title"><h1 id="title">错误名称</h1></article>)
    expect(() => replayWorkbench('新工作台')).toThrow()
    rerender(<article aria-label="新工作台" style={{ display: 'none' }} />)
    expect(() => replayWorkbench('新工作台')).toThrow()
    rerender(<div />)
    expect(queryReplayWorkbench('新工作台')).toBeNull()
  } finally { scan.mockRestore() }
})

it('indexed region and navigation lookups preserve role, name, visibility and uniqueness', () => {
  const { rerender } = render(<><section aria-label="路径" /><nav aria-label="主导航"><button>今日总览</button></nav></>)
  expect(replayRegion('路径')).toHaveRole('region')
  expect(replayNavigation('主导航').getByRole('button', { name: '今日总览' })).toBeInTheDocument()
  rerender(<div aria-label="路径" />)
  expect(() => replayRegion('路径')).toThrow()
  rerender(<section aria-label="路径" aria-labelledby="other"><h2 id="other">错误名称</h2></section>)
  expect(() => replayRegion('路径')).toThrow()
  rerender(<section aria-label="路径" hidden />)
  expect(() => replayRegion('路径')).toThrow()
  rerender(<><section aria-label="路径" /><section aria-label="路径" /></>)
  expect(() => queryReplayRegion('路径')).toThrow()
  expect(() => queryReplayLabel('路径')).toThrow()
  rerender(<div />)
  expect(queryReplayRegion('路径')).toBeNull()
  expect(queryReplayLabel('路径')).toBeNull()
  expect(() => replayRegion('路径')).toThrow()
  expect(() => replayNavigation('主导航')).toThrow()
})

it('workbench lookup retains unique label, article role and accessibility checks', () => {
  const { rerender } = render(<article aria-label="测试工作台">内容</article>)
  expect(replayWorkbench('测试工作台')).toHaveAccessibleName('测试工作台')
  rerender(<><article aria-label="测试工作台" /><article aria-label="测试工作台" /></>)
  expect(() => replayWorkbench('测试工作台')).toThrow()
  rerender(<section aria-label="测试工作台" />)
  expect(() => replayWorkbench('测试工作台')).toThrow()
  rerender(<article aria-label="测试工作台" aria-labelledby="other"><h1 id="other">错误名称</h1></article>)
  expect(() => replayWorkbench('测试工作台')).toThrow()
  rerender(<article aria-label="测试工作台" aria-hidden="true" />)
  expect(() => replayWorkbench('测试工作台')).toThrow()
  rerender(<div />)
  expect(() => replayWorkbench('测试工作台')).toThrow()
  expect(queryReplayWorkbench('测试工作台')).toBeNull()
})

it.each([
  { query: replayToolbar, className: 'replay-toolbar' },
  { query: replayHeading, className: 'replay-heading' },
])('scoped $className queries retain uniqueness and actual role/name queries', ({ query, className }) => {
  const { rerender } = render(<div className={className}><button>操作</button></div>)
  expect(query().getByRole('button', { name: '操作' })).toHaveAccessibleName('操作')
  rerender(<div className={className}><button>操作</button><button>操作</button></div>)
  expect(() => query().getByRole('button', { name: '操作' })).toThrow()
  rerender(<><div className={className} /><div className={className} /></>)
  expect(query).toThrow()
  rerender(<div />)
  expect(query).toThrow()
})
