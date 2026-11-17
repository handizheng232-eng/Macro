import test from 'node:test';
import assert from 'node:assert/strict';
import {CommentsService} from '../src/service.mjs';
import {Memory,env} from './fixtures.mjs';
test('continuous save and rate traffic cannot defer encrypted session cleanup',async t=>{
 let now=1000000;t.mock.method(Date,'now',()=>now);
 const storage=new Memory(),service=new CommentsService(storage,env,{});
 await service.save('session:expired',{token:'encrypted-fixture'},60000);
 const deadline=await storage.getAlarm();
 for(let i=1;i<=20;i++){now=1000000+i*1000;await service.save('state:'+i,{},300000);await service.limit('ip:'+i);assert.ok(await storage.getAlarm()<=deadline)}
 now=deadline;await storage.fire(service);assert.equal(await storage.get('session:expired'),undefined);
 await storage.setAlarm(now+900000);await service.save('exchange:soon',{},1000);assert.ok(await storage.getAlarm()<=now+300000);
});
test('cleanup is bounded and resumes across alarm invocations and service recreation',async t=>{
 let now=1000000;t.mock.method(Date,'now',()=>now);
 const storage=new Memory();let service=new CommentsService(storage,env,{});
 for(let i=0;i<250;i++)await storage.put('session:'+String(i).padStart(4,'0'),{token:'encrypted-fixture',expires:now-1});
 await storage.put('state:live',{expires:now+900000});await storage.setAlarm(now);
 await storage.fire(service);
 assert.ok([...storage.data.keys()].filter(k=>k.startsWith('session:')).length>0,'one invocation must not scan all records');
 assert.ok(storage.lists.every(o=>o.limit>0&&o.limit<=100),'all scans are bounded');
 let batches=1;
 while([...storage.data.keys()].some(k=>k.startsWith('session:'))&&batches<10){const next=await storage.getAlarm();assert.notEqual(next,null);assert.ok(next<=now+1000);now=next;service=new CommentsService(storage,env,{});await storage.fire(service);batches++}
 assert.equal([...storage.data.keys()].filter(k=>k.startsWith('session:')).length,0);assert.ok(batches>=3);assert.ok(await storage.get('state:live'));
 now=2000000;await storage.fire(service);assert.equal(storage.data.size,0);assert.equal(await storage.getAlarm(),null);
});
