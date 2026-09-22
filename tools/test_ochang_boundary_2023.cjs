const fs=require('fs'),vm=require('vm'),assert=require('assert');
const path=require('path');
const root=path.resolve(__dirname,'..');

const html=fs.readFileSync(root+'/cjwaste-test/index.html','utf8');
let js=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');
js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document:{getElementById:()=>({getAttribute:()=>'',textContent:'',classList:{contains:()=>true}})},localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{},polygonClipping:require(root+'/cjwaste-test/vendor/polygon-clipping-0.15.7.min.js')});
vm.runInContext(fs.readFileSync(root+'/cjwaste-test/data/ochang-boundary-2023.js','utf8'),ctx);
vm.runInContext(js,ctx);

const check=code=>vm.runInContext(code,ctx);

assert(check("insideOchang2023(36.7174626,127.4291884)"));
assert(!check("insideOchang2023(36.7277,127.4454)"));
assert(!check("insideOchang2023(36.74,127.455)"));
check("ochangContractRouteDistanceKm=()=>0");
for(const type of ['general','recycle']){
 assert(!check(`ochangContractZoneAllowedAtPoint('${type}',{district:'오창읍',provider:'제일환경'},36.74,127.455)`));
 assert(check(`ochangContractZoneAllowedAtPoint('${type}',{district:'오창읍',provider:'제일환경'},36.7174626,127.4291884)`));
}
check(`
const input=[[{lat:36.70,lng:127.38},{lat:36.72,lng:127.46}]];
const clipped=clipOchang2023Segments(input);
if(!clipped.length)throw Error('no clipped line');
for(const seg of clipped)for(let i=1;i<seg.length;i++){
 const a=seg[i-1],b=seg[i];
 if(!insideOchang2023((a.lat+b.lat)/2,(a.lng+b.lng)/2))throw Error('line escaped boundary');
}
if(input[0][0].lng!==127.38)throw Error('changed raw cache geometry');
const points=[{lat:36.70,lng:127.41},{lat:36.70,lng:127.46},{lat:36.74,lng:127.46},{lat:36.74,lng:127.41}];
const z={district:'오창읍',vehicle:'test',provider:'제일환경',contractLayer:true,days:['월'],points,rings:[points]};
const divided=partitionOchang2023Display('general',[z]);
const assigned=divided.filter(x=>!x.noSchedule).flatMap(zoneMultiPolygon);
if(polygonClipping.difference(assigned,ochang2023Geometry()).length)throw Error('assigned outside industrial park');
const total=polygonClipping.union(...divided.map(zoneMultiPolygon));
if(polygonClipping.difference(zoneMultiPolygon(z),total).length)throw Error('boundary clipping introduced a gap');
const contractArea=polygonClipping.union(...divided.filter(x=>!x.noSchedule).map(zoneMultiPolygon));
const unknownArea=polygonClipping.union(...divided.filter(x=>x.noSchedule).map(zoneMultiPolygon));
if(polygonClipping.intersection(contractArea,unknownArea).length)throw Error('boundary and neutral overlap');
activeDay='월';const filtered=partitionOchang2023Display('general',[z]);
if(filtered.some(x=>x.noSchedule))throw Error('weekday filter showed unknown schedule');
`);
console.log('PASS 2023 boundary: inside/outside, both waste types, clipped lines, unchanged cache, coverage, no overlap, filters');

check("activeDay='전체';routeLayerMatchedColor('general',{vehicle:'6224',day:'화',districts:['오근장동']})");
console.log('PASS live route color uses test-page display registry');
