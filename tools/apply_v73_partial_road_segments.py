from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')
orig=s

s,n=re.subn(r"const DONG_ROUTE_CACHE_VERSION='v72-road-retry-no-straight';",
            "const DONG_ROUTE_CACHE_VERSION='v73-partial-road-segments';",s,count=1)
if n!=1: raise SystemExit(f'route cache v72 marker not found: {n}')

s,n=re.subn(r"const SERVICE_ZONE_CACHE_VERSION=`zone-v72-road-retry-no-straight\|\$\{DONG_ROUTE_CACHE_VERSION\}`;",
            "const SERVICE_ZONE_CACHE_VERSION=`zone-v73-partial-road-segments|${DONG_ROUTE_CACHE_VERSION}`;",s,count=1)
if n!=1: raise SystemExit(f'zone cache v72 marker not found: {n}')

start=s.find('async function fetchRoadFollowingPath(points){')
end=s.find('\n\nfunction pointInsideRouteDistricts',start)
if start<0 or end<0: raise SystemExit('fetchRoadFollowingPath block not found')

new=r'''async function fetchRoadFollowingPath(points){
  if(!routeProxyConfigured()||!Array.isArray(points)||points.length<2)return null;
  const clean=[];
  for(const p of points){
    const q={lng:+p.lng,lat:+p.lat,term:p.term||'',name:p.name||''};
    if(!Number.isFinite(q.lng)||!Number.isFinite(q.lat))continue;
    const prev=clean[clean.length-1];
    if(prev&&Math.abs(prev.lng-q.lng)<1e-7&&Math.abs(prev.lat-q.lat)<1e-7)continue;
    clean.push(q);
  }
  if(clean.length<2)return null;

  window.__CJWASTE_ROUTE_PROXY_FAILED_LEGS=window.__CJWASTE_ROUTE_PROXY_FAILED_LEGS||[];
  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));

  async function requestOnce(batch){
    const payload={
      points:batch.map(p=>({x:+p.lng,y:+p.lat,name:String(p.term||p.name||'').slice(0,80)})),
      priority:'RECOMMEND'
    };
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),25000);
    try{
      const res=await fetch(ROUTE_PROXY_URL,{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal
      });
      const raw=await res.text();
      let data={};try{data=raw?JSON.parse(raw):{}}catch(e){data={}}
      if(!res.ok)throw new Error(`route proxy ${res.status}${raw?' '+raw.slice(0,300):''}`);
      const path=(data?.path||[]).map(p=>({lng:+p[0],lat:+p[1]})).filter(p=>Number.isFinite(p.lng)&&Number.isFinite(p.lat));
      if(path.length<2)throw new Error('empty road path');
      return {path,distance:+data.distance||0,duration:+data.duration||0,chunks:+data.chunks||1};
    }finally{clearTimeout(timer)}
  }

  async function requestWithRetry(batch){
    let lastErr=null;
    for(let attempt=0;attempt<3;attempt++){
      try{return await requestOnce(batch)}catch(err){
        lastErr=err;
        if(attempt<2)await sleep(attempt===0?250:700);
      }
    }
    throw lastErr||new Error('route request failed');
  }

  async function requestPartial(batch,depth=0){
    try{
      const ok=await requestWithRetry(batch);
      return {segments:[ok.path],failedLegs:[],distance:+ok.distance||0,duration:+ok.duration||0,chunks:+ok.chunks||1};
    }catch(err){
      if(batch.length<=2||depth>=8){
        const a=batch[0],b=batch[batch.length-1];
        const failed={
          from:{lat:+a.lat,lng:+a.lng,name:a.name||'',term:a.term||''},
          to:{lat:+b.lat,lng:+b.lng,name:b.name||'',term:b.term||''},
          message:String(err?.message||err)
        };
        window.__CJWASTE_ROUTE_PROXY_FAILED_LEGS.push(failed);
        console.warn('도로망 미해결 구간은 확정노선에서 제외합니다.',JSON.stringify(failed));
        return {segments:[],failedLegs:[failed],distance:0,duration:0,chunks:0};
      }
      const mid=Math.floor((batch.length-1)/2);
      const left=await requestPartial(batch.slice(0,mid+1),depth+1);
      const right=await requestPartial(batch.slice(mid),depth+1);
      return {
        segments:[...(left.segments||[]),...(right.segments||[])],
        failedLegs:[...(left.failedLegs||[]),...(right.failedLegs||[])],
        distance:(+left.distance||0)+(+right.distance||0),duration:(+left.duration||0)+(+right.duration||0),
        chunks:(+left.chunks||0)+(+right.chunks||0)
      };
    }
  }

  let segments=[],failedLegs=[],distance=0,duration=0,chunks=0;
  const MAX_POINTS=18;
  for(let start=0;start<clean.length-1;start+=MAX_POINTS-1){
    const batch=clean.slice(start,Math.min(start+MAX_POINTS,clean.length));
    if(batch.length<2)break;
    const part=await requestPartial(batch);
    segments.push(...(part.segments||[]));failedLegs.push(...(part.failedLegs||[]));
    distance+=+part.distance||0;duration+=+part.duration||0;chunks+=+part.chunks||0;
  }
  if(!segments.length&&!failedLegs.length)return null;
  return {
    segments,distance,duration,chunks,
    failedLegs,complete:failedLegs.length===0,
    // 단일 연속 도로망일 때만 path를 제공합니다. 여러 구간을 한 선으로 합쳐 빈 틈을 직선으로 잇지 않습니다.
    path:segments.length===1?segments[0]:[]
  };
}'''
s=s[:start]+new+s[end:]

