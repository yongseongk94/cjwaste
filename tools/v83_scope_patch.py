from pathlib import Path

p=Path("index.html")
s=p.read_text(encoding="utf-8")

def once(old,new,label):
    global s
    n=s.count(old)
    if n!=1:
        raise SystemExit(f"{label}: expected 1 match, found {n}")
    s=s.replace(old,new,1)

once(
"const RURAL_INFERRED_ROUTE_DISTRICTS=new Set(['오창읍','내수읍','북이면']);\nconst RURAL_ROUTE_MATCH_KM=0.030;",
"const RURAL_INFERRED_ROUTE_DISTRICTS=new Set(['오창읍','내수읍','북이면']);\n// 실제 ② 수거노선 레이어에 단계적으로 공개할 읍·면. 먼저 오창만 활성화합니다.\nconst RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍']);\nconst RURAL_ROUTE_MATCH_KM=0.030;",
"rural layer set"
)

once(
"""function routeDongScope(type,vehicle,day=''){
  const cm=contractRouteMeta(vehicle);if(cm)return [canonicalDistrict(cm.district)];
  const exact=day&&ROUTE_DONG_DAY_SCOPE[type]?.[vehicle]?.[day];
  const base=[...(exact||ROUTE_DONG_SCOPE[type]?.[vehicle]||[])].map(canonicalDistrict);
  // v83-1: 오창만 먼저 동지역과 같은 ② 수거노선 구조에 포함합니다.
  const ruralByDay=day
    ? [...(DIRECT_INFERRED_REGIONS?.[type]?.[vehicle]?.[day]||[])]
    : [...(SERVICE_ZONE_ROUTE_SCOPE[type]?.[vehicle]||[])];
  const ochang=ruralByDay.map(canonicalDistrict).filter(d=>d==='오창읍');
  return [...new Set([...base,...ochang])];
}""",
"""function routeDongScope(type,vehicle,day=''){
  const cm=contractRouteMeta(vehicle);if(cm)return [canonicalDistrict(cm.district)];
  const exact=day&&ROUTE_DONG_DAY_SCOPE[type]?.[vehicle]?.[day];
  return [...(exact||ROUTE_DONG_SCOPE[type]?.[vehicle]||[])].map(canonicalDistrict);
}
function routeRuralScope(type,vehicle,day=''){
  if(contractRouteMeta(vehicle))return [];
  const src=day
    ? [...(DIRECT_INFERRED_REGIONS?.[type]?.[vehicle]?.[day]||[])]
    : [...(SERVICE_ZONE_ROUTE_SCOPE[type]?.[vehicle]||[])];
  return [...new Set(src.map(canonicalDistrict).filter(d=>RURAL_ROUTE_LAYER_DISTRICTS.has(d)))];
}
function routeAllowedDistricts(spec){
  const src=Array.isArray(spec?.districts)&&spec.districts.length
    ? spec.districts
    : routeDongScope(spec?.type,spec?.vehicle,spec?.day);
  return [...new Set(src.map(canonicalDistrict).filter(Boolean))];
}
function routeScopeSignature(spec){
  return routeAllowedDistricts(spec).slice().sort().join('|');
}""",
"separate base and rural scope"
)

once(
"""function routeCacheKey(spec){
  return `${DONG_ROUTE_CACHE_VERSION}|${spec.type}|${spec.vehicle}|${spec.day}|${routeTextHash(spec.raw)}`;
}""",
"""function routeScopeCacheSuffix(spec){
  const base=[...routeDongScope(spec?.type,spec?.vehicle,spec?.day)].map(canonicalDistrict).filter(Boolean).sort();
  const scope=routeAllowedDistricts(spec).slice().sort();
  return base.join('|')===scope.join('|')?'':`|scope-${routeTextHash(scope.join('|'))}`;
}
function routeCacheKey(spec){
  return `${DONG_ROUTE_CACHE_VERSION}|${spec.type}|${spec.vehicle}|${spec.day}|${routeTextHash(spec.raw)}${routeScopeCacheSuffix(spec)}`;
}""",
"scope cache key"
)

once(
"""function existingDongRouteOverlay(spec){
  return (dongRouteOverlays[spec.type]||[]).find(x=>x.vehicle===spec.vehicle&&x.day===spec.day) || null;
}""",
"""function existingDongRouteOverlay(spec){
  const scopeKey=routeScopeSignature(spec);
  return (dongRouteOverlays[spec.type]||[]).find(x=>
    x.vehicle===spec.vehicle &&
    x.day===spec.day &&
    routeScopeSignature(x)===scopeKey
  ) || null;
}""",
"scope overlay identity"
)

