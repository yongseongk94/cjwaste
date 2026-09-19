from pathlib import Path
p=Path('index.html')
s=p.read_text(encoding='utf-8')
s=s.replace("const SERVICE_ZONE_CACHE_VERSION=`zone-v76-layer-visibility-refresh|${DONG_ROUTE_CACHE_VERSION}`;", "const SERVICE_ZONE_CACHE_VERSION=`zone-v78-rural-district-estimated-regions|${DONG_ROUTE_CACHE_VERSION}`;",1)
s=s.replace("      if(!RI_LAYER_DISTRICTS.has(district))serviceZoneRegions.push({district,riName:'',riCode:'',feature:f});", "      // 생활·재활용은 읍·면도 동지역처럼 전체 읍·면 경계에서 노선 기준 추정권역을 생성합니다.\n      serviceZoneRegions.push({district,riName:'',riCode:'',feature:f});",1)
s=s.replace("      serviceZoneRegions.push({district,riName,riCode,feature:f});", "      // 리 경계는 음식물/주소 판정용으로만 사용하며 생활·재활용 추정권역 생성 단위에는 넣지 않습니다.",1)
start=s.index("      if(RI_LAYER_DISTRICTS.has(region.district)){",s.index("async function buildServiceZones(type)"))
end=s.index("      done++;",start)
block="""      // 내수·오창·북이도 동지역과 동일하게 읍·면 전체 경계 안에서 차량×요일 근거노선으로 추정권역을 분할합니다.
      const groups=await serviceRouteGroups(type,region.district,'');
      const usable=groups.filter(g=>g.items.length);
      if(!usable.length){
        // 근거노선 좌표가 없으면 읍·면·동 전체를 임의 권역으로 채우지 않습니다.
      }else{
        await buildGridServiceZonesForRegion(type,region,usable);
      }
"""
s=s[:start]+block+s[end:]
p.write_text(s,encoding='utf-8')
print('RURAL_DISTRICT_ESTIMATED_ZONE_PATCH_OK')
