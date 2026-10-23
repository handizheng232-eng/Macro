import { render } from '@testing-library/react'
import { queryReplayWorkbench, replayWorkbench, replayToolbar, replayHeading } from './historyReplay.testHelpers'

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
