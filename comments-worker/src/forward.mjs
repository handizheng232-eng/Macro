import {HttpError} from './service.mjs';
// Materialize before forwarding: an early DO rejection must not outlive the
// originating request's body stream. Bound reads, including chunked requests.
export async function bufferRequest(request){
 if(!request.body)return request;
 const reader=request.body.getReader();let size=0;const chunks=[];
 while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>40000){await reader.cancel();throw new HttpError(413,'请求过大')}chunks.push(value)}
 const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength}
 return new Request(request,{body:bytes});
}
