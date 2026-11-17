export class CommentsAuthError extends Error {
  constructor() {super('登录已过期，请重新登录；未提交的发表和编辑草稿已保留。'); this.name = 'CommentsAuthError'}
}
export type CommentUser = {id: string; login: string}
export type CommentRow = {id: string; body: string; updatedAt: string; author: CommentUser | null; replyCount: number; replyToId: string | null; canEdit: boolean; canDelete: boolean}
export type CommentPage = {nodes: CommentRow[]; totalCount: number; pageInfo: {hasNextPage: boolean; endCursor: string | null}}
export interface CommentsApi {request(path: string, method?: string, body?: unknown): Promise<unknown>; login(): Promise<{user: CommentUser}>; logout(): Promise<void>; dispose?(): void}
export function customCommentsOrigin(env: Record<string, string | boolean | undefined>): string | null {
  if (env.VITE_CUSTOM_COMMENTS_ENABLED !== 'true' || typeof env.VITE_COMMENTS_API !== 'string') return null
  try { const u = new URL(env.VITE_COMMENTS_API); return u.protocol === 'https:' && u.origin === env.VITE_COMMENTS_API && !u.username && !u.password ? u.origin : null } catch { return null }
}
const base64url = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '')
export function createCommentsApi(origin: string): CommentsApi {
  let session: string | null = null
  let expiresAt = 0
  let cancelLogin: (() => void) | undefined
  async function request(path: string, method = 'GET', body?: unknown): Promise<unknown> {
    if (session && Date.now() >= expiresAt) {session = null; expiresAt = 0; throw new CommentsAuthError()}
    const response = await fetch(origin + path, {method, credentials: 'omit', redirect: 'error', cache: 'no-store', headers: {'Content-Type': 'application/json', ...(session ? {Authorization: `Bearer ${session}`} : {})}, ...(body === undefined ? {} : {body: JSON.stringify(body)}), signal: AbortSignal.timeout(20000)}).catch(() => {throw new Error('评论服务连接失败；草稿保留。若刚才提交过，请先刷新核对，不要重复提交。')})
    if (response.status === 401) {session = null; expiresAt = 0; throw new CommentsAuthError()}
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '评论请求失败；请先刷新核对操作结果')
    return data
  }
  function login(): Promise<{user: CommentUser}> {
    cancelLogin?.()
    // Open synchronously in a user gesture, before awaiting PKCE or network.
    const popup = window.open('about:blank', 'macro-comments-login', 'popup,width=600,height=740')
    if (!popup) return Promise.reject(new Error('登录弹窗被拦截，请允许弹窗后重试'))
    const verifier = base64url(crypto.getRandomValues(new Uint8Array(32)))
    return new Promise((resolve, reject) => {
      let finished = false, exchanging = false
      const cleanup = () => { window.removeEventListener('message', receive); window.clearTimeout(timer); window.clearInterval(closed); cancelLogin = undefined; popup.close() }
      const fail = (message: string) => { if (!finished) { finished = true; cleanup(); reject(new Error(message)) } }
      const receive = (event: MessageEvent) => {
        if (finished || exchanging || event.origin !== origin || event.source !== popup || event.data?.type !== 'macro-comments-oauth' || !/^[A-Za-z0-9_-]{43}$/.test(event.data?.code || '')) return
        exchanging = true
        void request('/auth/exchange', 'POST', {code: event.data.code, verifier}).then(value => {
          if (finished) return
          const result = value as {session: string; user: CommentUser; expiresAt: number}
          if (!/^[A-Za-z0-9_-]{43}$/.test(result.session) || !result.user?.id || result.expiresAt <= Date.now()) throw new Error('登录响应无效')
          session = result.session; expiresAt = result.expiresAt; finished = true; cleanup(); resolve({user: result.user})
        }).catch(e => fail(e instanceof Error ? e.message : '登录失败'))
      }
      const timer = window.setTimeout(() => fail('登录超时，请重试'), 300000)
      const closed = window.setInterval(() => { if (popup.closed && !exchanging) fail('登录窗口已关闭，请重试') }, 500)
      cancelLogin = () => fail('登录已取消')
      window.addEventListener('message', receive)
      void crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)).then(digest => request('/auth/start', 'POST', {challenge: base64url(new Uint8Array(digest))})).then(value => {
        if (finished) return
        const target = new URL((value as {url: string}).url)
        if (target.origin !== 'https://github.com' || target.pathname !== '/login/oauth/authorize') throw new Error('授权地址无效')
        popup.location.href = target.href
      }).catch(e => fail(e instanceof Error ? e.message : '登录失败'))
    })
  }
  return {request, login, async logout() { try { if (session) await request('/auth/logout', 'POST', {}) } finally { session = null; expiresAt = 0 } }, dispose() {cancelLogin?.(); session = null; expiresAt = 0}}
}
