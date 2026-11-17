import {DurableObject} from 'cloudflare:workers';
import {CommentsService} from './service.mjs';
import {GitHubProvider} from './github.mjs';
import {bufferRequest} from './forward.mjs';
export class CommentsObject extends DurableObject {
 constructor(ctx,env){super(ctx,env);this.service=new CommentsService(ctx.storage,env,new GitHubProvider(env))}
 fetch(request){return this.service.fetch(request)}
 alarm(){const job=this.service.queue.then(()=>this.service.alarm());this.service.queue=job.catch(()=>{});return job}
}
export default {async fetch(request,env){
 try {return await env.COMMENTS.get(env.COMMENTS.idFromName('macro-discussion-1')).fetch(await bufferRequest(request))}
 catch(error){const headers={'Cache-Control':'no-store','Vary':'Origin'};const origin=request.headers.get('Origin');if(origin==='https://handizheng232-eng.github.io')headers['Access-Control-Allow-Origin']=origin;return Response.json({error:error.status===413?'请求过大':'评论服务不可用'},{status:error.status===413?413:502,headers})}
}};
