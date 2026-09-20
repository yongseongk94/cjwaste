from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

old="const SERVICE_ZONE_CACHE_VERSION=`zone-v83-route-overlay-based|${DONG_ROUTE_CACHE_VERSION}`;"
new="const SERVICE_ZONE_CACHE_VERSION=`zone-v84-latest-route-evidence|${DONG_ROUTE_CACHE_VERSION}`;\nconst SERVICE_ZONE_PRECOMPUTE_ONLY=new URLSearchParams(location.search).get('zone_only')==='1';"
if s.count(old)!=1:
    raise SystemExit(f'zone version match={s.count(old)}')
s=s.replace(old,new,1)

hint_old="""const VERIFIED_ROUTE_ADDRESS_HINTS={
  '아르떼웨딩홀':'청주시 청원구 사천로 33',"""
hint_new="""const VERIFIED_ROUTE_ADDRESS_HINTS={
  // v84: 북이면 장양리 최신 노선 경유 순서(장양2리 → 장양1리 → 장양3리)를
  // 마을회관/경로당의 확인된 도로명주소로 고정해 동명이소 검색을 막습니다.
  '장양1리':'청주시 청원구 북이면 장양1길 29-3',
  '장양2리':'청주시 청원구 북이면 장양2길 81-1',
  '장양3리':'청주시 청원구 북이면 장양3길 13',
  '아르떼웨딩홀':'청주시 청원구 사천로 33',"""
if s.count(hint_old)!=1:
    raise SystemExit(f'hint match={s.count(hint_old)}')
s=s.replace(hint_old,hint_new,1)

hydrate_old="""    // 저장된 자동권역이 있으면 네트워크/재계산 없이 즉시 복원합니다.
    if(await hydrateCachedServiceZones(type))return;
    // 새 브라우저는 manifest/chunk를 먼저 복원합니다. 정적 권역이 있으면 무거운 전지역 재계산을 하지 않습니다.
    if(await hydrateExternalBundledServiceZones()){
      if(serviceZoneBuilt[type]){syncServiceZoneVisibility(type);return}
    }
    if(!serviceRegionLoadComplete)return;"""
hydrate_new="""    // 일반 접속은 캐시/정적 번들을 즉시 사용합니다.
    // zone_only=1 사전생성 작업은 반드시 현재 최신 코스에서 새로 계산하여 과거 권역 재사용을 막습니다.
    if(!SERVICE_ZONE_PRECOMPUTE_ONLY){
      if(await hydrateCachedServiceZones(type))return;
      if(await hydrateExternalBundledServiceZones()){
        if(serviceZoneBuilt[type]){syncServiceZoneVisibility(type);return}
      }
    }
    if(!serviceRegionLoadComplete)return;"""
if s.count(hydrate_old)!=1:
    raise SystemExit(f'hydrate block match={s.count(hydrate_old)}')
s=s.replace(hydrate_old,hydrate_new,1)

evidence_old="""      // 도로선이 만들어지지 않는 시설·마을명도 권역 분할에는 중요한 근거입니다.
      // 단, 실제 지도에는 별도 원/마커를 그리지 않습니다.
      if(base && !entry.isRoad){
        zoneEvidencePoints.push({lat:+base.lat,lng:+base.lng,name:base.name||entry.term,address:base.address||'',term:entry.term,district:base.district||routePointAnyDistrict(base)||''});
      }
      const anchors=await serviceAnchorsForEntry(entry,spec);"""
