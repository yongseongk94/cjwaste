from pathlib import Path
p=Path("index.html")
s=p.read_text(encoding="utf-8")
def once(old,new,label):
    global s
    n=s.count(old)
    if n!=1: raise SystemExit(f"{label}: expected 1 match, found {n}")
    s=s.replace(old,new,1)

once(
"const RURAL_INFERRED_ROUTE_DISTRICTS=new Set(['내수읍','북이면']);\nconst RURAL_ROUTE_MATCH_KM=0.030;",
"const RURAL_INFERRED_ROUTE_DISTRICTS=new Set(['오창읍','내수읍','북이면']);\nconst RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍']);\nconst RURAL_ROUTE_MATCH_KM=0.030;",
"ochang activation set")

once(
"function routeMatchLimitKm(district){return RURAL_INFERRED_ROUTE_DISTRICTS.has(canonicalDistrict(district))?RURAL_ROUTE_MATCH_KM:MAX_ADDRESS_ROUTE_DISTANCE_KM} // 주소점에서 실제 표시 수거노선 20m 이내만 수거일정으로 인정",
"function routeMatchLimitKm(district){const d=canonicalDistrict(district);return RURAL_ROUTE_LAYER_DISTRICTS.has(d)?MAX_ADDRESS_ROUTE_DISTANCE_KM:(RURAL_INFERRED_ROUTE_DISTRICTS.has(d)?RURAL_ROUTE_MATCH_KM:MAX_ADDRESS_ROUTE_DISTANCE_KM)} // 3단계: 오창 20m, 내수·북이는 기존 30m 유지",
"ochang 20m")

once(
"""function routeDongScope(type,vehicle,day=''){
  const cm=contractRouteMeta(vehicle);if(cm)return [canonicalDistrict(cm.district)];
  const exact=day&&ROUTE_DONG_DAY_SCOPE[type]?.[vehicle]?.[day];
  return [...(exact||ROUTE_DONG_SCOPE[type]?.[vehicle]||[])];
}""",
"""function routeDongScope(type,vehicle,day=''){
  const cm=contractRouteMeta(vehicle);if(cm)return [canonicalDistrict(cm.district)];
  const exact=day&&ROUTE_DONG_DAY_SCOPE[type]?.[vehicle]?.[day];
  return [...(exact||ROUTE_DONG_SCOPE[type]?.[vehicle]||[])];
}
function routeRuralScope(type,vehicle,day=''){
  if(contractRouteMeta(vehicle))return [];
  const src=day
    ? [...(DIRECT_INFERRED_REGIONS?.[type]?.[vehicle]?.[day]||[])]
    : [...(SERVICE_ZONE_ROUTE_SCOPE[type]?.[vehicle]||[])];
  return [...new Set(src.map(canonicalDistrict).filter(d=>RURAL_ROUTE_LAYER_DISTRICTS.has(d)))];
}
function routeAllowedDistricts(spec){
  const src=Array.isArray(spec?.districts)&&spec.districts.length?spec.districts:routeDongScope(spec?.type,spec?.vehicle,spec?.day);
  return [...new Set(src.map(canonicalDistrict).filter(Boolean))];
}
function routeScopeSignature(spec){return routeAllowedDistricts(spec).slice().sort().join('|');}""",
"separate rural scope")

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
"scope cache key")

for old in ["routeDongScope(spec.type,spec.vehicle,spec.day)"]:
    s=s.replace(old,"routeAllowedDistricts(spec)")

once(
"""function existingDongRouteOverlay(spec){
  return (dongRouteOverlays[spec.type]||[]).find(x=>x.vehicle===spec.vehicle&&x.day===spec.day) || null;
}""",
"""function existingDongRouteOverlay(spec){
  const scope=routeScopeSignature(spec);
  return (dongRouteOverlays[spec.type]||[]).find(x=>x.vehicle===spec.vehicle&&x.day===spec.day&&routeScopeSignature(x)===scope)||null;
}""",
"overlay scope identity")

