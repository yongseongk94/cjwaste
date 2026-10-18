const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..');process.chdir(root);
const html=fs.readFileSync('cjwaste-test2/index.html','utf8');let js=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const read=p=>JSON.parse(fs.readFileSync(p));const nodes={},requests=[];
const document={createElement:()=>({}),getElementById:id=>nodes[id]||(nodes[id]={dataset:{src:'cjwaste-test2/data/routes-integrated-manifest-v1.json'},getAttribute:()=>'',textContent:'',innerHTML:'',appendChild:()=>{},classList:{contains:()=>true}})};
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document,localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{},fetch:async p=>{requests.push(p);return {ok:true,json:async()=>read(p.split('?')[0])}}});
for(const f of ['ochang-boundary-2023.js','ochang2-boundary-2023.js'])vm.runInContext(fs.readFileSync('cjwaste-test2/data/'+f,'utf8'),ctx);
vm.runInContext(js,ctx);ctx.districts=read('tools/test2-connected/context.json').districts;
vm.runInContext('for(const [d,f] of Object.entries(districts))districtFeatureMap.set(d,f)',ctx);
ctx.polygonClipping=require('../../vendor/polygon-clipping-0.15.7.min.js');
ctx.performance=require('perf_hooks').performance;
const counts={created:0,attached:0,detached:0,styles:0};
ctx.kakao={maps:{LatLng:class {constructor(lat,lng){this.lat=lat;this.lng=lng}getLat(){return this.lat}getLng(){return this.lng}},Polygon:class {constructor(){counts.created++;this.map=null}getMap(){return this.map}setMap(m){if(m!==this.map){if(m)counts.attached++;else counts.detached++;this.map=m}}setOptions(){counts.styles++}},event:{addListener:()=>{}}}};
ctx.document.querySelectorAll=()=>[];
(async()=>{
 await vm.runInContext("Promise.all(['general','recycle'].map(t=>ensureLegacyDisplayZoneDistricts(t,['오창읍'])))",ctx);
 const manifestForRaw=read('data/service-zones-production-gapfill-v3-manifest.json');
 let rawCount=0;
 for(const type of ['general','recycle']){const r=await vm.runInContext(`loadExternalBundledServiceZones('${type}',Object.keys(districts))`,ctx);rawCount+=r.zones[type].length;}
 assert.equal(rawCount,6482,'main raw zone paths failed');
 const fetched=requests.length;
 vm.runInContext(`map={};resultMapVisible=()=>true;currentMapBoundsBox=()=>null;updateMapBadge=()=>{};syncDongRouteVisibility=()=>{};rebuildManualZoneOverlays=()=>{};activeLayer='general';`,ctx);
 let frames=0;const started=performance.now();
 while(vm.runInContext("materializeVisibleRawServiceZones('general')",ctx)){if(++frames>1000)throw Error('frame loop')}
 const initial={...counts,frames:frames+1,ms:Math.round(performance.now()-started)};
 const before={...counts};
 for(let i=0;i<5;i++)vm.runInContext("materializeVisibleRawServiceZones('general')",ctx);
 assert.equal(counts.created,before.created);assert.equal(counts.detached,before.detached);assert.equal(counts.styles,before.styles);
 vm.runInContext("activeDay='월';syncServiceZoneVisibility('general')",ctx);
 const onMonday={...counts};vm.runInContext("syncServiceZoneVisibility('general',true)",ctx);
 assert.deepEqual(counts,onMonday,'same day must not detach/reattach/restyle');
 vm.runInContext("serviceLayerState.zone=false;syncServiceZoneVisibility('general')",ctx);
 assert(vm.runInContext("serviceZoneOverlays.general.every(z=>!z.polygon.getMap())",ctx));
 vm.runInContext("serviceLayerState.zone=true;activeDay='전체';activeLayer='recycle'",ctx);
 while(vm.runInContext("materializeVisibleRawServiceZones('recycle')",ctx)){}
 assert(vm.runInContext("serviceZoneOverlays.general.every(z=>!z.polygon.getMap())",ctx));
 const switchBefore=counts.created;vm.runInContext("activeLayer='general';materializeVisibleRawServiceZones('general')",ctx);
 assert.equal(counts.created,switchBefore,'returning layer recreates polygons');
 assert.equal(requests.length,fetched,'rendering fetched routes');
 assert(vm.runInContext("localScheduleIndexes.general===null&&localScheduleIndexes.recycle===null",ctx),'rendering built route index');
 assert(!html.includes('setTimeout(()=>{if(isCurrent())forceActiveServiceLayerVisibility(layer)}'));
 // Verify precomputed metadata and split geometry against the original refinement algorithm.
 await vm.runInContext("loadExternalBundledPrecomputedData('all')",ctx);
 for(const type of ['general','recycle'])await vm.runInContext(`ensureLocalScheduleIndex('${type}')`,ctx);
 let preserved=0;
 const manifest=read('cjwaste-test/data/service-zones-test-manifest.json');
 for(const [type,entries] of Object.entries(manifest.types))for(const entry of entries){
  ctx.sourceZones=read(entry.path).zones;ctx.zoneType=type;
  const expected=vm.runInContext(`sourceZones.flatMap((z,i)=>mainDisplayZoneParts(zoneType,normalizeMainDisplaySchedule(zoneType,z)).map(p=>({i,vehicle:p.vehicle,days:p.days,ambiguous:p.ambiguous,rings:p.hitRings||p.rings||[p.points]})))`,ctx);
  const saved=read(entry.path.replace('cjwaste-test/data/zones/','cjwaste-test2/data/display-zones-v1/')).parts;
  assert.equal(saved.length,expected.length);
  saved.forEach(([i,p],n)=>{const z=ctx.sourceZones[i];assert.equal(JSON.stringify({i,vehicle:p.vehicle,days:p.days,ambiguous:p.ambiguous,rings:p.hitRings||z.hitRings||z.rings||[z.points]}),JSON.stringify(expected[n]));preserved++;});
 }
 const report={ok:true,initialOchang:initial,repeatedViewport:{created:0,detached:0,styleUpdates:0},sameDayRedraw:0,layerSwitchRecreation:0,renderRouteFetches:0,renderIndexBuilds:0,precomputedPartsVerified:preserved,mainRawZonesLoaded:rawCount};
 fs.writeFileSync('tools/test2-performance/test-report.json',JSON.stringify(report,null,2));console.log(report);
})().catch(e=>{console.error(e);process.exit(1)});
