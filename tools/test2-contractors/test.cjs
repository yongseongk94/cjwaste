// Offline regression checks: no browser or network requests.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'../..');
const html=fs.readFileSync(root+'/cjwaste-test2/index.html','utf8');
let js=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');
js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document:{getElementById:()=>({getAttribute:()=>'',textContent:'',classList:{contains:()=>true}})},localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{}});
vm.runInContext(js,ctx);
const packed=JSON.parse(fs.readFileSync(root+'/cjwaste-test2/data/precomputed-routes-contractor-groups-v1.json'));
const base=JSON.parse(fs.readFileSync(root+'/data/precomputed-routes-v76-layer-visibility-refresh-a1e5f19fa4da.json'));
assert.deepStrictEqual(packed.routes.filter(r=>!r.dataRef),base.routes.filter(r=>!r.vehicle.includes('환경|')),'direct routes changed');
for(const r of packed.routes.filter(r=>r.dataRef))assert(packed.geometryPool[r.dataRef]);
ctx.packed=packed;
vm.runInContext(`{
 for(const type of ['general','recycle'])for(const r of CONTRACT_ROUTES[type])for(const days of [['월','수','금'],['화','목']]){
   const present=days.filter(d=>r.days[d]);const keys=present.map(day=>routeCacheKey({...r,type,day,raw:r.days[day]}));
   if(new Set(keys).size>1)throw Error('weekday cache mismatch '+r.vehicle);
 }
 const saved=dongRouteOverlays;const fakeMap={};map=fakeMap;let calls=0;
 const line=()=>{let target=null;return {getMap:()=>target,setMap:m=>{calls++;target=m},setOptions:()=>{}}};
 const p=line(),q=line(),r=line();
 dongRouteOverlays.general=[{type:'general',vehicle:'3344',day:'화',geometryKey:'a',polylines:[p]},{type:'general',vehicle:'3344',day:'목',geometryKey:'a',polylines:[p]},{type:'general',vehicle:'3344',day:'월',geometryKey:'b',polylines:[q]}];
 dongRouteOverlays.recycle=[{type:'recycle',vehicle:'0262',day:'화',geometryKey:'c',polylines:[r]}];
 routeLayerMatchedColor=()=> '#123456';serviceLayerState.route=true;selectedVehicle.general='전체';selectedVehicle.recycle='전체';activeLayer='general';activeDay='화';
 syncDongRouteVisibility('general');if(p.getMap()!==map||q.getMap()||r.getMap())throw Error('initial visibility');
 calls=0;activeDay='목';syncDongRouteVisibility('general');if(calls!==0)throw Error('same geometry detached');
 for(let i=0;i<20;i++){activeLayer=i%2?'general':'recycle';activeDay='화';syncDongRouteVisibility(activeLayer);if((p.getMap()===map)!==(activeLayer==='general')||(r.getMap()===map)!==(activeLayer==='recycle')||q.getMap())throw Error('rapid-switch stale lines');}
 serviceLayerState.route=false;syncDongRouteVisibility(activeLayer);if(p.getMap()||q.getMap()||r.getMap())throw Error('disabled route visible');
}`,ctx);
console.log('PASS offline: direct routes unchanged, shared weekday caches, zero redraw on shared days, rapid layer switches, route toggle');