once(
"  const buildKey=`${spec.type}|${spec.vehicle}|${spec.day}`;",
"  const buildKey=`${spec.type}|${spec.vehicle}|${spec.day}|${routeScopeSignature(spec)}`;",
"build key")

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
      const base=routeDongScope(type,route.vehicle,routeDay);
      if(base.length)out.push({...common,districts:[...base],scopeKind:'base'});
      const rural=routeRuralScope(type,route.vehicle,routeDay);
      if(rural.length)out.push({...common,districts:rural,scopeKind:'rural'});
    }
  }
  return out;
}""",
"selection rural specs")

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
  const push=s=>{const k=`${s.type}|${s.vehicle}|${s.day}|${routeScopeSignature(s)}`;if(!seen.has(k)){seen.add(k);out.push(s)}};
  for(const type of ['general','recycle']){
    for(const route of routeCatalog(type)){
      for(const [day,raw] of Object.entries(route.days||{})){
        const common={type,vehicle:route.vehicle,provider:route.provider||'',plate:route.plate||route.vehicle,housing:route.housing||'single',zoneEligible:route.zoneEligible!==false,day,raw};
        const base=(route.districts?.length?[...route.districts]:routeDongScope(type,route.vehicle,day)).map(canonicalDistrict);
        if(base.length)push({...common,districts:base,scopeKind:'base'});
        const rural=routeRuralScope(type,route.vehicle,day);
        if(rural.length)push({...common,districts:rural,scopeKind:'rural'});
      }
    }
  }
  return out;
}""",
"all specs")

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
    const groups=await serviceRouteGroups(type,region.district,region.riName||'');
    const usable=groups.filter(g=>g.items.length);
    if(!usable.length)return false;
    await buildGridServiceZonesForRegion(type,region,usable);
    return true;
  }
  if(RURAL_INFERRED_ROUTE_DISTRICTS.has(region.district)){
    wholeFeatureZone(type,region.feature,{...meta,noSchedule:true,groupOutline:true,days:[]});
    await buildRuralRouteBufferZones(type,region);
    return true;
  }
  wholeFeatureZone(type,region.feature,meta);
  return true;
}""",
"ochang estimated area")

once(
"""    if(RURAL_INFERRED_ROUTE_DISTRICTS.has(district)){
      const near=await nearestRouteMatchesForAddress(type,{...ctx,district,legalEmd:district});
      if(seq!==nearbyScheduleRequestSeq)return;
      if(near?.length)renderNearbyRouteSchedule(type,near,ctx);
      else if(!renderRestoredRuralRiSchedule(type,ctx))renderNoNearbyRouteSchedule(type,district);
      continue;
    }""",
"""    if(district==='오창읍'){
      const near=await nearestRouteMatchesForAddress(type,{...ctx,district,legalEmd:district});
      if(seq!==nearbyScheduleRequestSeq)return;
      if(near?.length){renderNearbyRouteSchedule(type,near,ctx);continue}
      const match=await ensureServiceZoneMatch(type,{...ctx,district,legalEmd:district});
      if(seq!==nearbyScheduleRequestSeq)return;
      if(match)renderServiceZoneSchedule(type,{...match,estimated:true,zoneStatus:'estimated'},ctx);
      else renderNoNearbyRouteSchedule(type,district);
      continue;
    }
    if(RURAL_INFERRED_ROUTE_DISTRICTS.has(district)){
      const near=await nearestRouteMatchesForAddress(type,{...ctx,district,legalEmd:district});
      if(seq!==nearbyScheduleRequestSeq)return;
      if(near?.length)renderNearbyRouteSchedule(type,near,ctx);
      else if(!renderRestoredRuralRiSchedule(type,ctx))renderNoNearbyRouteSchedule(type,district);
      continue;
    }""",
"ochang schedule")

p.write_text(s,encoding="utf-8")
