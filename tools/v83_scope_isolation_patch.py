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
"""function routeDongScope(type,vehicle,day=''){
  const cm=contractRouteMeta(vehicle);if(cm)return [canonicalDistrict(cm.district)];
  const exact=day&&ROUTE_DONG_DAY_SCOPE[type]?.[vehicle]?.[day];
  return [...(exact||ROUTE_DONG_SCOPE[type]?.[vehicle]||[])].map(canonicalDistrict);
}""",
"""function routeDongScope(type,vehicle,day=''){
  const cm=contractRouteMeta(vehicle);if(cm)return [canonicalDistrict(cm.district)];
  const exact=day&&ROUTE_DONG_DAY_SCOPE[type]?.[vehicle]?.[day];
  // 직영 기본노선은 동지역만 유지합니다. 읍·면은 routeRuralScope()에서 요일별 별도 범위로 생성합니다.
  return [...(exact||ROUTE_DONG_SCOPE[type]?.[vehicle]||[])]
    .map(canonicalDistrict)
    .filter(d=>DONG_ROUTE_DISTRICTS.has(d));
}""",
"direct base scope must be dong only"
)

once(
"""      for(const r of (data.routes||[])){
        const spec=(Array.isArray(r.districts)&&r.districts.length)
          ? exactMap.get(`${r.type}|${r.vehicle}|${r.day}|${routeScopeSignature(r)}`)
          : baseMap.get(`${r.type}|${r.vehicle}|${r.day}`);
        if(!spec||existingDongRouteOverlay(spec))continue;
        createDongRouteOverlay(spec,{...(r.data||{}),fromCache:true,fromBundle:true});
      }""",
"""      for(const r of (data.routes||[])){
        const hasExplicitScope=Array.isArray(r.districts)&&r.districts.length;
        const spec=hasExplicitScope
          ? exactMap.get(`${r.type}|${r.vehicle}|${r.day}|${routeScopeSignature(r)}`)
          : baseMap.get(`${r.type}|${r.vehicle}|${r.day}`);
        if(!spec||existingDongRouteOverlay(spec))continue;
        // v76 내장본은 일부 직영 차량에서 동지역+읍면 범위가 한 캐시에 섞여 있었습니다.
        // 명시적 범위정보가 없는 구형 번들은 해당 요일의 과거 범위에 읍면이 섞였으면 재사용하지 않고 다시 계산합니다.
        if(!hasExplicitScope&&!routeCompany(spec.vehicle)){
          const legacyExact=ROUTE_DONG_DAY_SCOPE[r.type]?.[r.vehicle]?.[r.day];
          const legacyScope=[...(legacyExact||ROUTE_DONG_SCOPE[r.type]?.[r.vehicle]||[])].map(canonicalDistrict);
          if(legacyScope.some(d=>RURAL_INFERRED_ROUTE_DISTRICTS.has(d)))continue;
        }
        createDongRouteOverlay(spec,{...(r.data||{}),fromCache:true,fromBundle:true});
      }""",
"skip legacy mixed-scope bundle routes"
)

once(
"""  const bundled=hydrateBundledPrecomputedData();
  if(!bundled)await hydrateCachedRouteOverlays(specs);
  if(activeLayer==='general'||activeLayer==='recycle')syncDongRouteVisibility(activeLayer);""",
"""  hydrateBundledPrecomputedData();
  // 내장 v76 노선이 일부 복원돼도, 범위키가 다른 읍·면/재계산 노선은 IndexedDB에서 항상 추가 복원합니다.
  await hydrateCachedRouteOverlays(specs);
  if(activeLayer==='general'||activeLayer==='recycle')syncDongRouteVisibility(activeLayer);""",
"always hydrate scoped IndexedDB routes"
)

once(
"""  specs=specs.map(s=>{
    if(RI_LAYER_DISTRICTS.has(district))return {...s,districts:[district],scopeKind:'rural'};
    const districts=Array.isArray(s.districts)&&s.districts.length?s.districts:[...serviceZoneRouteScope(type,s.vehicle)];
    return {...s,districts,scopeKind:s.scopeKind||'base'};
  });""",
"""  specs=specs.map(s=>{
    if(RI_LAYER_DISTRICTS.has(district))return {...s,districts:[district],scopeKind:'rural'};
    // 동지역 추정권역용 근거노선도 읍·면이 섞인 SERVICE_ZONE_ROUTE_SCOPE를 쓰지 않고
    // 실제 동지역 표시범위와 동일한 routeDongScope를 재사용합니다.
    const districts=routeDongScope(type,s.vehicle,s.day);
    return {...s,districts,scopeKind:s.scopeKind||'base'};
  }).filter(s=>s.districts.length);""",
"service zone direct scope isolation"
)

once(
"const SERVICE_ZONE_CACHE_VERSION=`zone-v83-3-all-rural-route-estimate|${DONG_ROUTE_CACHE_VERSION}`;",
"const SERVICE_ZONE_CACHE_VERSION=`zone-v83-4-scope-isolation|${DONG_ROUTE_CACHE_VERSION}`;",
"service zone cache bump"
)

required=[
  ".filter(d=>DONG_ROUTE_DISTRICTS.has(d));",
  "if(!hasExplicitScope&&!routeCompany(spec.vehicle)){",
  "await hydrateCachedRouteOverlays(specs);",
  "zone-v83-4-scope-isolation",
]
for token in required:
    if token not in s:
        raise SystemExit(f"missing required token: {token}")

p.write_text(s,encoding="utf-8")