once(
"  const buildKey=`${spec.type}|${spec.vehicle}|${spec.day}`;",
"  const buildKey=`${spec.type}|${spec.vehicle}|${spec.day}|${routeScopeSignature(spec)}`;",
"scope build key"
)

count=s.count("routeDongScope(spec.type,spec.vehicle,spec.day)")
if count!=5:
    raise SystemExit(f"routeAllowed replacements: expected 5, found {count}")
s=s.replace("routeDongScope(spec.type,spec.vehicle,spec.day)","routeAllowedDistricts(spec)")

once(
"""function routeCandidatesForSelection(type){
  const provider=selectedVehicle[type]||'전체';
  const day=activeDay||'전체';
  const out=[];
  for(const route of routeCatalog(type)){
    if(provider!=='전체'&&!routeSelectedBy(provider,route.vehicle))continue;
    for(const [routeDay,raw] of Object.entries(route.days||{})){
      if(day!=='전체'&&routeDay!==day)continue;
      const districts=routeDongScope(type,route.vehicle,routeDay);
      if(!districts.length)continue;
      out.push({type,vehicle:route.vehicle,provider:route.provider||'',plate:route.plate||route.vehicle,housing:route.housing||'single',zoneEligible:route.zoneEligible!==false,day:routeDay,raw,districts:[...districts]});
    }
  }
  return out;
}""",
"""function routeCandidatesForSelection(type){
  const provider=selectedVehicle[type]||'전체';
  const day=activeDay||'전체';
  const out=[];
  for(const route of routeCatalog(type)){
    if(provider!=='전체'&&!routeSelectedBy(provider,route.vehicle))continue;
    for(const [routeDay,raw] of Object.entries(route.days||{})){
      if(day!=='전체'&&routeDay!==day)continue;
      const common={type,vehicle:route.vehicle,provider:route.provider||'',plate:route.plate||route.vehicle,housing:route.housing||'single',zoneEligible:route.zoneEligible!==false,day:routeDay,raw};
      const base=(route.districts?.length?[...route.districts]:routeDongScope(type,route.vehicle,routeDay)).map(canonicalDistrict);
      if(base.length)out.push({...common,districts:[...new Set(base)],scopeKind:'base'});
      const rural=routeRuralScope(type,route.vehicle,routeDay);
      if(rural.length)out.push({...common,districts:rural,scopeKind:'rural'});
    }
  }
  return out;
}""",
"route selection specs"
)

once(
"""function allDongRouteSpecs(){
  const out=[];const seen=new Set();
  for(const type of ['general','recycle']){
    for(const route of routeCatalog(type)){
      for(const [day,raw] of Object.entries(route.days||{})){
        const districts=(route.districts?.length?[...route.districts]:routeDongScope(type,route.vehicle,day)).map(canonicalDistrict);
        if(!districts.length)continue;
        const key=`${type}|${route.vehicle}|${day}`;if(seen.has(key))continue;seen.add(key);
        out.push({type,vehicle:route.vehicle,provider:route.provider||'',plate:route.plate||route.vehicle,housing:route.housing||'single',zoneEligible:route.zoneEligible!==false,day,raw,districts});
      }
    }
  }
  return out;
}""",
"""function allDongRouteSpecs(){
  const out=[];const seen=new Set();
  const pushSpec=(spec)=>{
    const key=`${spec.type}|${spec.vehicle}|${spec.day}|${routeScopeSignature(spec)}`;
    if(seen.has(key))return;
    seen.add(key);out.push(spec);
  };
  for(const type of ['general','recycle']){
    for(const route of routeCatalog(type)){
      for(const [day,raw] of Object.entries(route.days||{})){
        const common={type,vehicle:route.vehicle,provider:route.provider||'',plate:route.plate||route.vehicle,housing:route.housing||'single',zoneEligible:route.zoneEligible!==false,day,raw};
        const base=(route.districts?.length?[...route.districts]:routeDongScope(type,route.vehicle,day)).map(canonicalDistrict);
        if(base.length)pushSpec({...common,districts:[...new Set(base)],scopeKind:'base'});
        const rural=routeRuralScope(type,route.vehicle,day);
        if(rural.length)pushSpec({...common,districts:rural,scopeKind:'rural'});
      }
    }
  }
  return out;
}""",
"all route specs"
)

