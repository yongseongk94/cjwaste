const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..');process.chdir(root);
const html=fs.readFileSync('cjwaste-test2/index.html','utf8');let js=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const read=p=>JSON.parse(fs.readFileSync(p));const nodes={},requests=[];
const document={createElement:()=>({}),getElementById:id=>nodes[id]||(nodes[id]={dataset:{src:'cjwaste-test2/data/routes-integrated-manifest-v1.json'},getAttribute:()=>'',textContent:'',innerHTML:'',appendChild:()=>{},classList:{contains:()=>true}})};
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document,localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{},fetch:async p=>{requests.push(p);return {ok:true,json:async()=>read(p.split('?')[0])}}});
vm.runInContext(js,ctx);ctx.districts=read('tools/test2-connected/context.json').districts;
vm.runInContext('for(const [d,f] of Object.entries(districts))districtFeatureMap.set(d,f)',ctx);
ctx.polygonClipping=require('../../vendor/polygon-clipping-0.15.7.min.js');
(async()=>{
 await vm.runInContext("loadExternalBundledPrecomputedData('all')",ctx);
 await vm.runInContext("Promise.all([ensureLegacyDisplayZoneDistricts('general',Object.keys(districts)),ensureLegacyDisplayZoneDistricts('recycle',Object.keys(districts))])",ctx);
 for(const type of ['general','recycle'])await vm.runInContext(`ensureLocalScheduleIndex('${type}')`,ctx);
 const report=vm.runInContext(`(()=>{
 const report={};
 for(const type of ['general','recycle']){
  let total=0,parts=0,consensus=0,mixed=0,weekdayCorrected=0;
  for(const zones of legacyDisplayZones[type].values())for(const z of zones){
   total++;const out=mainDisplayZoneParts(type,z);parts+=out.length;
   if(contractRouteMeta(z.vehicle)&&z.days.includes('월')){
    if(!z.days.includes('수')||!z.days.includes('금'))throw Error('weekday not expanded');weekdayCorrected++;
   }
   const original=zoneMultiPolygon(z),merged=polygonClipping.union(...out.map(zoneMultiPolygon));
   if(polygonClipping.xor(original,merged).length)throw Error('main boundary changed');
   for(const p of out){if(p.refinementBasis==='route-consensus')consensus++;if(p.ambiguous)mixed++;if(!p.estimated)throw Error('estimate labelled confirmed');}
  }
  report[type]={total,parts,consensus,mixed,weekdayCorrected};
 }
 const fixed=normalizeMainDisplaySchedule('general',{district:'내수읍',riName:'도원리',days:['화']});
 if(fixed.days.join()!=='월'||fixed.vehicle!=='6138')throw Error('Dowon');
 return report;
 })()`,ctx);
 assert(report.general.total>2700);assert(report.recycle.total>2600);
 assert(report.general.consensus>0);assert(report.general.weekdayCorrected>0);
 // Transit geometry must not enter the schedule evidence index.
 const test=vm.runInContext(`(()=>{const r=bundledPrecomputedExternal.routes.find(r=>r.data.connectionSegments?.length);const spec=bundleRouteRecordSpec(r,allDongRouteSpecs());return buildLocalScheduleIndex(r.type,{routes:[{...r,liveSpec:spec,data:{segments:[],connectionSegments:r.data.connectionSegments,estimatedServiceSegments:r.data.estimatedServiceSegments}}]}).records.length})()`,ctx);
 assert.equal(test,0);
 assert(!html.includes('const zones=coarseDisplayZones(type);'));
 fs.writeFileSync('tools/test2-zones/test-report.json',JSON.stringify({ok:true,mainGeometryPreserved:true,transitExcluded:true,...report},null,2));console.log(report);
})().catch(e=>{console.error(e);process.exit(1)});
