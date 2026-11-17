import test from 'node:test';
import assert from 'node:assert/strict';
import {make,req} from './fixtures.mjs';
test('health is real but unconfigured service is not ready',async()=>{const r=await make().fetch(req('/health'));assert.equal(r.status,200);assert.equal((await r.json()).configured,false)});
