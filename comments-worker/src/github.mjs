import {b64,DISCUSSION,REPOSITORY,fail} from './service.mjs';
const fields=`id body updatedAt deletedAt isMinimized author { login ... on User { id } ... on Bot { id } } discussion { id repository { id } } replyTo { id } replies(first:1) { totalCount } viewerCanUpdate viewerCanDelete`;
const connection=`totalCount pageInfo { hasNextPage endCursor } nodes { ${fields} }`;
// GitHub downloads PKCS#1 RSA keys. WebCrypto imports PKCS#8; wrap locally,
// without files, shell commands, logging, or returning any key bytes.
function privateKeyDer(pem){
 const bytes=Uint8Array.from(atob(pem.replace(/-----[^-]+-----|\s/g,'')),c=>c.charCodeAt(0));
 if(!pem.includes('BEGIN RSA PRIVATE KEY'))return bytes;
 const tlv=(tag,data)=>{let n=data.length,length=[];do{length.unshift(n&255);n>>>=8}while(n);return new Uint8Array([tag,...(data.length<128?[data.length]:[128|length.length,...length]),...data])};
 return tlv(48,new Uint8Array([2,1,0,48,13,6,9,42,134,72,134,247,13,1,1,1,5,0,...tlv(4,bytes)]));
}
export class GitHubProvider {
 constructor(env,fetcher=fetch){this.env=env;this.fetcher=(...args)=>fetcher(...args);this.installation=null}
 async request(url,token,body){const response=await this.fetcher(url,{method:'POST',redirect:'manual',headers:{Authorization:`Bearer ${token}`,Accept:'application/vnd.github+json','Content-Type':'application/json','User-Agent':'Macro-Comments','X-GitHub-Api-Version':'2022-11-28'},body:JSON.stringify(body),signal:AbortSignal.timeout(15000)});if(!response.ok)fail(response.status===401?401:502,response.status===401?'GitHub 授权已失效，请重新登录':'GitHub 请求失败');return response.json()}
 async graphql(token,query,variables,nullable=false){const payload=await this.request('https://api.github.com/graphql',token,{query,variables});if(payload.errors?.length){if(nullable&&payload.data?.node===null&&payload.errors.every(e=>e.type==='NOT_FOUND'&&e.path?.length===1&&e.path[0]==='node'))return {node:null};fail(502,'GitHub 查询失败')}if(!payload.data)fail(502,'GitHub 响应无效');return payload.data}
 async authorize(code,verifier){const r=await this.fetcher('https://github.com/login/oauth/access_token',{method:'POST',redirect:'manual',headers:{Accept:'application/json','Content-Type':'application/json'},body:JSON.stringify({client_id:this.env.CLIENT_ID,client_secret:this.env.CLIENT_SECRET,code,code_verifier:verifier,redirect_uri:this.env.WORKER_ORIGIN+'/auth/callback'}),signal:AbortSignal.timeout(15000)});const grant=await r.json();if(!r.ok||grant.error||!grant.access_token)fail(401,'GitHub 授权失败');return {access_token:grant.access_token,expires_in:grant.expires_in}}
 async viewer(token){return (await this.graphql(token,'query { viewer { id login } }',{})).viewer}
 async readToken(){
  if(this.installation?.expires>Date.now()+60000)return this.installation.token;
  const enc=new TextEncoder(),now=Math.floor(Date.now()/1000),head=b64(enc.encode(JSON.stringify({alg:'RS256',typ:'JWT'}))),body=b64(enc.encode(JSON.stringify({iat:now-60,exp:now+540,iss:this.env.APP_ID}))),content=head+'.'+body;
  let key;
  try{key=await crypto.subtle.importKey('pkcs8',privateKeyDer(this.env.APP_PRIVATE_KEY),{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['sign'])}
  catch{fail(502,'KEY_IMPORT_FAILED：GitHub App 私钥格式或密钥类型不兼容；请检查服务器配置')}
  let jwt;
  try{jwt=content+'.'+b64(await crypto.subtle.sign('RSASSA-PKCS1-v1_5',key,enc.encode(content)))}
  catch{fail(502,'KEY_SIGN_FAILED：GitHub App 签名失败')}
  let result;
  try{result=await this.request(`https://api.github.com/app/installations/${this.env.INSTALLATION_ID}/access_tokens`,jwt,{repositories:['Macro'],permissions:{discussions:'read',metadata:'read'}})}
  catch(e){if(e?.status)throw e;fail(502,typeof AbortSignal.timeout!=='function'?'TIMEOUT_API_UNAVAILABLE':e?.message?.includes('Illegal invocation')?'FETCH_RECEIVER_INVALID':e instanceof SyntaxError?'TOKEN_RESPONSE_NOT_JSON':'TOKEN_REQUEST_RUNTIME_FAILED')}
  if(!result.token)fail(502,'安装授权不可用');this.installation={token:result.token,expires:Date.parse(result.expires_at)};return result.token
 }
 async get(token,id){return (await this.graphql(token,`query($id:ID!){ node(id:$id){ ... on DiscussionComment { ${fields} } } }`,{id},true)).node}
 async list(token,after){const {node}=await this.graphql(token,`query($id:ID!,$after:String){node(id:$id){... on Discussion{id repository{id} comments(first:20,after:$after){${connection}}}}}`,{id:DISCUSSION,after});if(node?.id!==DISCUSSION||node.repository?.id!==REPOSITORY)fail(502,'讨论绑定不匹配');return node.comments}
 async replies(token,id,after){const {node}=await this.graphql(token,`query($id:ID!,$after:String){node(id:$id){... on DiscussionComment { replies(first:20,after:$after){${connection}} }}}`,{id,after});if(!node?.replies)fail(404,'评论不存在');return node.replies}
 async create(token,body,replyToId){const data=await this.graphql(token,'mutation($input:AddDiscussionCommentInput!){addDiscussionComment(input:$input){comment{id}}}',{input:{discussionId:DISCUSSION,body,...(replyToId?{replyToId}:{})}});return data.addDiscussionComment.comment.id}
 async update(token,id,body){await this.graphql(token,'mutation($input:UpdateDiscussionCommentInput!){updateDiscussionComment(input:$input){comment{id}}}',{input:{commentId:id,body}})}
 async remove(token,id){await this.graphql(token,'mutation($input:DeleteDiscussionCommentInput!){deleteDiscussionComment(input:$input){clientMutationId}}',{input:{id}})}
}
