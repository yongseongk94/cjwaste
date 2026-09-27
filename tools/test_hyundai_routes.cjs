const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(root+'/cjwaste-test/index.html','utf8');
let js=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');
js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document:{getElementById:()=>({getAttribute:()=>'',textContent:'',classList:{contains:()=>true}})},localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{}});
vm.runInContext(js,ctx);
const check=s=>vm.runInContext(s,ctx);
const bundle=JSON.parse(fs.readFileSync(root+'/cjwaste-test/data/precomputed-hyundai-v1.json'));
assert.equal(bundle.routes.length,4);
for(const r of bundle.routes){
 ctx.record=r;
 check(`{
  const spec=bundleRouteRecordSpec(record,allDongRouteSpecs());
  if(!hyundaiRouteAffected(spec))throw Error('wrong route replaced');
  if(!routeCacheKey(spec).endsWith('|hyundai-landmarks-v1'))throw Error('stale cache');
  if(!buildLocalScheduleIndex(spec.type,{routes:[record]}).records.length)throw Error('missing corrected schedule');
  const old={...record};delete old.hyundaiVersion;
  if(buildLocalScheduleIndex(spec.type,{routes:[old]}).records.length)throw Error('old schedule geometry accepted');
 }`);
 assert.equal(r.data.zoneEvidencePoints.length,r.day==='화'?4:6);
 assert.equal(r.data.travelSegments.length,1);
 assert.deepEqual(r.data.missingTerms,[]);
 assert(r.data.zoneEvidencePoints.every(p=>p.url&&p.district==='내덕1동'));
 assert(!r.data.zoneEvidencePoints.some(p=>['형제빌라','풀하우스','오성빌리지','위너스빌'].includes(p.name)));
}
console.log('PASS Hyundai: four weekday/type slots, exact landmarks, stale cache and schedule geometry rejected');
