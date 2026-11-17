import {afterEach,expect,it,vi} from 'vitest'
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react'
import {CustomComments} from './customComments'
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals()})
it.each(['POST','PATCH','GET','local-expiry','reply-PATCH'])('clears UI auth on %s expiry, preserves both drafts and recovers login',async mode=>{
 const popup={closed:false,close:vi.fn(),location:{href:''}}
 vi.spyOn(window,'open').mockReturnValue(popup as unknown as Window)
 vi.stubGlobal('crypto',{getRandomValues:(v:Uint8Array)=>{v.fill(7);return v},subtle:{digest:async()=>new Uint8Array(32).buffer}})
 let rejected=false,loginCount=0,now=1000000
 vi.spyOn(Date,'now').mockImplementation(()=>now)
 const row={id:'C1',body:'original',updatedAt:'v1',author:{id:'U1',login:'fixture'},replyCount:mode==='reply-PATCH'?1:0,replyToId:null,canEdit:true,canDelete:true}
 const fetcher=vi.fn(async(path:string,init?:RequestInit)=>{
  if(path.endsWith('/auth/start'))return {ok:true,json:async()=>({url:'https://github.com/login/oauth/authorize?state=fixture'})}
  if(path.endsWith('/auth/exchange')){loginCount++;return {ok:true,json:async()=>({session:'s'.repeat(43),user:row.author,expiresAt:now+60000})}}
  if(path.endsWith('/replies')&&!rejected)return {ok:true,json:async()=>({nodes:[{...row,id:'R1',body:'reply original',replyToId:'C1',replyCount:0}],totalCount:1,pageInfo:{hasNextPage:false,endCursor:null}})}
  if(rejected)return {ok:false,status:401,json:async()=>({error:'expired fixture session'})}
  return {ok:true,json:async()=>init?.method==='PATCH'?{comment:{...row,body:'edit draft'}}:{nodes:[row],totalCount:1,pageInfo:{hasNextPage:false,endCursor:null}}}
 })
 vi.stubGlobal('fetch',fetcher)
 render(<CustomComments origin="https://worker.example"/>);await screen.findByText('original')
 async function login(){popup.location.href='';fireEvent.click(screen.getByRole('button',{name:'使用 GitHub 登录 / 注册'}));await waitFor(()=>expect(popup.location.href).toContain('github.com'));window.dispatchEvent(new MessageEvent('message',{origin:'https://worker.example',source:popup as unknown as Window,data:{type:'macro-comments-oauth',code:'c'.repeat(43)}}));await screen.findByText('已登录：fixture');await waitFor(()=>expect(screen.getByRole('button',{name:'退出登录'})).not.toBeDisabled())}
 await login()
 fireEvent.change(screen.getByRole('textbox',{name:'发表留言'}),{target:{value:'post draft'}})
 if(mode==='reply-PATCH'){fireEvent.click(screen.getByRole('button',{name:'查看回复（1）'}));await screen.findByText('reply original')}
 fireEvent.click(screen.getAllByRole('button',{name:'编辑'}).at(-1)!);fireEvent.change(screen.getByRole('textbox',{name:'编辑留言'}),{target:{value:'edit draft'}})
 if(mode==='local-expiry')now+=60001;else rejected=true
 if(mode==='GET'){vi.spyOn(window,'confirm').mockReturnValue(true);fireEvent.click(screen.getByRole('button',{name:'刷新站内评论'}))}
 else fireEvent.click(screen.getByRole('button',{name:mode.endsWith('PATCH')?'保存修改':'发表'}))
 await screen.findByRole('alert')
 expect(screen.queryByText('已登录：fixture')).toBeNull()
 expect(screen.getByRole('button',{name:'使用 GitHub 登录 / 注册'})).not.toBeDisabled()
 expect(screen.getByRole('button',{name:'发表'})).toBeDisabled();expect(screen.getByRole('button',{name:'保存修改'})).toBeDisabled()
 expect(screen.getByRole('alert')).toHaveTextContent('重新登录')
 expect(screen.getByRole('textbox',{name:'发表留言'})).toHaveValue('post draft');expect(screen.getByRole('textbox',{name:'编辑留言'})).toHaveValue('edit draft')
 rejected=false;await login();expect(loginCount).toBe(2)
 expect(screen.getByRole('textbox',{name:'发表留言'})).toHaveValue('post draft');expect(screen.getByRole('textbox',{name:'编辑留言'})).toHaveValue('edit draft')
 expect(screen.getByRole('button',{name:'发表'})).not.toBeDisabled();expect(screen.getByRole('button',{name:'保存修改'})).not.toBeDisabled()
 fireEvent.click(screen.getByRole('button',{name:'保存修改'}));await screen.findByText('修改已保存并由服务器读回确认');expect(screen.getByRole('textbox',{name:'发表留言'})).toHaveValue('post draft')
})
