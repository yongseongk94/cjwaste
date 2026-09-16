from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')
orig=s

# Cache version: old v70 polygons must never be reused.
s,n=re.subn(r"const SERVICE_ZONE_CACHE_VERSION=`zone-v70-dong-polygons-persist\|\$\{DONG_ROUTE_CACHE_VERSION\}`;",
            "const SERVICE_ZONE_CACHE_VERSION=`zone-v71-confirmed-route-excluded|${DONG_ROUTE_CACHE_VERSION}`;",s,count=1)
if n!=1: raise SystemExit(f'cache version marker not found: {n}')

# UI: service-zone layer is now explicitly inference-only.
s=s.replace('<button class="active" data-structure="zone">① 수거권역</button>',
            '<button class="active" data-structure="zone">① 추정권역</button>',1)
s=s.replace('<div class="admin-help">자동 추정권역이 실제와 다를 때 지도에서 직접 권역을 그립니다. 직접 그린 권역은 주소 판정에서 자동권역보다 우선합니다.</div>',
            '<div class="admin-help">확정 수거노선 밖의 추정권역이 실제와 다를 때 지도에서 직접 권역을 그립니다. 직접 그린 권역은 자동 추정권역보다 우선합니다.</div>',1)

# Add exact-route-only group distance. serviceGroupDistanceKm also considers hidden evidence points,
# which are useful for inference but must NOT define a confirmed route corridor.
needle="function serviceGroupDistanceKm(group,lat,lng){\n  let best=Infinity;for(const item of (group?.items||[]))best=Math.min(best,serviceZoneEvidenceDistanceKm(item,lat,lng));return best;\n}"
insert=needle+"\nfunction serviceGroupRouteDistanceKm(group,lat,lng){\n  let best=Infinity;for(const item of (group?.items||[]))best=Math.min(best,routeItemDistanceKm(item,lat,lng));return best;\n}"
if needle not in s: raise SystemExit('serviceGroupDistanceKm marker not found')
s=s.replace(needle,insert,1)

