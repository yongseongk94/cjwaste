from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
orig=s

# 1) bump automatic-zone cache version so old boundary polygons are not reused
old="const SERVICE_ZONE_CACHE_VERSION=`zone-v67-rural30-noapart|${DONG_ROUTE_CACHE_VERSION}`;"
new="const SERVICE_ZONE_CACHE_VERSION=`zone-v68-boundary-majority|${DONG_ROUTE_CACHE_VERSION}`;"
if old not in s:
    raise SystemExit('SERVICE_ZONE_CACHE_VERSION marker not found')
s=s.replace(old,new,1)

# 2) persist estimated metadata in bundled export and IndexedDB cache
old="vehicles:[...(z.vehicles||[])],plate:z.plate||'',days:[...(z.days||[])],groupKey:z.groupKey||'',ambiguous:!!z.ambiguous,\n      automatic:true,sourceOnly:!!z.sourceOnly,riGrouped:!!z.riGrouped,contractLayer:!!z.contractLayer,routeBuffer:!!z.routeBuffer,noSchedule:!!z.noSchedule,groupOutline:!!z.groupOutline"
new="vehicles:[...(z.vehicles||[])],plate:z.plate||'',days:[...(z.days||[])],groupKey:z.groupKey||'',ambiguous:!!z.ambiguous,estimated:!!z.estimated,neighborRatio:Number.isFinite(+z.neighborRatio)?+z.neighborRatio:0,neighborSupport:+z.neighborSupport||0,neighborTotal:+z.neighborTotal||0,\n      automatic:true,sourceOnly:!!z.sourceOnly,riGrouped:!!z.riGrouped,contractLayer:!!z.contractLayer,routeBuffer:!!z.routeBuffer,noSchedule:!!z.noSchedule,groupOutline:!!z.groupOutline"
if old not in s:
    raise SystemExit('bundled zone export fields marker not found')
s=s.replace(old,new,1)

old="vehicles:[...(z.vehicles||[])],plate:z.plate||'',days:[...(z.days||[])],groupKey:z.groupKey||'',ambiguous:!!z.ambiguous,\n        automatic:true,sourceOnly:!!z.sourceOnly,riGrouped:!!z.riGrouped,contractLayer:!!z.contractLayer,routeBuffer:!!z.routeBuffer,noSchedule:!!z.noSchedule,groupOutline:!!z.groupOutline"
new="vehicles:[...(z.vehicles||[])],plate:z.plate||'',days:[...(z.days||[])],groupKey:z.groupKey||'',ambiguous:!!z.ambiguous,estimated:!!z.estimated,neighborRatio:Number.isFinite(+z.neighborRatio)?+z.neighborRatio:0,neighborSupport:+z.neighborSupport||0,neighborTotal:+z.neighborTotal||0,\n        automatic:true,sourceOnly:!!z.sourceOnly,riGrouped:!!z.riGrouped,contractLayer:!!z.contractLayer,routeBuffer:!!z.routeBuffer,noSchedule:!!z.noSchedule,groupOutline:!!z.groupOutline"
if old not in s:
    raise SystemExit('IndexedDB zone fields marker not found')
s=s.replace(old,new,1)

# 3) prefer confirmed polygon over estimated/legacy ambiguous on boundary overlap, and return estimated state
old="hits.sort((a,b)=>(a.ambiguous?1:0)-(b.ambiguous?1:0));\n  const z=hits[0];\n  return {vehicle:z.vehicle,vehicles:[...(z.vehicles||[])],provider:z.provider||routeCompany(z.vehicle),plate:z.plate||'',days:[...(z.days||[])],distanceKm:Infinity,matchBasis:'displayed-zone',zoneStatus:z.ambiguous?'boundary':'inferred',matchedRoads:[],district,riName,riGrouped:!!z.riGrouped,contractLayer:!!z.contractLayer,routeBuffer:!!z.routeBuffer,noSchedule:!!z.noSchedule,groupOutline:!!z.groupOutline};"
new="hits.sort((a,b)=>(a.ambiguous?2:(a.estimated?1:0))-(b.ambiguous?2:(b.estimated?1:0)));\n  const z=hits[0];\n  return {vehicle:z.vehicle,vehicles:[...(z.vehicles||[])],provider:z.provider||routeCompany(z.vehicle),plate:z.plate||'',days:[...(z.days||[])],distanceKm:Infinity,matchBasis:'displayed-zone',zoneStatus:z.estimated?'estimated':(z.ambiguous?'boundary':'inferred'),estimated:!!z.estimated,neighborRatio:Number.isFinite(+z.neighborRatio)?+z.neighborRatio:0,neighborSupport:+z.neighborSupport||0,neighborTotal:+z.neighborTotal||0,matchedRoads:[],district,riName,riGrouped:!!z.riGrouped,contractLayer:!!z.contractLayer,routeBuffer:!!z.routeBuffer,noSchedule:!!z.noSchedule,groupOutline:!!z.groupOutline};"
if old not in s:
    raise SystemExit('serviceZoneOverlayMatch marker not found')
