import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { StrictMode } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { ReplayCommentsLayout, COMMENT_ROUTE } from './replayComments'
import commentsCss from './replayComments.css?raw'

it('only mounts configured custom editor on opted-in current article, and historical mode removes it', async () => {
  vi.stubEnv('VITE_CUSTOM_COMMENTS_ENABLED', 'true')
  vi.stubEnv('VITE_COMMENTS_API', 'https://worker.example')
  vi.stubGlobal('fetch', vi.fn(async () => ({ok: true, json: async () => ({nodes: [], totalCount: 0, pageInfo: {hasNextPage: false, endCursor: null}})})))
  const {container, rerender} = render(<ReplayCommentsLayout route={COMMENT_ROUTE} historical={false}>正文</ReplayCommentsLayout>)
  fireEvent.click(screen.getByRole('button', {name: '展开在线评论'}))
  expect(await screen.findByRole('textbox', {name: '发表留言'})).toBeInTheDocument()
  expect(container.querySelector('giscus-widget')).toBeNull()
  rerender(<ReplayCommentsLayout route={COMMENT_ROUTE} historical>正文</ReplayCommentsLayout>)
  expect(screen.queryByRole('textbox')).toBeNull()
})

it('scopes a left outline and wider right comments rail to this article', () => {
  expect(commentsCss).toMatch(/\.replay-comments-layout > \.replay-reading-controls\s*\{[^}]*padding-left: 264px;[^}]*padding-right: 0;/)
  expect(commentsCss).toMatch(/\.replay-comments-layout > \.replay-reading-controls \.replay-outline\s*\{[^}]*float: left;[^}]*margin-left: -264px;/)
  expect(commentsCss).toContain('clamp(360px, 25vw, 420px)')
})

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); vi.unstubAllEnvs(); vi.unstubAllGlobals() })
it('opts in by exact route, preserves research, and excludes current comments from history', () => {
  const { rerender } = render(<ReplayCommentsLayout route={COMMENT_ROUTE} historical={false}><article>研究正文</article></ReplayCommentsLayout>)
  expect(screen.queryByText(/等待 giscus App 授权/)).toBeNull()
  expect(screen.getByText('研究正文')).toBeInTheDocument()
  expect(screen.getByRole('complementary', { name: '公开留言与讨论' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '在 GitHub 打开本篇讨论 ↗' })).toHaveAttribute('href', 'https://github.com/handizheng232-eng/Macro/discussions/1')
  expect(screen.getByRole('link', { name: '修改／删除我的评论（前往 GitHub）↗' })).toHaveAttribute('href', 'https://github.com/handizheng232-eng/Macro/discussions/1')
  expect(screen.getByText(/当前嵌入框不提供直接编辑或删除/)).toBeVisible()
  expect(screen.getByText(/点击评论框的提交按钮后/)).toBeInTheDocument()
  expect(screen.getByText(/点击评论框的提交按钮后/)).not.toBeVisible()
  rerender(<ReplayCommentsLayout route={COMMENT_ROUTE} historical><article>研究正文</article></ReplayCommentsLayout>)
  expect(screen.queryByRole('complementary')).toBeNull()
  rerender(<ReplayCommentsLayout route={`${COMMENT_ROUTE}-other`} historical={false}><article>其他篇</article></ReplayCommentsLayout>)
  expect(screen.queryByRole('complementary')).toBeNull()
})

it('fails closed while installation is pending, and mounts one fixed-number widget when ready', async () => {
  const { container, rerender } = render(<ReplayCommentsLayout route={COMMENT_ROUTE} historical={false} appReady={false}>正文</ReplayCommentsLayout>)
  expect(screen.getByText(/等待 giscus App 授权/)).toBeInTheDocument()
  expect(container.querySelector('giscus-widget')).toBeNull()
  rerender(<StrictMode><ReplayCommentsLayout route={COMMENT_ROUTE} historical={false} appReady>正文</ReplayCommentsLayout></StrictMode>)
  fireEvent.click(screen.getByRole('button', { name: '展开在线评论' }))
  await waitFor(() => expect(container.querySelector('giscus-widget')?.shadowRoot?.querySelector('iframe')).toBeTruthy())
  const widget = container.querySelector('giscus-widget')!
  expect(container.querySelectorAll('giscus-widget')).toHaveLength(1)
  const iframe = widget.shadowRoot!.querySelector('iframe')!
  const url = new URL(iframe.src)
  expect(url.searchParams.get('number')).toBe('1')
  expect(url.searchParams.get('repoId')).toBe('R_kgDOUe7w2Q')
  expect(url.searchParams.get('categoryId')).toBe('DIC_kwDOUe7w2c4DLS_J')
  expect(url.searchParams.get('inputPosition')).toBe('top')
  const theme = url.searchParams.get('theme') || ''
  expect(theme).toMatch(/^data:text\/css;charset=utf-8,/)
  expect(decodeURIComponent(theme)).toContain('@import url("https://giscus.app/themes/light.css")')
  expect(decodeURIComponent(theme)).toMatch(/\.gsc-comment-box-textarea\s*\{[^}]*min-height: 280px !important;/)
  expect(url.pathname).toBe('/zh-CN/widget')
  const message = (origin: string, source: Window | null, number = 1) => window.dispatchEvent(new MessageEvent('message', { origin, source, data: { giscus: { discussion: { number, url: 'https://github.com/handizheng232-eng/Macro/discussions/1' } } } }))
  act(() => { message('https://evil.example', iframe.contentWindow); message('https://giscus.app', window); message('https://giscus.app', iframe.contentWindow, 2) })
  expect(screen.queryByText('在线讨论已连接')).toBeNull()
  // Live giscus metadata identifies the discussion by URL, without a number field.
  act(() => window.dispatchEvent(new MessageEvent('message', { origin: 'https://giscus.app', source: iframe.contentWindow, data: { giscus: { discussion: { url: 'https://github.com/handizheng232-eng/Macro/discussions/1' } } } })))
  expect(screen.getByText('在线讨论已连接')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '刷新评论' }))
  await waitFor(() => expect(container.querySelector('giscus-widget')?.shadowRoot?.querySelector('iframe')).toBeTruthy())
  expect(iframe.isConnected).toBe(false)
  expect(container.querySelectorAll('giscus-widget')).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: '收起在线评论' }))
  expect(container.querySelector('giscus-widget')).toBeNull()
})