# Replace the dong grid builder. Every polygon cell is estimated; cells touching a confirmed
# displayed route corridor are excluded from the inference layer.
start=s.find('async function buildGridServiceZonesForRegion(type,region,groups){')
end=s.find('\nfunction isContractRegion(region){',start)
if start<0 or end<0: raise SystemExit('grid builder block not found')
new_block=r'''async function buildGridServiceZonesForRegion(type,region,groups){
  const b=featureBounds(region.feature);if(!b||!groups.length)return;
  const rural=RI_LAYER_DISTRICTS.has(region.district);
  // 동지역 추정권역은 확정 표시노선 주변을 빼고 남은 공간만 채웁니다.
  // 약 70~85m 격자로 샘플링해 확정노선이 지나가는 셀을 추정폴리곤에서 제외합니다.
  const latStep=.00068,lngStep=.00086;
  const ny=Math.max(1,Math.ceil((b.maxLat-b.minLat)/latStep));
  const nx=Math.max(1,Math.ceil((b.maxLng-b.minLng)/lngStep));
  const grid=Array.from({length:ny},()=>Array(nx).fill(null));
  const groupByKey=new Map(groups.map(g=>[g.key,g]));

  function touchesConfirmedRoute(lat0,lat1,lng0,lng1){
    const lat=(lat0+lat1)/2,lng=(lng0+lng1)/2;
    const samples=[
      [lat,lng],[lat0,lng0],[lat0,lng1],[lat1,lng0],[lat1,lng1],
      [lat0,lng],[lat1,lng],[lat,lng0],[lat,lng1]
    ];
    for(const [y,x] of samples){
      for(const g of groups){
        if(serviceGroupRouteDistanceKm(g,y,x)<=MAX_ADDRESS_ROUTE_DISTANCE_KM)return true;
      }
    }
    return false;
  }

  // 1) 확정 수거선 20m 범위를 제외한 빈 공간만 추정 셀로 만듭니다.
  for(let iy=0;iy<ny;iy++){
    const lat0=b.minLat+iy*latStep,lat1=Math.min(b.maxLat,lat0+latStep),lat=(lat0+lat1)/2;
    for(let ix=0;ix<nx;ix++){
      const lng0=b.minLng+ix*lngStep,lng1=Math.min(b.maxLng,lng0+lngStep),lng=(lng0+lng1)/2;
      if(!pointInGeoFeature([lng,lat],region.feature))continue;
      const cls=classifyServiceGroups(groups,lat,lng);if(!cls)continue;
      if(touchesConfirmedRoute(lat0,lat1,lng0,lng1))continue;
      grid[iy][ix]={ix,iy,key:cls.group.key,ambiguous:cls.ambiguous,estimated:true,group:cls.group,lng0,lng1,lat0,lat1};
    }
    if(iy%8===0)await sleepMs(0);
  }

  function dominantNeighborForBoundary(iy,ix,cell){
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
      if(!second||top[1]>second[1])return {key:top[0],support:top[1],total,ratio:top[1]/Math.max(1,total)};
    }
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

  // 2) 추정권역 경계셀은 주변 노선 점유비율이 높은 쪽에 편입하되 계속 (추정)으로 유지합니다.
  for(let iy=0;iy<ny;iy++)for(let ix=0;ix<nx;ix++){
    const cell=grid[iy][ix];if(!cell?.ambiguous)continue;
    const choice=dominantNeighborForBoundary(iy,ix,cell);
    const chosen=groupByKey.get(choice.key)||cell.group;
    cell.key=chosen.key;cell.group=chosen;cell.ambiguous=false;cell.estimated=true;
    cell.neighborRatio=choice.ratio;cell.neighborSupport=choice.support;cell.neighborTotal=choice.total;
  }

  // 3) 같은 추정 일정끼리 큰 블록으로 병합합니다. 배포 내장본에서는 이 블록들을 다시 실제 폴리곤으로 합칩니다.
  const finished=[];let active=new Map();
  for(let iy=0;iy<ny;iy++){
    const runs=mergedRowRuns(grid[iy].filter(Boolean));
    const next=new Map();
    for(const run of runs){
      const id=`${run.sig}|${run.x0}|${run.x1}`;
      const prev=active.get(id);
      if(prev&&prev.iy1===iy-1){
        prev.iy1=iy;prev.lat1=run.lat1;
        prev.neighborSupport+=(+run.neighborSupport||0);
        prev.neighborTotal+=(+run.neighborTotal||0);
        prev.neighborRatio=prev.neighborTotal?prev.neighborSupport/prev.neighborTotal:(+prev.neighborRatio||0);
        next.set(id,prev);
      }else next.set(id,{...run,iy0:iy,iy1:iy});
    }
    for(const [id,rect] of active)if(!next.has(id))finished.push(rect);
    active=next;
  }
  for(const rect of active.values())finished.push(rect);

  for(const rect of finished){
    const left=b.minLng+rect.x0*lngStep,right=Math.min(b.maxLng,b.minLng+(rect.x1+1)*lngStep);
    const bottom=b.minLat+rect.iy0*latStep,top=Math.min(b.maxLat,b.minLat+(rect.iy1+1)*latStep);
    addServiceZonePolygon(type,[{lat:bottom,lng:left},{lat:bottom,lng:right},{lat:top,lng:right},{lat:top,lng:left}],{
      district:region.district,riName:region.riName||'',vehicle:rect.group.vehicle,provider:rect.group.provider||routeCompany(rect.group.vehicle),days:rect.group.days,groupKey:rect.group.key,
      ambiguous:false,estimated:true,neighborRatio:+rect.neighborRatio||0,neighborSupport:+rect.neighborSupport||0,neighborTotal:+rect.neighborTotal||0,automatic:true,rural,gridMerged:true,estimateReason:'outside-confirmed-route'
    });
  }
}'''
s=s[:start]+new_block+s[end:]