evidence_new="""      // 도로선이 만들어지지 않는 시설·마을명도 권역 분할에는 중요한 근거입니다.
      // zone_only 사전생성에서는 읍·면의 도로명 항목도 근거점으로 사용하고 길찾기 API 호출은 생략합니다.
      const baseDistrict=canonicalDistrict(base?.district||routePointAnyDistrict(base));
      const zoneOnlyRural=!!base&&SERVICE_ZONE_PRECOMPUTE_ONLY&&RURAL_INFERRED_ROUTE_DISTRICTS.has(baseDistrict);
      if(base && (!entry.isRoad||zoneOnlyRural)){
        zoneEvidencePoints.push({lat:+base.lat,lng:+base.lng,name:base.name||entry.term,address:base.address||'',term:entry.term,district:baseDistrict||''});
      }
      if(zoneOnlyRural){
        serviceTermCount++;
        if(baseDistrict&&!touchedDistricts.includes(baseDistrict))touchedDistricts.push(baseDistrict);
        continue;
      }
      const anchors=await serviceAnchorsForEntry(entry,spec);"""
if s.count(evidence_old)!=1:
    raise SystemExit(f'evidence block match={s.count(evidence_old)}')
s=s.replace(evidence_old,evidence_new,1)

inferred_old="    const inferredMovement=await inferredRuralMovementSegments(ruralMovementAnchors);"
inferred_new="    const inferredMovement=SERVICE_ZONE_PRECOMPUTE_ONLY?{segments:[],inferredMovementCount:0}:await inferredRuralMovementSegments(ruralMovementAnchors);"
if s.count(inferred_old)!=1:
    raise SystemExit(f'inferred match={s.count(inferred_old)}')
s=s.replace(inferred_old,inferred_new,1)

count=s.count("  scheduleDongRoutePreload();")
if count<2:
    raise SystemExit(f'schedule preload occurrences={count}')
s=s.replace("  scheduleDongRoutePreload();","  if(!SERVICE_ZONE_PRECOMPUTE_ONLY)scheduleDongRoutePreload();")

init_old="""  hydrateCachedServiceZones('general').then(async cached=>{
    if(!cached)await hydrateExternalBundledServiceZones();
    if(activeLayer==='general')setLayer('general');
  }).catch(e=>console.warn('생활 추정권역 초기 복원 실패',e));
  hydrateCachedServiceZones('recycle').then(async cached=>{
    if(!cached)await hydrateExternalBundledServiceZones();
  }).catch(e=>console.warn('재활용 추정권역 초기 복원 실패',e));"""
init_new="""  if(!SERVICE_ZONE_PRECOMPUTE_ONLY){
    hydrateCachedServiceZones('general').then(async cached=>{
      if(!cached)await hydrateExternalBundledServiceZones();
      if(activeLayer==='general')setLayer('general');
    }).catch(e=>console.warn('생활 추정권역 초기 복원 실패',e));
    hydrateCachedServiceZones('recycle').then(async cached=>{
      if(!cached)await hydrateExternalBundledServiceZones();
    }).catch(e=>console.warn('재활용 추정권역 초기 복원 실패',e));
  }"""
if s.count(init_old)!=1:
    raise SystemExit(f'init hydration match={s.count(init_old)}')
s=s.replace(init_old,init_new,1)

required=[
    'zone-v84-latest-route-evidence',
    'SERVICE_ZONE_PRECOMPUTE_ONLY',
    "'장양1리':'청주시 청원구 북이면 장양1길 29-3'",
    "'장양2리':'청주시 청원구 북이면 장양2길 81-1'",
    "'장양3리':'청주시 청원구 북이면 장양3길 13'",
    'const zoneOnlyRural='
]
for x in required:
    if x not in s:
        raise SystemExit('missing '+x)
p.write_text(s,encoding='utf-8')

wp=Path('.github/workflows/v83-service-zones-refresh.yml')
w=wp.read_text(encoding='utf-8')
w=w.replace('zone-v83-route-overlay-based','zone-v84-latest-route-evidence')
w=w.replace('service-zones-v83-','service-zones-v84-')
w=w.replace('v83_zone_refresh=', 'zone_only=1&v84_zone_refresh=')
w=w.replace('V83_ZONE_STATS','V84_ZONE_STATS')
w=w.replace('v83-zone-stats','v84-zone-stats')
w=w.replace('v83 service zones','v84 service zones')
w=w.replace('v83 service-zone','v84 service-zone')
wp.write_text(w,encoding='utf-8')
print('v84 patch applied')
