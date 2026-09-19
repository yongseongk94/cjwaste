from pathlib import Path
p=Path('index.html')
s=p.read_text(encoding='utf-8')
old="""async function buildRuralRiServiceZone(type,region){
  const meta=ruralRiZoneMeta(type,region);
  if(!meta)return false;
  if(RURAL_ROUTE_LAYER_DISTRICTS.has(region.district)){
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
}"""
new="""async function buildRuralRiServiceZone(type,region){
  // 오창·내수·북이는 리 일정표가 비어 있어도 실제 차량×요일 근거노선으로 추정권역을 생성합니다.
  if(RURAL_ROUTE_LAYER_DISTRICTS.has(region.district)){
    const groups=await serviceRouteGroups(type,region.district,region.riName||'');
    const usable=groups.filter(g=>g.items.length);
    if(!usable.length)return false;
    await buildGridServiceZonesForRegion(type,region,usable);
    return true;
  }
  const meta=ruralRiZoneMeta(type,region);
  if(!meta)return false;
  if(RURAL_INFERRED_ROUTE_DISTRICTS.has(region.district)){
    wholeFeatureZone(type,region.feature,{...meta,noSchedule:true,groupOutline:true,days:[]});
    await buildRuralRouteBufferZones(type,region);
    return true;
  }
  wholeFeatureZone(type,region.feature,meta);
  return true;
}"""
if old not in s: raise SystemExit('target block not found')
s=s.replace(old,new,1)
s=s.replace('zone-v77-rural-estimated-regions|${DONG_ROUTE_CACHE_VERSION}','zone-v78-rural-estimated-regions-fix|${DONG_ROUTE_CACHE_VERSION}',1)
p.write_text(s,encoding='utf-8')
print('RURAL_ESTIMATED_REGION_FIX_OK')