s=s.replace(old,new,1)

# 4) map tooltip/click distinguishes estimated boundary assignment
old="const detail=meta.ambiguous?'자동 권역 경계부 · 담당자 확인 권장':`${serviceZoneLabel(zone)}${contract?' · 제일환경 대행업체 구간':(meta.riGrouped?' · 리 단위 통합권역':(meta.manual?' · 관리자 수동권역':' · 자동 추정권역'))}`;\n    const basis=meta.manual?'관리자 직접 지정':(contract?'오창산업단지 대행업체 구간 · 리 단위 표시':(meta.riGrouped?'읍·면 법정리 1개 = 수거권역 1개':'원본 수거노선 최근접 분할'));"
new="const ratioText=meta.estimated&&Number.isFinite(+meta.neighborRatio)&&+meta.neighborRatio>0?` · 인접권역 ${Math.round(+meta.neighborRatio*100)}% 우세`:'';\n    const detail=meta.estimated?`${serviceZoneLabel(zone)} · 자동권역 경계부 (추정)${ratioText}`:(meta.ambiguous?'자동 권역 경계부 · 담당자 확인 권장':`${serviceZoneLabel(zone)}${contract?' · 제일환경 대행업체 구간':(meta.riGrouped?' · 리 단위 통합권역':(meta.manual?' · 관리자 수동권역':' · 자동 추정권역'))}`);\n    const basis=meta.manual?'관리자 직접 지정':(meta.estimated?'인접 자동권역 비율이 더 높은 수거노선 일정으로 편입':(contract?'오창산업단지 대행업체 구간 · 리 단위 표시':(meta.riGrouped?'읍·면 법정리 1개 = 수거권역 1개':'원본 수거노선 최근접 분할')));"
if old not in s:
    raise SystemExit('zone tooltip marker not found')
s=s.replace(old,new,1)

old="updateMapBadge(`${meta.district||''}${meta.riName?' '+meta.riName:''} · ${serviceZoneLabel(zone)} · ${contract?'제일환경 대행업체 구간':(meta.riGrouped?'리 단위 수거권역':(meta.manual?'관리자 수동권역':'수거노선 근거 자동추정권역'))}${meta.ambiguous?' · 경계부 확인 필요':''}`);"
new="updateMapBadge(`${meta.district||''}${meta.riName?' '+meta.riName:''} · ${serviceZoneLabel(zone)} · ${contract?'제일환경 대행업체 구간':(meta.riGrouped?'리 단위 수거권역':(meta.manual?'관리자 수동권역':'수거노선 근거 자동추정권역'))}${meta.estimated?' · (추정)':(meta.ambiguous?' · 경계부 확인 필요':'')}`);"
if old not in s:
    raise SystemExit('zone click badge marker not found')
s=s.replace(old,new,1)

old="renderServiceZoneSchedule(type,{vehicle:zone.vehicle,vehicles:zone.vehicles,provider:zone.provider,plate:zone.plate,days:zone.days,riGrouped:!!zone.riGrouped,contractLayer:!!zone.contractLayer,zoneStatus:meta.manual?'manual':(meta.ambiguous?'boundary':'inferred'),distanceKm:Infinity},{district:meta.district||'',legalEmd:meta.district||'',legalRi:meta.riName||''},{fromMap:true});"
new="renderServiceZoneSchedule(type,{vehicle:zone.vehicle,vehicles:zone.vehicles,provider:zone.provider,plate:zone.plate,days:zone.days,riGrouped:!!zone.riGrouped,contractLayer:!!zone.contractLayer,zoneStatus:meta.manual?'manual':(meta.estimated?'estimated':(meta.ambiguous?'boundary':'inferred')),estimated:!!meta.estimated,neighborRatio:Number.isFinite(+meta.neighborRatio)?+meta.neighborRatio:0,neighborSupport:+meta.neighborSupport||0,neighborTotal:+meta.neighborTotal||0,distanceKm:Infinity},{district:meta.district||'',legalEmd:meta.district||'',legalRi:meta.riName||''},{fromMap:true});"
if old not in s:
    raise SystemExit('zone click render marker not found')