# If a dong has no usable geometry, do not paint the whole administrative district as if it were known.
old="""        if(!usable.length){
          if(groups.length===1)wholeFeatureZone(type,region.feature,{district:region.district,riName:region.riName||'',vehicle:groups[0].vehicle,provider:groups[0].provider||routeCompany(groups[0].vehicle),days:groups[0].days,automatic:true,sourceOnly:true,rural:false});
        }else{
          await buildGridServiceZonesForRegion(type,region,usable);
        }"""
new="""        if(!usable.length){
          // 근거노선 좌표가 없으면 동 전체를 임의 수거권역으로 채우지 않습니다.
        }else{
          await buildGridServiceZonesForRegion(type,region,usable);
        }"""
if old not in s: raise SystemExit('buildServiceZones usable marker not found')
s=s.replace(old,new,1)

# Automatic dong polygons are inference only, never a confirmed result.
old="""  const z=hits[0];
  return {vehicle:z.vehicle,vehicles:[...(z.vehicles||[])],provider:z.provider||routeCompany(z.vehicle),plate:z.plate||'',days:[...(z.days||[])],distanceKm:Infinity,matchBasis:'displayed-zone',zoneStatus:z.estimated?'estimated':(z.ambiguous?'boundary':'inferred'),estimated:!!z.estimated,neighborRatio:Number.isFinite(+z.neighborRatio)?+z.neighborRatio:0,neighborSupport:+z.neighborSupport||0,neighborTotal:+z.neighborTotal||0,matchedRoads:[],district,riName,riGrouped:!!z.riGrouped,contractLayer:!!z.contractLayer,routeBuffer:!!z.routeBuffer,noSchedule:!!z.noSchedule,groupOutline:!!z.groupOutline,gridMerged:!!z.gridMerged,polygonized:!!z.polygonized};"""
new="""  const z=hits[0];
  const dongEstimated=DONG_ROUTE_DISTRICTS.has(district)&&!z.manual&&!z.routeBuffer;
  return {vehicle:z.vehicle,vehicles:[...(z.vehicles||[])],provider:z.provider||routeCompany(z.vehicle),plate:z.plate||'',days:[...(z.days||[])],distanceKm:Infinity,matchBasis:'displayed-zone',zoneStatus:(z.estimated||dongEstimated)?'estimated':(z.ambiguous?'boundary':'inferred'),estimated:!!z.estimated||dongEstimated,neighborRatio:Number.isFinite(+z.neighborRatio)?+z.neighborRatio:0,neighborSupport:+z.neighborSupport||0,neighborTotal:+z.neighborTotal||0,matchedRoads:[],district,riName,riGrouped:!!z.riGrouped,contractLayer:!!z.contractLayer,routeBuffer:!!z.routeBuffer,noSchedule:!!z.noSchedule,groupOutline:!!z.groupOutline,gridMerged:!!z.gridMerged,polygonized:!!z.polygonized};"""
if old not in s: raise SystemExit('serviceZoneOverlayMatch return marker not found')
s=s.replace(old,new,1)

# Address priority: exact contractor row -> direct displayed route within threshold -> inferred polygon.
old="""    // 동지역/오창은 화면에 그려지는 ① 수거권역과 동일한 판정구조를 사용합니다.
    const match=await ensureServiceZoneMatch(type,{...ctx,district,legalEmd:district});
    if(seq!==nearbyScheduleRequestSeq)return;
    if(match)renderServiceZoneSchedule(type,match,ctx);
    else renderNoNearbyRouteSchedule(type,district);"""
