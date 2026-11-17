import {afterEach, expect, it, vi} from 'vitest'
import {createCommentsApi} from './customCommentsClient'
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals()})
it('popup rejects foreign origin/source; sends only opaque session bearer with cookies omitted',async()=>{
 const popup={closed:false,close:vi.fn(),location:{href:''}}
 vi.spyOn(window,'open').mockReturnValue(popup as unknown as Window)
 vi.stubGlobal('crypto',{getRandomValues:(v:Uint8Array)=>{v.fill(7);return v},subtle:{digest:async()=>new Uint8Array(32).buffer}})
 const calls:{path:string; init?:RequestInit}[]=[]
 vi.stubGlobal('fetch',vi.fn(async(path:string,init?:RequestInit)=>{calls.push({path,init});return {ok:true,json:async()=>path.endsWith('/auth/start')?{url:'https://github.com/login/oauth/authorize?state=fixture'}:path.endsWith('/auth/exchange')?{session:'s'.repeat(43),user:{id:'U',login:'fixture'},expiresAt:Date.now()+60000}:{user:{id:'U',login:'fixture'}}}}))
 const api=createCommentsApi('https://worker.example');const pending=api.login();await vi.waitFor(()=>expect(popup.location.href).toContain('github.com'))
 const data={type:'macro-comments-oauth',code:'c'.repeat(43)}
 window.dispatchEvent(new MessageEvent('message',{origin:'https://evil.example',source:popup as unknown as Window,data}))
 window.dispatchEvent(new MessageEvent('message',{origin:'https://worker.example',source:window,data}))
 expect(calls).toHaveLength(1)
 window.dispatchEvent(new MessageEvent('message',{origin:'https://worker.example',source:popup as unknown as Window,data}))
 await expect(pending).resolves.toEqual({user:{id:'U',login:'fixture'}})
 await api.request('/me');expect(calls.at(-1)?.init?.credentials).toBe('omit');expect((calls.at(-1)?.init?.headers as Record<string,string>).Authorization).toBe('Bearer '+'s'.repeat(43))
 expect(calls.every(c=>!c.path.includes('ssss'))).toBe(true);await api.logout();await api.request('/me');expect((calls.at(-1)?.init?.headers as Record<string,string>).Authorization).toBeUndefined();api.dispose?.()
})
it('network failure is explicit and never pretends a write succeeded',async()=>{vi.stubGlobal('fetch',vi.fn(async()=>{throw new TypeError('Failed to fetch')}));await expect(createCommentsApi('https://worker.example').request('/comments','POST',{body:'fixture'})).rejects.toThrow('评论服务连接失败')})
it('blocked popup is an honest error',async()=>{vi.spyOn(window,'open').mockReturnValue(null);await expect(createCommentsApi('https://worker.example').login()).rejects.toThrow('弹窗被拦截')})
