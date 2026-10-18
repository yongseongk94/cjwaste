const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..');process.chdir(root);
const html=fs.readFileSync('cjwaste-test2/index.html','utf8');let js=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const read=p=>JSON.parse(fs.readFileSync(p));const nodes={},requests=[];
const document={createElement:()=>({}),getElementById:id=>nodes[id]||(nodes[id]={dataset:{src:'cjwaste-test2/data/routes-integrated-manifest-v1.json'},getAttribute:()=>'',textContent:'',innerHTML:'',appendChild:()=>{},classList:{contains:()=>true}})};
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document,localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{},fetch:async p=>{requests.push(p);return {ok:true,json:async()=>read(p.split('?')[0])}}});
vm.runInContext(js,ctx);ctx.districts=read('tools/test2-connected/context.json').districts;
vm.runInContext('for(const [d,f] of Object.entries(districts))districtFeatureMap.set(d,f)',ctx);
const main=fs.readFileSync('index.html','utf8');
const section=(s,a,b)=>s.slice(s.indexOf(a),s.indexOf(b,s.indexOf(a)));
for(const [a,b] of [
 ['function serviceZoneOverlayMatch(type,ctx){','async function ensureServiceZoneMatch'],
 ['async function ensureServiceZoneMatch(type,ctx){','function geoPointKm'],
 ['async function refreshNearbyRouteSchedules(ctx){','function renderVehicleFilter'],
 ['async function nearestRouteMatchesForAddress(type,ctx){','const ruralSubzoneProfileCache'],
 ['function renderServiceZoneSchedule(type,match,ctx,options={})','function loadManualZones'],
 ['const FORCED_RI_SCHEDULE_OVERRIDES=','const CONFIRMED_ADDRESS_SCHEDULE_OVERRIDES=']
])assert.equal(section(html,a,b).trim(),section(main,a,b).trim(),a+' differs from main');
assert(html.includes("const TEST_SERVICE_ZONE_MANIFEST='data/service-zones-production-gapfill-v3-manifest.json'"));
(async()=>{
 const report={mainDecisionPipelineIdentical:true,mainZoneSourceIdentical:true};
 vm.runInContext(`
 routeSpecsForDistrict=()=>testRows.map(r=>({vehicle:r.vehicle,day:r.day,raw:r.raw||''}));
 ensureDistrictRouteItems=async()=>testRows;
 routeItemDistanceKm=item=>item.distance;
 `,ctx);
 ctx.testRows=[{vehicle:'6138',day:'월',distance:.019},{vehicle:'6138',day:'화',distance:.020},{vehicle:'6138',day:'목',distance:.020001},{vehicle:'3344',day:'수',distance:.0195}];
 let hit=await vm.runInContext("nearestRouteMatchesForAddress('general',{district:'내수읍',lat:36.7,lng:127.5})",ctx);
 assert.equal(hit[0].vehicle,'6138');assert.equal(hit[0].days.join(','),'월,화');
 ctx.testRows=[{vehicle:'6138',day:'월',distance:.020001}];
 hit=await vm.runInContext("nearestRouteMatchesForAddress('general',{district:'내수읍',lat:36.7,lng:127.5})",ctx);assert.equal(hit.length,0);
 ctx.testRows=[{vehicle:'6138',day:'월',distance:.005},{vehicle:'3344',day:'수',distance:.019,raw:'공항로'}];
 hit=await vm.runInContext("nearestRouteMatchesForAddress('general',{district:'내수읍',lat:36.7,lng:127.5,address:'청주시 청원구 공항로 1'})",ctx);assert.equal(hit[0].vehicle,'3344');
 report.distanceThresholdAndVehicleIsolation=true;report.roadNamePriority=true;
 const result=vm.runInContext(`(()=>{
 manualZoneMatch=()=>null;ochangContractZoneAllowedAtPoint=()=>true;
 const points=[{lat:36.65,lng:127.48},{lat:36.65,lng:127.49},{lat:36.66,lng:127.49},{lat:36.66,lng:127.48}];
 rawServiceZonesForDistrict=()=>[{district:'내덕1동',vehicle:'A',days:['목'],points,estimated:true}];
 const h=serviceZoneOverlayMatch('general',{district:'내덕1동',lat:36.655,lng:127.485});
 if(h?.days.join()!=='목'||h.matchBasis!=='displayed-zone')throw Error('polygon fallback');
 if(serviceZoneOverlayMatch('general',{district:'내덕1동',lat:36.67,lng:127.485}))throw Error('outside polygon');
 rawServiceZonesForDistrict=()=>[{district:'오창읍',riName:'각리',vehicle:'3344',days:['금'],points,estimated:true}];
 const o=serviceZoneOverlayMatch('general',{district:'오창읍',legalRi:'각리',lat:36.67,lng:127.485});
 if(o?.days.join()!=='금')throw Error('main Ochang fallback');
 const f=forcedRiScheduleOverride('general',{district:'내수읍',legalRi:'도원리'});
 if(f?.days.join()!=='월'||f.vehicle!=='6138')throw Error('Dowon override');
 return true;
 })()`,ctx);
 report.polygonFallbackAndDowon=result;
 fs.writeFileSync('tools/test2-criteria/test-report.json',JSON.stringify(report,null,2));console.log(report);
})().catch(e=>{console.error(e);process.exit(1)});
