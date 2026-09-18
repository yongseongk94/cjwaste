from pathlib import Path

p = Path("index.html")
s = p.read_text(encoding="utf-8")

def rep(old, new, label):
    global s
    c = s.count(old)
    if c != 1:
        raise SystemExit(f"{label}: expected 1 match, found {c}")
    s = s.replace(old, new, 1)

rep(
    "const SERVICE_ZONE_CACHE_VERSION=`zone-v80-rural-route-ready|${DONG_ROUTE_CACHE_VERSION}`;",
    "const SERVICE_ZONE_CACHE_VERSION=`zone-v82-district-grid-unified|${DONG_ROUTE_CACHE_VERSION}`;",
    "zone cache version",
)

rep(
    "      if(!RI_LAYER_DISTRICTS.has(district))serviceZoneRegions.push({district,riName:'',riCode:'',feature:f});",
    """      // v82: 생활·재활용 추정지역은 읍·면·동 모두 행정구역 전체 경계를 동일하게 사용합니다.
      // 오창·내수·북이도 리 단위로 쪼개지 않고 동지역과 같은 차량×요일 노선 기반 분할을 사용합니다.
      serviceZoneRegions.push({district,riName:'',riCode:'',feature:f});""",
    "district service-zone region",
)

rep(
    """      serviceZoneRegions.push({district,riName,riCode,feature:f});

      // 생활·재활용: 법정리별 일정표 + 시설/도로명 실제 주소대조 규칙을 붙여 생성.
      // 오창의 동명이리 화산리는 li_cd로 꽃화산/빛화산을 구분합니다.
      for(const type of ['general','recycle']){
        // 위탁구역은 riScheduleFromSources에서 직영차량과 분리해 위탁업체 일정만 반환합니다.
        const scheduleByDay=riScheduleFromSources(type,district,riName,riCode);
        addRiServiceGeometry(f,district,riName,type,scheduleByDay,riCode);
      }
""",
    """      // v82: 리 경계는 음식물 분류배출 및 주소 세부판정 자료로만 유지합니다.
      // 생활·재활용 지도 레이어에는 리 단위 폴리곤을 만들지 않습니다.
""",
    "remove rural ri service zones",
)

rep(
    """      if(RI_LAYER_DISTRICTS.has(region.district)){
        // v66: 내수·오창·북이는 법정리 경계 자체를 ① 수거권역으로 사용합니다.
        // 같은 리 안을 100m 격자로 다시 쪼개지 않습니다.
        await buildRuralRiServiceZone(type,region);
      }else{
        const groups=await serviceRouteGroups(type,region.district,region.riName||'');
        const usable=groups.filter(g=>g.items.length);
        if(!usable.length){
          // 근거노선 좌표가 없으면 동 전체를 임의 수거권역으로 채우지 않습니다.
        }else{
          await buildGridServiceZonesForRegion(type,region,usable);
        }
      }""",
    """      // v82: 읍·면·동을 구분하지 않고 동일한 방식으로 추정지역을 생성합니다.
      // 행정구역 전체에서 차량×요일 수거노선을 기준으로 최근접 분할하고,
      // 실제 표시 수거노선 20m 이내는 확정구간으로 남겨 추정폴리곤에서 제외합니다.
      const groups=await serviceRouteGroups(type,region.district,'');
      const usable=groups.filter(g=>g.items.length);
      if(usable.length)await buildGridServiceZonesForRegion(type,region,usable);""",
    "unify service-zone build",
)

rep(
    """    const bugi=districtFeatures.get('북이면');
    if(bugi)addWholeDistrictExclusion(bugi,'북이면');

    setLayer(activeLayer);""",
    """    const bugi=districtFeatures.get('북이면');
    if(bugi)addWholeDistrictExclusion(bugi,'북이면');

    // v82: 생활·재활용 추정지역은 리 경계를 기다릴 필요가 없습니다.
    // 행정구역 경계가 준비되는 즉시 동지역과 읍·면을 같은 방식으로 계산합니다.
    serviceRegionLoadComplete=true;
    serviceZoneBuilt.general=false;
    serviceZoneBuilt.recycle=false;
    setLayer(activeLayer);
    scheduleDongRoutePreload();""",
    "start service zones after district boundaries",
)

rep(
    """  // 행정동/법정리 경계가 준비된 뒤 모든 차량×요일 노선을 조용히 사전 계산·저장합니다.
  // v63 내장본이 있으면 첫 접속부터 즉시 표시되며, 이 호출은 누락분 점검/재생성용입니다.
  scheduleDongRoutePreload();""",
    """  // v82: 차량×요일 노선 사전계산은 행정구역 경계 직후 이미 시작합니다.
  // 법정리 로딩 완료 시점에는 현재 레이어만 다시 동기화합니다.
  if(activeLayer==='general'||activeLayer==='recycle')setLayer(activeLayer);""",
    "avoid delayed duplicate preload",
)

old_note = "※ 주소가 표시 수거노선 30m 이내로 매칭되면 해당 노선의 더 세부적인 결과를 우선 적용합니다."
if old_note in s:
    s = s.replace(
        old_note,
        "※ 주소가 표시 수거노선 20m 이내로 매칭되면 해당 노선의 결과를 우선 적용하고, 그 밖은 행정구역 단위 추정지역을 사용합니다.",
        1,
    )

required = [
    "zone-v82-district-grid-unified",
    "읍·면·동 모두 행정구역 전체 경계를 동일하게 사용",
    "생활·재활용 지도 레이어에는 리 단위 폴리곤을 만들지 않습니다.",
    "읍·면·동을 구분하지 않고 동일한 방식으로 추정지역을 생성합니다.",
    "생활·재활용 추정지역은 리 경계를 기다릴 필요가 없습니다.",
]
missing = [x for x in required if x not in s]
if missing:
    raise SystemExit(f"validation missing: {missing}")

p.write_text(s, encoding="utf-8")
