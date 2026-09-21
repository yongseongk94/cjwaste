const fs=require('fs'),vm=require('vm'),assert=require('assert');
const path=require('path');
const root=path.resolve(__dirname,'..');
if(!process.argv[2])throw Error('Usage: node tools/test_disjoint_display.cjs emd.json [geometry-output.json]');
const html=fs.readFileSync(root+'/cjwaste-test/index.html','utf8');
let js=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');
js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document:{getElementById:()=>({getAttribute:()=>'',textContent:'',classList:{contains:()=>true}})},localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{},polygonClipping:require(root+'/cjwaste-test/vendor/polygon-clipping-0.15.7.min.js')});
vm.runInContext(js,ctx);
const emd=JSON.parse(fs.readFileSync(process.argv[2]));
ctx.features=emd.features.filter(f=>(f.properties.sggnm||'').includes('청원구'));
ctx.manifest=JSON.parse(fs.readFileSync(root+'/cjwaste-test/data/service-zones-gapfill-v3-manifest.json'));
console.log('features',ctx.features.length,'manifest',Object.keys(ctx.manifest));
vm.runInContext(`features.forEach(f=>districtFeatureMap.set(canonicalDistrict(f.properties.dong||f.properties.emdnm),f));`,ctx);


for(const type of ['general','recycle']){
 for(const e of ctx.manifest.types[type]){
  const chunk=JSON.parse(fs.readFileSync(root+'/'+e.path));
  ctx.chunk=chunk;ctx.type=type;
  vm.runInContext('registerRawServiceZones(type,chunk.zones||[])',ctx);
 }
}
console.log(vm.runInContext("[...rawServiceZones.general].map(([d,z])=>[d,z.length])",ctx));
ctx.outputs=[];
vm.runInContext(`
const extent={minLat:36.64,maxLat:36.67,minLng:127.46,maxLng:127.50};
currentMapBoundsBox=()=>extent;
const samples=[];
for(const [district,feature] of districtFeatureMap){
 const b=featureBounds(feature);
 samples.push({district,lat:(b.minLat+b.maxLat)/2,lng:(b.minLng+b.maxLng)/2});
 const p=outerRingsOfFeature(feature)[0][0];
 samples.push({district:district+' 경계',lat:p[1],lng:p[0]});
}
for(const type of ['general','recycle']){
 for(const sample of samples){
  Object.assign(extent,{minLat:sample.lat-.009,maxLat:sample.lat+.009,minLng:sample.lng-.012,maxLng:sample.lng+.012});
  const start=Date.now();
  const zones=coarseDisplayZones(type);
  outputs.push({type,sample,extent:{...extent},zones});
  console.log(type,sample.district,zones.length,Date.now()-start+'ms');
 }
}
`,ctx,{timeout:240000});
ctx.scenarios=[];
vm.runInContext(`
Object.assign(extent,{minLat:36.646,maxLat:36.674,minLng:127.464,maxLng:127.501});
const all=coarseDisplayZones('general');
for(const day of DAYS){
 activeDay=day;
 scenarios.push({label:'day '+day,expected:all.filter(z=>z.days.includes(day)),actual:coarseDisplayZones('general')});
}
activeDay='전체';
for(const vehicle of [...new Set(all.map(z=>z.vehicle))]){
 selectedVehicle.general=vehicle;
 scenarios.push({label:'vehicle '+vehicle,expected:all.filter(z=>rawZoneMatchesCurrentFilter('general',z)),actual:coarseDisplayZones('general')});
}
selectedVehicle.general='전체';
manualServiceZones=[
 {type:'general',vehicle:'3346',days:['월'],points:[{lat:36.65,lng:127.479},{lat:36.655,lng:127.479},{lat:36.655,lng:127.487},{lat:36.65,lng:127.487}]},
 {type:'general',vehicle:'6224',days:['화'],points:[{lat:36.652,lng:127.482},{lat:36.657,lng:127.482},{lat:36.657,lng:127.490},{lat:36.652,lng:127.490}]}
];
const parts=displayPartitionMasks('general').manualParts.flatMap(({zone,geometry})=>displayGeometryZones(zone,geometry));
scenarios.push({label:'manual subtraction',expected:all,actual:[...coarseDisplayZones('general'),...parts]});
if(parts.some(z=>z.vehicle==='3346'&&pointInZonePolygon(36.653,127.483,z)))throw Error('manual priority mismatch');
if(!parts.some(z=>z.vehicle==='6224'&&pointInZonePolygon(36.653,127.483,z)))throw Error('manual priority missing');
console.log('PASS manual priority');
`,ctx);
if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify({viewports:ctx.outputs,scenarios:ctx.scenarios}));
const rendered=[];
ctx.kakao={maps:{LatLng:class {constructor(lat,lng){this.lat=lat;this.lng=lng;}},Polygon:class {
 constructor(options){this.options=options;this.map=null;rendered.push(this);}
 setMap(map){this.map=map;} getMap(){return this.map;}
 setOptions(options){Object.assign(this.options,options);}
},event:{addListener(){}}}};
vm.runInContext(`
map={};activeLayer='general';testAdminBoundaryLoadStarted=true;updateMapBadge=()=>{};
materializeVisibleRawServiceZones('general');
materializeVisibleRawServiceZones('general');
if(serviceZoneOverlays.general.some(z=>z.displayBase))throw Error('duplicate base layer');
`,ctx);
assert.equal(rendered.filter(p=>p.map).length,vm.runInContext('serviceZoneOverlays.general.length',ctx));
console.log('PASS repeated render replaces previous polygons');
