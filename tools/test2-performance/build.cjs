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
(async()=>{
 await vm.runInContext("loadExternalBundledPrecomputedData('all')",ctx);
 for(const type of ['general','recycle'])await vm.runInContext(`ensureLocalScheduleIndex('${type}')`,ctx);
 const manifest=read('cjwaste-test/data/service-zones-test-manifest.json');let total=0;
 for(const [type,entries] of Object.entries(manifest.types))for(const entry of entries){
  ctx.sourceZones=read(entry.path).zones;ctx.zoneType=type;
  const parts=vm.runInContext(`sourceZones.flatMap((original,i)=>{
   const z=normalizeMainDisplaySchedule(zoneType,original);
   return mainDisplayZoneParts(zoneType,z).map(p=>{
    const patch={};
    for(const key of ['vehicle','vehicles','provider','days','ambiguous','automatic','fromBundle','mainDisplay','estimated','rural','refinementBasis','evidenceSamples','productionOverride'])if(p[key]!==undefined)patch[key]=p[key];
    if(JSON.stringify(p.hitRings||p.rings||[p.points])!==JSON.stringify(z.hitRings||z.rings||[z.points]))patch.hitRings=p.hitRings||p.rings||[p.points];
    return [i,patch];
   });
  })`,ctx);
  const dest=entry.path.replace('cjwaste-test/data/zones/','cjwaste-test2/data/display-zones-v1/');fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,JSON.stringify({version:1,parts}));total+=parts.length;
 }
 console.log({precomputedDisplayParts:total});
})().catch(e=>{console.error(e);process.exit(1)});
