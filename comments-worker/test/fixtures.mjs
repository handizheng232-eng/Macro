import assert from 'node:assert/strict';
import {CommentsService} from '../src/service.mjs';
import {randomBytes} from 'node:crypto';
class Memory {
 data=new Map(); scheduled=null; lists=[];
 async get(k){return structuredClone(this.data.get(k))}
 async put(k,v){this.data.set(k,structuredClone(v))}
 async delete(k){return this.data.delete(k)}
 async list(options={}){this.lists.push(options);return new Map([...this.data].sort(([a],[b])=>a<b?-1:a>b?1:0).filter(([k])=>!options.startAfter||k>options.startAfter).slice(0,options.limit).map(([k,v])=>[k,structuredClone(v)]))}
 async getAlarm(){return this.scheduled}
 async setAlarm(time){this.scheduled=Number(time)}
 async fire(service){assert.notEqual(this.scheduled,null);assert.ok(this.scheduled<=Date.now());this.scheduled=null;await service.alarm()}
}
const env={SITE_ORIGIN:'https://handizheng232-eng.github.io',WORKER_ORIGIN:'https://comments.example',ENVIRONMENT:'production'};
const make=(provider={})=>new CommentsService(new Memory(),env,provider);
const req=(path,method='GET',body,token,origin=env.SITE_ORIGIN)=>new Request(env.WORKER_ORIGIN+path,{method,headers:{Origin:origin,'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},...(body?{body:JSON.stringify(body)}:{})});
const configured={...env,APP_ID:'123',CLIENT_ID:'Iv.fixture',INSTALLATION_ID:'1',CLIENT_SECRET:'TEST_ONLY',APP_PRIVATE_KEY:'TEST_ONLY',TOKEN_KEY:randomBytes(32).toString('base64')};
const verifier='a'.repeat(43);
const digest=async s=>Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s))).toString('base64url');
function fixture(){const storage=new Memory();const provider={authorize:async()=>({access_token:'github_FIXTURE_TOKEN',expires_in:28800}),viewer:async()=>({id:'U1',login:'owner'})};return {storage,provider,service:new CommentsService(storage,configured,provider)}}
async function login(f){const start=await f.service.fetch(req('/auth/start','POST',{challenge:await digest(verifier)}));assert.equal(start.status,200);const url=new URL((await start.json()).url);assert.equal(url.searchParams.has('scope'),false);assert.equal(url.searchParams.get('code_challenge_method'),'S256');const callback=await f.service.fetch(req('/auth/callback?code=fixture&state='+url.searchParams.get('state')));assert.equal(callback.status,200);const html=await callback.text();assert.ok(!html.includes('github_FIXTURE_TOKEN'));const code=JSON.parse(html.match(/const message=(.*);window.opener/)[1]).code;return {code,state:url.searchParams.get('state')}}
export {Memory,env,make,req,fixture,login,verifier};