once(
"""function syncDongRouteVisibility(type){
  Object.values(dongRouteOverlays).flat().forEach(item=>setRouteItemMap(item,null));
  if(activeLayer!==type||(type!=='general'&&type!=='recycle')||!serviceLayerState.route)return;
  const provider=selectedVehicle[type]||'전체';
  const day=activeDay||'전체';
  for(const item of dongRouteOverlays[type]){
    if(provider!=='전체'&&!routeSelectedBy(provider,item.vehicle))continue;
    if(day!=='전체'&&item.day!==day)continue;
    setRouteItemOptions(item,{strokeColor:DAY_COLORS[item.day]||'#334155'});
    setRouteItemMap(item,map);
  }
}""",
"""function syncDongRouteVisibility(type){
  Object.values(dongRouteOverlays).flat().forEach(item=>setRouteItemMap(item,null));
  if(activeLayer!==type||(type!=='general'&&type!=='recycle')||!serviceLayerState.route)return;
  const provider=selectedVehicle[type]||'전체';
  const day=activeDay||'전체';
  for(const item of dongRouteOverlays[type]){
    if(item.scopeKind==='rural'&&!routeAllowedDistricts(item).some(d=>RURAL_ROUTE_LAYER_DISTRICTS.has(d)))continue;
    if(provider!=='전체'&&!routeSelectedBy(provider,item.vehicle))continue;
    if(day!=='전체'&&item.day!==day)continue;
    setRouteItemOptions(item,{strokeColor:DAY_COLORS[item.day]||'#334155'});
    setRouteItemMap(item,map);
  }
}""",
"route visibility"
)

once(
"""    if(data.version===DONG_ROUTE_CACHE_VERSION){
      const specMap=new Map(allDongRouteSpecs().map(s=>[`${s.type}|${s.vehicle}|${s.day}`,s]));
      for(const r of (data.routes||[])){
        const spec=specMap.get(`${r.type}|${r.vehicle}|${r.day}`);
        if(!spec||existingDongRouteOverlay(spec))continue;
        createDongRouteOverlay(spec,{...(r.data||{}),fromCache:true,fromBundle:true});
      }
      hydrated=true;
    }""",
"""    if(data.version===DONG_ROUTE_CACHE_VERSION){
      const specs=allDongRouteSpecs();
      const baseMap=new Map(specs.filter(s=>s.scopeKind!=='rural').map(s=>[`${s.type}|${s.vehicle}|${s.day}`,s]));
      const exactMap=new Map(specs.map(s=>[`${s.type}|${s.vehicle}|${s.day}|${routeScopeSignature(s)}`,s]));
      for(const r of (data.routes||[])){
        const spec=(Array.isArray(r.districts)&&r.districts.length)
          ? exactMap.get(`${r.type}|${r.vehicle}|${r.day}|${routeScopeSignature(r)}`)
          : baseMap.get(`${r.type}|${r.vehicle}|${r.day}`);
        if(!spec||existingDongRouteOverlay(spec))continue;
        createDongRouteOverlay(spec,{...(r.data||{}),fromCache:true,fromBundle:true});
      }
      hydrated=true;
    }""",
"bundle hydration"
)

once(
"    routes.push({type,vehicle:item.vehicle,day:item.day,data});",
"    routes.push({type,vehicle:item.vehicle,day:item.day,districts:routeAllowedDistricts(item),scopeKind:item.scopeKind||'base',data});",
"bundle export route scope"
)

once(
"""  specs=specs.map(s=>({...s,districts:Array.isArray(s.districts)&&s.districts.length?s.districts:[...serviceZoneRouteScope(type,s.vehicle)]}));
  if(district==='오창읍'&&contractSpecs.length)specs.push(...contractSpecs);""",
"""  specs=specs.map(s=>{
    if(RI_LAYER_DISTRICTS.has(district))return {...s,districts:[district],scopeKind:'rural'};
    const districts=Array.isArray(s.districts)&&s.districts.length?s.districts:[...serviceZoneRouteScope(type,s.vehicle)];
    return {...s,districts,scopeKind:s.scopeKind||'base'};
  });
  if(district==='오창읍'&&contractSpecs.length)specs.push(...contractSpecs.map(s=>({...s,scopeKind:'base'})));""",
"rural service specs"
)

once(
"const SERVICE_ZONE_CACHE_VERSION=`zone-v83-1-ochang-route-estimate|${DONG_ROUTE_CACHE_VERSION}`;",
"const SERVICE_ZONE_CACHE_VERSION=`zone-v83-1a-scope-separated|${DONG_ROUTE_CACHE_VERSION}`;",
"zone cache version"
)

required=[
  "const RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍']);",
  "function routeRuralScope(type,vehicle,day='')",
  "function routeAllowedDistricts(spec)",
  "function routeScopeSignature(spec)",
  "scopeKind:'rural'",
  "zone-v83-1a-scope-separated",
]
for token in required:
    if token not in s:
        raise SystemExit(f"missing required token: {token}")

p.write_text(s,encoding="utf-8")