s=s.replace(old,new,1)

# 5) estimated cells must not merge into confirmed cells even when same route group
old="const sig=`${c.key}|${c.ambiguous?'1':'0'}`;"
new="const sig=`${c.key}|${c.estimated?'E':(c.ambiguous?'A':'C')}`;"
if old not in s:
    raise SystemExit('mergedRowRuns marker not found')
s=s.replace(old,new,1)

# 6) replace grid builder: classify first, then assign ambiguous cells to the locally dominant neighboring route group
start=s.find('async function buildGridServiceZonesForRegion(type,region,groups){')
end=s.find('\nfunction isContractRegion(region){',start)
if start<0 or end<0:
    raise SystemExit('buildGridServiceZonesForRegion block not found')
new_block=r'''async function buildGridServiceZonesForRegion(type,region,groups){
  const b=featureBounds(region.feature);if(!b||!groups.length)return;
  const rural=RI_LAYER_DISTRICTS.has(region.district);
  if(groups.length===1){
    wholeFeatureZone(type,region.feature,{district:region.district,riName:region.riName||'',vehicle:groups[0].vehicle,provider:groups[0].provider||routeCompany(groups[0].vehicle),days:groups[0].days,groupKey:groups[0].key,automatic:true,rural});
    return;
  }
  // 읍·면은 법정리/노선통로 구조를 유지하고, 이 격자 분할은 동지역 자동권역에만 사용합니다.
  const latStep=.00175,lngStep=.00205;
  const ny=Math.max(1,Math.ceil((b.maxLat-b.minLat)/latStep));
  const nx=Math.max(1,Math.ceil((b.maxLng-b.minLng)/lngStep));
  const grid=Array.from({length:ny},()=>Array(nx).fill(null));
  const groupByKey=new Map(groups.map(g=>[g.key,g]));

  // 1차: 기존 최근접 수거노선 기준으로 모든 셀을 분류하고 경계부만 표시해 둡니다.
  for(let iy=0;iy<ny;iy++){
    const lat0=b.minLat+iy*latStep,lat1=Math.min(b.maxLat,lat0+latStep),lat=(lat0+lat1)/2;
    for(let ix=0;ix<nx;ix++){
      const lng0=b.minLng+ix*lngStep,lng1=Math.min(b.maxLng,lng0+lngStep),lng=(lng0+lng1)/2;
      if(!pointInGeoFeature([lng,lat],region.feature))continue;
      const cls=classifyServiceGroups(groups,lat,lng);if(!cls)continue;
      grid[iy][ix]={ix,iy,key:cls.group.key,ambiguous:cls.ambiguous,estimated:false,group:cls.group,lng0,lng1,lat0,lat1};
    }
    if(iy%8===0)await sleepMs(0);
  }

  function dominantNeighborForBoundary(iy,ix,cell){
    // 가까운 확정권역부터 최대 3칸 반경까지 넓혀 보며, 셀 개수 비율이 높은 수거노선을 선택합니다.
    // 동률이면 반경을 넓히고, 끝까지 동률이면 기존 최근접 분류를 보조기준으로 유지합니다.
    for(const radius of [1,2,3]){
      const counts=new Map();let total=0;
      for(let dy=-radius;dy<=radius;dy++)for(let dx=-radius;dx<=radius;dx++){
        if(!dx&&!dy)continue;
        if(Math.max(Math.abs(dx),Math.abs(dy))!==radius)continue;
        const n=grid[iy+dy]?.[ix+dx];
        if(!n||n.ambiguous)continue;
        counts.set(n.key,(counts.get(n.key)||0)+1);total++;
      }
      if(!counts.size)continue;
      const ranked=[...counts.entries()].sort((a,b)=>b[1]-a[1]||(a[0]===cell.key?-1:(b[0]===cell.key?1:String(a[0]).localeCompare(String(b[0]),'ko'))));
      const top=ranked[0],second=ranked[1];
      if(!second||top[1]>second[1]){
        return {key:top[0],support:top[1],total,ratio:top[1]/Math.max(1,total)};
      }
    }
    // 확정 이웃이 매우 적거나 끝까지 동률이면, 주변 모든 원분류의 비율을 한 번 더 비교합니다.
    const counts=new Map();let total=0;
    for(let dy=-3;dy<=3;dy++)for(let dx=-3;dx<=3;dx++){
      if(!dx&&!dy)continue;
      const n=grid[iy+dy]?.[ix+dx];if(!n)continue;
      counts.set(n.key,(counts.get(n.key)||0)+1);total++;
    }
    if(counts.size){
      const ranked=[...counts.entries()].sort((a,b)=>b[1]-a[1]||(a[0]===cell.key?-1:(b[0]===cell.key?1:String(a[0]).localeCompare(String(b[0]),'ko'))));
      const top=ranked[0];return {key:top[0],support:top[1],total,ratio:top[1]/Math.max(1,total)};
    }
    return {key:cell.key,support:0,total:0,ratio:0};
  }

  // 2차: 경계부 셀을 주변 확정 자동권역의 점유비율이 높은 쪽 일정에 편입합니다.
  for(let iy=0;iy<ny;iy++)for(let ix=0;ix<nx;ix++){
    const cell=grid[iy][ix];if(!cell?.ambiguous)continue;
    const choice=dominantNeighborForBoundary(iy,ix,cell);
    const chosen=groupByKey.get(choice.key)||cell.group;
    cell.key=chosen.key;cell.group=chosen;cell.ambiguous=false;cell.estimated=true;
    cell.neighborRatio=choice.ratio;cell.neighborSupport=choice.support;cell.neighborTotal=choice.total;
  }

  // 3차: 확정셀과 추정셀을 따로 병합하여, 추정 표기가 확정권역에 섞여 사라지지 않게 합니다.
  for(let iy=0;iy<ny;iy++){
    const cells=grid[iy].filter(Boolean);
    for(const run of mergedRowRuns(cells)){
      const left=b.minLng+run.x0*lngStep,right=Math.min(b.maxLng,b.minLng+(run.x1+1)*lngStep);
      addServiceZonePolygon(type,[{lat:run.lat0,lng:left},{lat:run.lat0,lng:right},{lat:run.lat1,lng:right},{lat:run.lat1,lng:left}],{
        district:region.district,riName:region.riName||'',vehicle:run.group.vehicle,provider:run.group.provider||routeCompany(run.group.vehicle),days:run.group.days,groupKey:run.group.key,
        ambiguous:false,estimated:!!run.estimated,neighborRatio:+run.neighborRatio||0,neighborSupport:+run.neighborSupport||0,neighborTotal:+run.neighborTotal||0,automatic:true,rural
      });
    }
    if(iy%8===0)await sleepMs(0);
  }
}'''
s=s[:start]+new_block+s[end:]

