import test from 'node:test';
import assert from 'node:assert/strict';
import {bufferRequest} from '../src/forward.mjs';
test('DO forwarding materializes bounded body before early response',async()=>{const request=new Request('https://example.test/auth/start',{method:'POST',body:'{}'});const forwarded=await bufferRequest(request);assert.equal(request.bodyUsed,true);assert.equal(await forwarded.text(),'{}');await assert.rejects(()=>bufferRequest(new Request('https://example.test',{method:'POST',body:'x'.repeat(40001)})),e=>e.status===413)});
