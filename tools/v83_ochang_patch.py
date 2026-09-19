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
'<button class="active" data-structure="zone">① 추정권역</button>',
'<button class="active" data-structure="zone">① 추정지역</button>',
"zone label"
)
once(
'<button class="active" data-structure="route">② 근거노선</button>',
'<button class="active" data-structure="route">② 수거노선</button>',
"route label"
)

once(
"const RURAL_INFERRED_ROUTE_DISTRICTS=new Set(['내수읍','북이면']);",
"const RURAL_INFERRED_ROUTE_DISTRICTS=new Set(['오창읍','내수읍','북이면']);",
"rural districts"
)

once(
"function routeMatchLimitKm(district){return RURAL_INFERRED_ROUTE_DISTRICTS.has(canonicalDistrict(district))?RURAL_ROUTE_MATCH_KM:MAX_ADDRESS_ROUTE_DISTANCE_KM} // 주소점에서 실제 표시 수거노선 20m 이내만 수거일정으로 인정",
"function routeMatchLimitKm(district){const d=canonicalDistrict(district);return d==='오창읍'?MAX_ADDRESS_ROUTE_DISTANCE_KM:(RURAL_INFERRED_ROUTE_DISTRICTS.has(d)?RURAL_ROUTE_MATCH_KM:MAX_ADDRESS_ROUTE_DISTANCE_KM)} // 오창 20m, 내수·북이는 이번 단계에서 기존 30m 유지",
"route match limit"
)

once(
"""function routeDongScope(type,vehicle,day=''){
  const cm=contractRouteMeta(vehicle);if(cm)return [canonicalDistrict(cm.district)];
  const exact=day&&ROUTE_DONG_DAY_SCOPE[type]?.[vehicle]?.[day];
  return [...(exact||ROUTE_DONG_SCOPE[type]?.[vehicle]||[])];
}""",
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
"routeDongScope"
)

once(
"const SERVICE_ZONE_CACHE_VERSION=`zone-v76-layer-visibility-refresh|${DONG_ROUTE_CACHE_VERSION}`;",
"const SERVICE_ZONE_CACHE_VERSION=`zone-v83-1-ochang-route-estimate|${DONG_ROUTE_CACHE_VERSION}`;",
"service zone cache version"
)

once(
"""async function buildRuralRiServiceZone(type,region){
  const meta=ruralRiZoneMeta(type,region);
  if(!meta)return false;
  if(RURAL_INFERRED_ROUTE_DISTRICTS.has(region.district)){
    // 리 단위 묶음은 외곽선/약한 배경으로만 유지하고, 실제 일정권역은 노선 30m 통로입니다.
    wholeFeatureZone(type,region.feature,{...meta,noSchedule:true,groupOutline:true,days:[]});
    await buildRuralRouteBufferZones(type,region);
    return true;
  }
  // 오창읍은 기존 v66 리 단위 권역을 유지하며 산업단지 대행구간은 별도 색상으로 표시합니다.
  wholeFeatureZone(type,region.feature,meta);
  return true;
}""",
"""async function buildRuralRiServiceZone(type,region){
  const meta=ruralRiZoneMeta(type,region);
  if(!meta)return false;
  if(region.district==='오창읍'){
    // v83-1: 오창은 실제 차량×요일 수거노선을 근거로 빈 공간을 ① 추정지역으로 나눕니다.
    // 표시 수거노선 20m 범위는 확정구간으로 남기고 추정 폴리곤에서 제외합니다.
    const groups=await serviceRouteGroups(type,region.district,region.riName||'');
    const usable=groups.filter(g=>g.items.length);
    if(!usable.length)return false;
    await buildGridServiceZonesForRegion(type,region,usable);
    return true;
  }
  if(RURAL_INFERRED_ROUTE_DISTRICTS.has(region.district)){
    // 내수·북이는 이번 단계에서 v76 구조를 그대로 유지합니다.
    wholeFeatureZone(type,region.feature,{...meta,noSchedule:true,groupOutline:true,days:[]});
    await buildRuralRouteBufferZones(type,region);
    return true;
  }
  wholeFeatureZone(type,region.feature,meta);
  return true;
}""",
"build rural service zone"
)

once(
"""    if(RURAL_INFERRED_ROUTE_DISTRICTS.has(district)){
      const near=await nearestRouteMatchesForAddress(type,{...ctx,district,legalEmd:district});
      if(seq!==nearbyScheduleRequestSeq)return;
      if(near?.length)renderNearbyRouteSchedule(type,near,ctx);
      else if(!renderRestoredRuralRiSchedule(type,ctx))renderNoNearbyRouteSchedule(type,district);
      continue;
    }
    if(DONG_ROUTE_DISTRICTS.has(district)){""",
"""    if(district==='오창읍'){
      // v83-1: 오창은 동지역과 동일하게 20m 실제 수거노선을 우선하고,
      // 그 밖의 주소는 노선 기반 ① 추정지역으로 판정합니다.
      const near=await nearestRouteMatchesForAddress(type,{...ctx,district,legalEmd:district});
      if(seq!==nearbyScheduleRequestSeq)return;
      if(near?.length){renderNearbyRouteSchedule(type,near,ctx);continue}
      const match=await ensureServiceZoneMatch(type,{...ctx,district,legalEmd:district});
      if(seq!==nearbyScheduleRequestSeq)return;
      if(match)renderServiceZoneSchedule(type,{...match,estimated:true,zoneStatus:'estimated'},ctx);
      else if(!renderRestoredRuralRiSchedule(type,ctx))renderNoNearbyRouteSchedule(type,district);
      continue;
    }
    if(RURAL_INFERRED_ROUTE_DISTRICTS.has(district)){
      const near=await nearestRouteMatchesForAddress(type,{...ctx,district,legalEmd:district});
      if(seq!==nearbyScheduleRequestSeq)return;
      if(near?.length)renderNearbyRouteSchedule(type,near,ctx);
      else if(!renderRestoredRuralRiSchedule(type,ctx))renderNoNearbyRouteSchedule(type,district);
      continue;
    }
    if(DONG_ROUTE_DISTRICTS.has(district)){""",
"refresh nearby schedules"
)

once(
"""  setLayer('general');
  // 내장 좌표는 즉시 렌더링하고, 행정경계/누락분 점검은 뒤에서 진행합니다.
  scheduleDongRoutePreload();
  zoneBuildPromise=buildZonePolygons();""",
"""  setLayer('general');
  // v83-1: 기존 내장 좌표는 즉시 복원하되, 오창 신규노선 계산은 행정경계가 준비된 뒤 시작합니다.
  // buildZonePolygons() 끝에서 scheduleDongRoutePreload()가 호출됩니다.
  zoneBuildPromise=buildZonePolygons();""",
"init preload order"
)

required=[
    "zone-v83-1-ochang-route-estimate",
    "const ochang=ruralByDay.map(canonicalDistrict).filter(d=>d==='오창읍');",
    "if(region.district==='오창읍'){",
    "if(district==='오창읍'){",
    "① 추정지역",
    "② 수거노선",
]
for token in required:
    if token not in s:
        raise SystemExit(f"missing required token: {token}")

p.write_text(s,encoding="utf-8")