# 7) render estimated schedule explicitly as (추정)
start=s.find('function renderServiceZoneSchedule(type,match,ctx,options={}){')
end=s.find('\nfunction loadManualZones(){',start)
if start<0 or end<0:
    raise SystemExit('renderServiceZoneSchedule block not found')
old_block=s[start:end]
new_block=r'''function renderServiceZoneSchedule(type,match,ctx,options={}){
  if(!match)return;
  const company=match.provider||routeCompany(match.vehicle);
  const vehicles=(match.vehicles||[]).length?match.vehicles:[match.vehicle].filter(Boolean);
  const plate=match.plate||((vehicles.length===1)?routePlate(vehicles[0]):'');
  if(!options.fromMap)selectedVehicle[type]=company||match.vehicle||'전체';
  const days=DAYS.filter(d=>(match.days||[]).includes(d));const badge=document.getElementById(type+'Badge');
  const estimated=match.zoneStatus==='estimated'||!!match.estimated;
  const estimateMark=estimated?' (추정)':'';
  if(match.contractLayer)badge.textContent=`오창산업단지 대행${estimateMark} · ${days.join('·')}`;
  else if(company)badge.textContent=`대행권역${estimateMark} · ${days.join('·')}`;
  else if(match.riGrouped)badge.textContent=`리 단위${estimateMark} · ${days.join('·')}`;
  else if(match.zoneStatus==='manual')badge.textContent=`관리자권역 · ${days.join('·')}`;
  else if(match.zoneStatus==='boundary')badge.textContent=`권역경계 · ${days.join('·')}`;
  else badge.textContent=`수거권역${estimateMark} · ${days.join('·')}`;
  renderDays(type+'Days',days);
  const ratioPct=estimated&&Number.isFinite(+match.neighborRatio)&&+match.neighborRatio>0?Math.round(+match.neighborRatio*100):0;
  const status=match.zoneStatus==='manual'?'관리자가 직접 지정한 수거권역':(estimated?`자동 수거권역 경계부 — 인접권역 비율이 높은 일정으로 편입 (추정)${ratioPct?` · 우세비율 약 ${ratioPct}%`:''}`:(match.routeBuffer?'법정리 안 수거노선 30m 권역':(match.riGrouped?'법정리 전체를 하나로 묶은 수거권역':(match.zoneStatus==='boundary'?'자동 수거권역 경계부 — 담당자 확인 권장':'화면에 표시된 ① 수거권역 내부'))));
  const place=[ctx?.legalEmd||ctx?.district,ctx?.legalRi].filter(Boolean).join(' ');const apartmentNotice=type==='recycle'?'<br><br><strong>공동주택 안내:</strong> 의무관리대상 공동주택은 재활용품 수거에 대해 자체 위탁계약을 체결하여 처리합니다.':'';
  const phone=company?(CONTRACT_OPERATOR_INFO[company]?.phone||''):'';
  const vehicleText=vehicles.length>1?vehicles.map(routeDisplayLabel).join(' / '):(vehicles.length?routeDisplayLabel(vehicles[0]):'담당 확인');
  const body=company
    ? `<strong>수거방식:</strong> 대행수거<br><strong>수거업체:</strong> ${escapeHtml(company)}${phone?' · '+phone:''}${plate?`<br><strong>차량:</strong> ${escapeHtml(plate)}`:''}<br><strong>수거일${estimateMark}:</strong> ${days.join(' · ')||'요일 확인 필요'}`
    : `<strong>수거방식:</strong> 청원구 직영<br><strong>담당:</strong> ${escapeHtml(vehicleText)}<br><strong>수거일${estimateMark}:</strong> ${days.join(' · ')||'요일 확인 필요'}`;
  const basis=estimated
    ? `자동권역 경계부는 주변 확정 자동권역을 최대 3칸 반경까지 비교해 같은 수거노선이 차지하는 비율이 더 높은 쪽 일정으로 편입했습니다${ratioPct?`(우세비율 약 ${ratioPct}%)`:''}.`
    : (match.contractLayer?'오창산업단지 대행업체 구간을 별도 색상으로 구분하고, 최신 제일환경 원본노선의 요일을 리 단위로 묶었습니다.':(match.routeBuffer?'내수·북이는 리 단위 구분을 유지하되 실제 일정은 표시 수거노선 30m 이내에서만 인정합니다.':(match.riGrouped?'오창읍은 법정리 1개를 ① 수거권역 1개로 표시합니다.':`${company?'대행업체 원본 차량×요일 노선':'직영 원본 차량×요일 노선'}을 기준으로 만든 ① 수거권역과 주소를 매칭했습니다.`)));
  document.getElementById(type+'Detail').innerHTML=`<div class="${(match.zoneStatus==='boundary'||estimated)?'pending':'verified'}">${place?`<strong>판정지역:</strong> ${escapeHtml(place)}<br>`:''}${body}${company&&type==='general'?contractorIncombustibleSummary(ctx):''}<br><span style="color:#6b7280">※ ${basis} 현재 판정: ${status}.</span>${apartmentNotice}</div>`;
}'''
s=s[:start]+new_block+s[end:]

if s==orig:
    raise SystemExit('no changes made')

# Required markers
required=[
    'zone-v68-boundary-majority',
    'function dominantNeighborForBoundary',
    "cell.estimated=true",
    "zoneStatus:z.estimated?'estimated'",
    "수거일${estimateMark}",
    '인접권역 비율이 높은 일정으로 편입 (추정)',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'missing marker: {marker}')

p.write_text(s,encoding='utf-8')
print('boundary majority patch applied',len(orig),'->',len(s))
