from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')
orig=s

s,n=re.subn(r"const DONG_ROUTE_CACHE_VERSION='[^']+';", "const DONG_ROUTE_CACHE_VERSION='v72-road-retry-no-straight';", s, count=1)
if n!=1: raise SystemExit(f'DONG route cache version not found: {n}')

s,n=re.subn(r"const SERVICE_ZONE_CACHE_VERSION=`zone-v71-confirmed-route-excluded\|\$\{DONG_ROUTE_CACHE_VERSION\}`;",
            "const SERVICE_ZONE_CACHE_VERSION=`zone-v72-road-retry-no-straight|${DONG_ROUTE_CACHE_VERSION}`;", s, count=1)
if n!=1: raise SystemExit(f'service-zone cache version not found: {n}')

start=s.find('async function fetchRoadFollowingPath(points){')
end=s.find('\n\nfunction pointInsideRouteDistricts', start)
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

  window.__CJWASTE_ROUTE_PROXY_FINAL_FAILURES=window.__CJWASTE_ROUTE_PROXY_FINAL_FAILURES||0;
  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  const mergePaths=(a,b)=>{
    if(!a?.length)return b||[];
    if(!b?.length)return a||[];
    const out=[...a],last=out[out.length-1],first=b[0];
    const skip=last&&first&&Math.abs(last.lng-first.lng)<1e-8&&Math.abs(last.lat-first.lat)<1e-8?1:0;
    out.push(...b.slice(skip));return out;
  };

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
      if(!res.ok)throw new Error(`route proxy ${res.status}${raw?' '+raw.slice(0,220):''}`);
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

  async function requestResilient(batch,depth=0){
    try{return await requestWithRetry(batch)}catch(err){
      if(batch.length<=2||depth>=6)throw err;
      const mid=Math.floor((batch.length-1)/2);
      const left=await requestResilient(batch.slice(0,mid+1),depth+1);
      const right=await requestResilient(batch.slice(mid),depth+1);
      return {path:mergePaths(left.path,right.path),distance:(+left.distance||0)+(+right.distance||0),duration:(+left.duration||0)+(+right.duration||0),chunks:(+left.chunks||1)+(+right.chunks||1)};
    }
  }

  try{
    let path=[],distance=0,duration=0,chunks=0;
    const MAX_POINTS=18;
    for(let start=0;start<clean.length-1;start+=MAX_POINTS-1){
      const batch=clean.slice(start,Math.min(start+MAX_POINTS,clean.length));
      if(batch.length<2)break;
      const part=await requestResilient(batch);
      path=mergePaths(path,part.path);distance+=+part.distance||0;duration+=+part.duration||0;chunks+=+part.chunks||1;
    }
    if(path.length<2)throw new Error('no complete road path');
    return {path,distance,duration,chunks:chunks||1};
  }catch(err){
    window.__CJWASTE_ROUTE_PROXY_FINAL_FAILURES++;
    console.warn('도로망 수거노선 최종 실패, 직선 대체 없이 해당 구간을 제외합니다.',err);
    return null;
  }
}'''

s=s[:start]+new+s[end:]

# Update explanatory wording so the UI never claims a straight fallback is a confirmed road route.
s=s.replace('확인지점 직선 연결로 대체합니다.','직선 대체 없이 해당 구간을 제외합니다.')

if s==orig: raise SystemExit('no changes')
p.write_text(s,encoding='utf-8')
print('v72 route reliability patch applied')
