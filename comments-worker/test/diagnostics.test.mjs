import test from 'node:test';
import assert from 'node:assert/strict';
import {GitHubProvider} from '../src/github.mjs';

test('key import failure exposes only a fixed diagnostic, never key contents',async()=>{
 const marker='fixture-private-material-not-a-real-key';
 const provider=new GitHubProvider({APP_PRIVATE_KEY:marker,APP_ID:'1'},()=>{throw new Error('network must not run')});
 await assert.rejects(()=>provider.readToken(),e=>e.status===502&&e.message.startsWith('KEY_IMPORT_FAILED')&&!e.message.includes(marker));
});

test('provider must not bind the runtime fetch function to a provider instance',async()=>{
 let receiver;
 const provider=new GitHubProvider({},function(){receiver=this;return Promise.resolve(Response.json({ok:true}))});
 await provider.request('https://api.github.com/graphql','fixture-only',{query:'query { viewer { id } }'});
 assert.equal(receiver,undefined);
});

test('Workers-compatible manual redirects fail closed for API and OAuth calls',async()=>{
 const seen=[];
 const provider=new GitHubProvider({CLIENT_ID:'fixture',CLIENT_SECRET:'fixture',WORKER_ORIGIN:'https://fixture.invalid'},async(url,init)=>{seen.push(init.redirect);return new Response('{}',{status:302,headers:{Location:'https://untrusted.invalid'}})});
 await assert.rejects(()=>provider.request('https://api.github.com/graphql','fixture',{}));
 await assert.rejects(()=>provider.authorize('fixture-code','fixture-verifier'));
 assert.deepEqual(seen,['manual','manual']);
});