# Rural movement: preserve each successful road path separately; never join across a failed leg.
old="""    const roadResult=await fetchRoadFollowingPath(anchors);
    if(!roadResult?.path?.length)continue;
    const local=clipRoutePathToDistricts(roadResult.path,[district]);
    for(const seg of local){
      if(seg.length<2)continue;
      segments.push(seg.map(p=>({lat:+p.lat,lng:+p.lng})));
      inferredMovementCount++;
    }"""
new2="""    const roadResult=await fetchRoadFollowingPath(anchors);
    for(const roadPath of (roadResult?.segments||[])){
      const local=clipRoutePathToDistricts(roadPath,[district]);
      for(const seg of local){
        if(seg.length<2)continue;
        segments.push(seg.map(p=>({lat:+p.lat,lng:+p.lng})));
        inferredMovementCount++;
      }
    }"""
if old not in s: raise SystemExit('rural roadResult caller not found')
s=s.replace(old,new2,1)

# Entry route: remove the exact straight fallback `roadResult?.path||anchors`.
old="""      if(anchors.length>=2){
        roadRequestedCount++;
        const roadResult=await fetchRoadFollowingPath(anchors);
        if(roadResult)roadMatchedCount++;
        const raw=roadResult?.path||anchors;

        // 해당 차량·요일에 배정된 동지역 경계 안에서만 구간을 남깁니다.
        const localSegments=clipRoutePathToDistricts(raw,routeDongScope(spec.type,spec.vehicle,spec.day));
        if(localSegments.length){
          for(const seg of localSegments){
            if(seg.length>=2)segments.push(seg.map(p=>({lat:+p.lat,lng:+p.lng})));
          }
          anchorPointCount+=anchors.length;
          termShown=true;
        }
      }"""
new3="""      if(anchors.length>=2){
        roadRequestedCount++;
        const roadResult=await fetchRoadFollowingPath(anchors);
        let matchedThisTerm=false;
        for(const roadPath of (roadResult?.segments||[])){
          // 해당 차량·요일에 배정된 동지역 경계 안에서만 실제 도로망 구간을 남깁니다.
          const localSegments=clipRoutePathToDistricts(roadPath,routeDongScope(spec.type,spec.vehicle,spec.day));
          if(!localSegments.length)continue;
          for(const seg of localSegments){
            if(seg.length>=2){segments.push(seg.map(p=>({lat:+p.lat,lng:+p.lng})));matchedThisTerm=true}
          }
        }
        if(matchedThisTerm){
          roadMatchedCount++;
          anchorPointCount+=anchors.length;
          termShown=true;
        }
      }"""
if old not in s: raise SystemExit('entry roadResult fallback block not found')
s=s.replace(old,new3,1)

# Explicit user-facing wording: displayed confirmed lines are API-returned road geometry only.
s=s.replace('실제 도로망 적용 ${roadMatchedCount}/${roadRequestedCount}구간',
            '실제 도로망 확인 ${roadMatchedCount}/${roadRequestedCount}항목',1)

# Guardrail against reintroducing the straight fallback.
if 'roadResult?.path||anchors' in s or 'roadResult?.path || anchors' in s:
    raise SystemExit('straight fallback still present')

if s==orig: raise SystemExit('no changes')
p.write_text(s,encoding='utf-8')
print('v73 partial road-segment patch applied')
