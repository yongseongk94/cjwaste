const fs=require('fs'),vm=require('vm'),path=require('path'),crypto=require('crypto');
const root=path.resolve(__dirname,'../..');process.chdir(root);
const read=p=>JSON.parse(fs.readFileSync(p));
let js=[...fs.readFileSync('cjwaste-test2/index.html','utf8').matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document:{getElementById:()=>({getAttribute:()=>'',textContent:'',classList:{contains:()=>true}})},localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{}});vm.runInContext(js,ctx);
const packed=read('cjwaste-test2/data/precomputed-routes-contractor-groups-v1.json');
const baseline=packed.routes.map(r=>r.dataRef?{...r,data:packed.geometryPool[r.dataRef]}:r);
const latest=read('cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json').routes;
const uam=read('data/precomputed-uam-contractor-routes-v1.json').routes;
ctx.input=[...latest,...uam,...baseline];
const records=vm.runInContext(`(()=>{const specs=allDongRouteSpecs(),out=[],seen=new Set();for(const r of input){const s=bundleRouteRecordSpec(r,specs);if(!s)continue;const scope=routeScopeSignature(s),key=[r.type,r.vehicle,r.day,scope].join('|');if(seen.has(key))continue;seen.add(key);out.push({type:r.type,vehicle:r.vehicle,day:r.day,districts:routeAllowedDistricts(s),scopeSignature:scope,data:r.data,group:contractorRouteGeometryKey(s)});}return out})()`,ctx);
// Within a confirmed common weekday route preserve every newly corrected source segment.
const grouped=new Map();for(const r of records)if(r.group){if(!grouped.has(r.group))grouped.set(r.group,[]);grouped.get(r.group).push(r)}
for(const rs of grouped.values()){
 const d=JSON.parse(JSON.stringify(rs[0].data));
 for(const k of ['segments','zoneEvidencePoints','estimatedServiceSegments','connectionSegments','estimatedTerms']){
  if(!rs.some(r=>r.data[k]))continue;const seen=new Set();d[k]=[];for(const r of rs)for(const v of r.data[k]||[]){const sig=JSON.stringify(v);if(!seen.has(sig)){seen.add(sig);d[k].push(v)}}
 }
 d.contractorGroupVersion='weekday-groups-v2';for(const r of rs)r.data=d;
}
const groups=new Map();for(const r of records){const key=r.type+'|'+r.scopeSignature;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(r)}
const folder='cjwaste-test2/data/routes-integrated-v1';fs.mkdirSync(folder,{recursive:true});let chunks=[],total=0;
for(const [key,rs] of groups){const id=crypto.createHash('sha256').update(key).digest('hex').slice(0,12);const pool={},refs=[],memo=new Map();for(const r of rs){const sig=JSON.stringify(r.data);let ref=memo.get(sig);if(!ref){ref='g'+memo.size;memo.set(sig,ref);pool[ref]=r.data}const {data,group,...meta}=r;refs.push({...meta,dataRef:ref})}const out={version:'v76-test2-connected-v12',revision:'integrated-v1',geometryPool:pool,routes:refs};const filename=folder+'/'+id+'.json';fs.writeFileSync(filename,JSON.stringify(out));const size=fs.statSync(filename).size;total+=size;chunks.push({type:rs[0].type,districts:rs[0].districts,vehicles:[...new Set(rs.map(r=>r.vehicle))],path:filename,bytes:size,routes:rs.length});}
const manifest={version:'v76-test2-connected-v12',revision:'integrated-v1',chunks};fs.writeFileSync('cjwaste-test2/data/routes-integrated-manifest-v1.json',JSON.stringify(manifest));
const report={records:records.length,chunks:chunks.length,totalBytes:total,byType:Object.fromEntries(['general','recycle'].map(t=>[t,chunks.filter(x=>x.type===t).reduce((n,x)=>n+x.bytes,0)])),ruralLatest:latest.length,uamLatest:uam.length};fs.writeFileSync('tools/test2-integration/build-report.json',JSON.stringify(report,null,2));console.log(report);