it('preserves the exact article hash after the vendor callback cleanup, without handling credentials', async () => {
  await import('giscus')
  window.history.replaceState(null, '', `#${COMMENT_ROUTE}`)
  // Model only the vendor's documented URL cleanup, never supply or inspect auth data.
  vi.spyOn(customElements.get('giscus-widget')!.prototype, 'setupSession').mockImplementation(() => window.history.replaceState(null, '', window.location.pathname))
  render(<ReplayCommentsLayout route={COMMENT_ROUTE} historical={false} appReady>正文</ReplayCommentsLayout>)
  fireEvent.click(screen.getByRole('button', { name: '展开在线评论' }))
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })
  expect(window.location.hash).toBe(`#${COMMENT_ROUTE}`)
})

it('does not treat iframe load or a timeout as success; errors stay readable and retry remounts', async () => {
  const { container } = render(<ReplayCommentsLayout route={COMMENT_ROUTE} historical={false} appReady>正文</ReplayCommentsLayout>)
  fireEvent.click(screen.getByRole('button', { name: '展开在线评论' }))
  await waitFor(() => expect(container.querySelector('giscus-widget')?.shadowRoot?.querySelector('iframe')).toBeTruthy())
  const iframe = container.querySelector('giscus-widget')!.shadowRoot!.querySelector('iframe')!
  fireEvent.load(iframe)
  expect(screen.queryByText('在线讨论已连接')).toBeNull()
  act(() => window.dispatchEvent(new MessageEvent('message', { origin: 'https://giscus.app', source: iframe.contentWindow, data: { giscus: { error: 'test fixture: unavailable' } } })))
  expect(screen.getByText(/评论服务暂不可用/)).toBeInTheDocument()
  expect(screen.queryByText(/test fixture/)).toBeNull()
  vi.useFakeTimers()
  fireEvent.click(screen.getByRole('button', { name: '重新连接' }))
  await act(async () => { await Promise.resolve() })
  act(() => vi.advanceTimersByTime(15000))
  expect(screen.getByText(/尚未收到讨论确认/)).toBeInTheDocument()
  expect(screen.queryByText('在线讨论已连接')).toBeNull()
  expect(iframe.isConnected).toBe(false)
})

it('cleans message listeners, iframe and timers on strict-history and route switches', async () => {
  const add = vi.spyOn(window, 'addEventListener')
  const remove = vi.spyOn(window, 'removeEventListener')
  const { container, rerender } = render(<StrictMode><ReplayCommentsLayout route={COMMENT_ROUTE} historical={false} appReady>正文</ReplayCommentsLayout></StrictMode>)
  fireEvent.click(screen.getByRole('button', { name: '展开在线评论' }))
  await waitFor(() => expect(container.querySelector('giscus-widget')?.shadowRoot?.querySelector('iframe')).toBeTruthy())
  const handlers = add.mock.calls.filter(call => call[0] === 'message').map(call => call[1])
  const iframe = container.querySelector('giscus-widget')!.shadowRoot!.querySelector('iframe')!
  rerender(<StrictMode><ReplayCommentsLayout route={COMMENT_ROUTE} historical appReady>正文</ReplayCommentsLayout></StrictMode>)
  expect(iframe.isConnected).toBe(false)
  for (const handler of handlers) expect(remove.mock.calls.some(call => call[0] === 'message' && call[1] === handler)).toBe(true)
  rerender(<ReplayCommentsLayout route="history/other" historical={false} appReady>其他篇</ReplayCommentsLayout>)
  expect(container.querySelector('giscus-widget')).toBeNull()
  expect(screen.queryByRole('complementary')).toBeNull()
})