new="""    if(DONG_ROUTE_DISTRICTS.has(district)){
      // 확실한 표시 수거노선 20m 이내가 최우선입니다. 그 밖의 빈 공간에서만 추정권역을 사용합니다.
      const near=await nearestRouteMatchesForAddress(type,{...ctx,district,legalEmd:district});
      if(seq!==nearbyScheduleRequestSeq)return;
      if(near?.length){renderNearbyRouteSchedule(type,near,ctx);continue}
      const match=await ensureServiceZoneMatch(type,{...ctx,district,legalEmd:district});
      if(seq!==nearbyScheduleRequestSeq)return;
      if(match)renderServiceZoneSchedule(type,{...match,estimated:true,zoneStatus:'estimated'},ctx);
      else renderNoNearbyRouteSchedule(type,district);
      continue;
    }
    // 오창읍은 기존 리 단위/대행 확정규칙을 유지합니다.
    const match=await ensureServiceZoneMatch(type,{...ctx,district,legalEmd:district});
    if(seq!==nearbyScheduleRequestSeq)return;
    if(match)renderServiceZoneSchedule(type,match,ctx);
    else renderNoNearbyRouteSchedule(type,district);"""
if old not in s: raise SystemExit('refreshNearbyRouteSchedules dong block not found')
s=s.replace(old,new,1)

# Correct explanatory text: estimated is not a confirmed automatic boundary.
s=s.replace("const detail=meta.estimated?`${serviceZoneLabel(zone)} · 자동권역 경계부 (추정)${ratioText}`:",
            "const detail=meta.estimated?`${serviceZoneLabel(zone)} · 확정 수거노선 밖 추정권역 (추정)${ratioText}`:",1)
s=s.replace("const basis=meta.manual?'관리자 직접 지정':(meta.estimated?'인접 자동권역 비율이 더 높은 수거노선 일정으로 편입':",
            "const basis=meta.manual?'관리자 직접 지정':(meta.estimated?'확정 표시 수거노선 20m 범위를 제외한 빈 구간을 주변 원본 노선 기준으로 추정':",1)
s=s.replace("const status=match.zoneStatus==='manual'?'관리자가 직접 지정한 수거권역':(estimated?`자동 수거권역 경계부 — 인접권역 비율이 높은 일정으로 편입 (추정)${ratioPct?` · 우세비율 약 ${ratioPct}%`:''}`:",
            "const status=match.zoneStatus==='manual'?'관리자가 직접 지정한 수거권역':(estimated?`확정 수거노선 밖 자동 추정권역 (추정)${ratioPct?` · 경계 우세비율 약 ${ratioPct}%`:''}`:",1)
s=s.replace("? `자동권역 경계부는 주변 확정 자동권역을 최대 3칸 반경까지 비교해 같은 수거노선이 차지하는 비율이 더 높은 쪽 일정으로 편입했습니다${ratioPct?`(우세비율 약 ${ratioPct}%)`:''}.`",
            "? `실제 표시 수거노선 20m 이내의 확정구간은 추정권역에서 제외했습니다. 남은 빈 구간만 주변 원본 수거노선과 경계 점유비율을 이용해 편입한 값입니다${ratioPct?`(경계 우세비율 약 ${ratioPct}%)`:''}.`",1)

# Map help text should no longer imply every polygon is a normal/confirmed service zone.
s=s.replace("주소 수거일정은 화면에 표시되는 ① 수거권역 폴리곤과 동일한 경계를 그대로 사용합니다. 자동권역은 원본 차량·요일별 수거노선을 같은 리/행정동 안에서 최근접 분할한 추정 범위이며,",
            "주소 수거일정은 실제 표시 수거노선 20m 이내를 먼저 확정하고, 그 밖의 주소에서만 ① 추정권역 폴리곤을 사용합니다. 추정권역은 확정 노선 범위를 제외한 빈 공간을 원본 차량·요일별 수거노선 기준으로 나눈 범위이며,",1)

if s==orig: raise SystemExit('no changes made')
p.write_text(s,encoding='utf-8')
print('v71 runtime confirmed-route exclusion patch applied')
