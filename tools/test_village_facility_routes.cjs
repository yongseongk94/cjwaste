const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(root+'/cjwaste-test/index.html','utf8');
let js=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');
js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document:{getElementById:()=>({getAttribute:()=>'',textContent:'',classList:{contains:()=>true}})},localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{}});
vm.runInContext(js,ctx);
const check=s=>vm.runInContext(s,ctx);
const bundle=JSON.parse(fs.readFileSync(root+'/cjwaste-test/data/precomputed-village-facility-routes-v1.json'));
ctx.inputBundle=bundle;check('villageRouteBundle=inputBundle');
assert.equal(bundle.villageVersion,'village-facility-v1');
assert.equal(bundle.version,check('DONG_ROUTE_CACHE_VERSION'));
const specs=check('allDongRouteSpecs().filter(villageSpecAffected)');
const key=s=>[s.type,s.vehicle,s.day,s.scopeSignature].join('|');
assert.equal(bundle.routes.length,specs.length,'incomplete vehicle/day build');
assert.equal(new Set(bundle.routes.map(key)).size,bundle.routes.length,'duplicate route slots');
check(`for(const spec of allDongRouteSpecs().filter(villageSpecAffected)){
 const r=villagePrecomputedRecord(spec);
 if(!r)throw Error('missing vehicle/day bundle');
 if(!routeCachePatchSuffix(spec).includes('village-facility-v1'))throw Error('stale cache key');
 if(!r.data.segments.length&&routeDescriptorsForMap(spec.raw).some(d=>villageFacilityCandidates(d.term,spec).length))throw Error('empty road geometry for matched village');
 const current=buildLocalScheduleIndex(spec.type,{routes:[r]});
 if(!current.records.length)throw Error('new route absent from schedule index');
 const old={...r};delete old.villageVersion;
 if(buildLocalScheduleIndex(spec.type,{routes:[old]}).records.length)throw Error('old village geometry reintroduced');
 for(const d of routeDescriptorsForMap(spec.raw)){
  if(!villageRouteTerm(d.term))continue;
  const fs=villageFacilityCandidates(d.term,spec);
  if(!fs.length&&!r.data.missingTerms.includes(d.term))throw Error('unresolved village not disclosed: '+d.term);
  for(const f of fs){
   if(!f.name||!f.address||!f.sourceUrl)throw Error('missing facility provenance');
   if(!r.data.zoneEvidencePoints.some(p=>routePointDistance(p,f)<.001))throw Error('facility coordinate missing');
  }
 }
}`);
assert.equal(check("villageRouteTerm('장양2리')"),'장양2리');
assert.equal(check("villageRouteTerm('은곡3구')"),'은곡3리');
assert.equal(check("villageRouteTerm('장양2길 81-1')"),'');
assert.equal(check("villageRouteTerm('오창사거리')"),'');
console.log('PASS facility routes: complete slots, coordinate provenance, missing village disclosure, cache invalidation, schedule replacement');

check(`
const center={lat:36.7,lng:127.5};
const crossing=clipVillageFacilitySegments([[{lat:36.7,lng:127.49},{lat:36.7,lng:127.51}]],center);
if(crossing.length!==1||crossing[0].length!==2)throw Error('crossing road lost');
for(const point of crossing[0])if(routePointDistance(point,center)>.181)throw Error('facility radius exceeded');
if(clipVillageFacilitySegments([[{lat:36.8,lng:127.49},{lat:36.8,lng:127.51}]],center).length)throw Error('distant road retained');
`);
console.log('PASS facility neighborhood clipping: crossing retained, distant road excluded');
