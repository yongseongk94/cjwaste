const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(root+'/cjwaste-test/index.html','utf8');
let js=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');
js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document:{getElementById:()=>({getAttribute:()=>'',textContent:'',classList:{contains:()=>true}})},localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{}});
vm.runInContext(js,ctx);
const check=s=>vm.runInContext(s,ctx);
const bundle=JSON.parse(fs.readFileSync(root+'/cjwaste-test/data/precomputed-village-connected-v2.json'));
ctx.inputBundle=bundle;check('villageRouteBundle=inputBundle');
assert.equal(bundle.villageVersion,'village-facility-v1');
assert.equal(bundle.travelVersion,'village-connected-v2');
assert.deepEqual(bundle.matches.filter(r=>r.status!=='matched').map(r=>r.village).sort(),['도암리','발산리','화죽리']);
assert.equal(bundle.matches.filter(r=>r.matchKind==='bus-stop').length,3,'verified bus fallbacks missing');
assert.equal(bundle.version,check('DONG_ROUTE_CACHE_VERSION'));
const previous=JSON.parse(fs.readFileSync(root+'/cjwaste-test/data/precomputed-village-facility-routes-v1.json'));
for(const r of bundle.routes){const old=previous.routes.find(x=>x.type===r.type&&x.vehicle===r.vehicle&&x.day===r.day&&x.scopeSignature===r.scopeSignature);assert.deepEqual(r.data.segments,old.data.segments,'transit geometry changed schedule evidence');}
const specs=check('allDongRouteSpecs().filter(villageSpecAffected)');
const key=s=>[s.type,s.vehicle,s.day,s.scopeSignature].join('|');
assert.equal(bundle.routes.length,specs.length,'incomplete vehicle/day build');
assert.equal(new Set(bundle.routes.map(key)).size,bundle.routes.length,'duplicate route slots');
check(`for(const spec of allDongRouteSpecs().filter(villageSpecAffected)){
 const r=villagePrecomputedRecord(spec);
 if(!r)throw Error('missing vehicle/day bundle');
 if(!routeCachePatchSuffix(spec).includes('village-connected-v2'))throw Error('stale cache key');
 if(!r.data.travelSegments?.length)throw Error('missing connected road');
 if(r.data.travelSegments.length!==1)throw Error('disconnected route '+spec.vehicle+' '+spec.day);
 for(const f of r.data.travelWaypoints)if(routeItemDistanceKm({segments:r.data.travelSegments},f.lat,f.lng)>(villageRouteTerm(f.term)?.1:.15))throw Error('waypoint too far from road');
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

// Conflicting coarse district boundaries must not drop a verified legal-village stop.
check(`{
 const p={lat:36.73228884,lng:127.5045303,term:'입동리'};
 const square={type:'Feature',geometry:{type:'Polygon',coordinates:[[[127.50,36.73],[127.51,36.73],[127.51,36.74],[127.50,36.74],[127.50,36.73]]]}};
 const spec=allDongRouteSpecs().find(s=>s.vehicle==='0264'&&s.day==='금'&&routeAllowedDistricts(s).includes('내수읍'));
 riFeatureMap.set('내수읍|입동리',square);
 if(villageEvidenceDistrict(p,spec)!=='내수읍')throw Error('legal-village evidence discarded');
 if(villageEvidenceDistrict({...p,lng:127.6},spec))throw Error('outside-village point accepted');
 riFeatureMap.delete('내수읍|입동리');
}`);
console.log('PASS exact legal-village boundary evidence and outside-point rejection');
