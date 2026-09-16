from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')
orig=s

old_version="const SERVICE_ZONE_CACHE_VERSION=`zone-v68-boundary-majority|${DONG_ROUTE_CACHE_VERSION}`;"
new_version="const SERVICE_ZONE_CACHE_VERSION=`zone-v69-merged-grid-blocks|${DONG_ROUTE_CACHE_VERSION}`;"
if old_version not in s:
    raise SystemExit('v68 service-zone cache marker not found')
s=s.replace(old_version,new_version,1)

# Keep the visual-merge flag when exporting/hydrating precomputed zones.
if 'groupOutline:!!z.groupOutline,gridMerged:!!z.gridMerged' not in s:
    n=s.count('groupOutline:!!z.groupOutline')
    if n < 2:
        raise SystemExit(f'expected zone serialization markers, found {n}')
    s=s.replace('groupOutline:!!z.groupOutline','groupOutline:!!z.groupOutline,gridMerged:!!z.gridMerged')

# Horizontal runs now aggregate estimation support so a merged block can show one representative ratio.
start=s.find('function mergedRowRuns(cells){')
end=s.find('\nfunction ',start+1)
if start<0 or end<0:
    raise SystemExit('mergedRowRuns block not found')
merged_fn=r'''function mergedRowRuns(cells){
  const runs=[];let run=null;
  for(const c of cells){
    const sig=`${c.key}|${c.estimated?'E':(c.ambiguous?'A':'C')}`;
    if(!run||run.sig!==sig||c.ix!==run.x1+1){
      if(run)runs.push(run);
      run={...c,sig,x0:c.ix,x1:c.ix,neighborSupport:+c.neighborSupport||0,neighborTotal:+c.neighborTotal||0};
    }else{
      run.x1=c.ix;
      if(run.estimated){
        run.neighborSupport+=(+c.neighborSupport||0);
        run.neighborTotal+=(+c.neighborTotal||0);
        run.neighborRatio=run.neighborTotal?run.neighborSupport/run.neighborTotal:(+run.neighborRatio||0);
      }
    }
  }
  if(run)runs.push(run);return runs;
}'''
s=s[:start]+merged_fn+s[end:]

# Replace the grid builder.  Same route + same certainty is merged horizontally and vertically;
# different confirmed/estimated states remain separate so '(추정)' is never lost.
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
  const latStep=.00175,lngStep=.00205;
  const ny=Math.max(1,Math.ceil((b.maxLat-b.minLat)/latStep));
  const nx=Math.max(1,Math.ceil((b.maxLng-b.minLng)/lngStep));
  const grid=Array.from({length:ny},()=>Array(nx).fill(null));
  const groupByKey=new Map(groups.map(g=>[g.key,g]));

  // 1) Base classification by nearest source route.
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

  // 2) Boundary cells inherit the locally dominant neighboring route but stay marked estimated.
  for(let iy=0;iy<ny;iy++)for(let ix=0;ix<nx;ix++){
    const cell=grid[iy][ix];if(!cell?.ambiguous)continue;
    const choice=dominantNeighborForBoundary(iy,ix,cell);
    const chosen=groupByKey.get(choice.key)||cell.group;
    cell.key=chosen.key;cell.group=chosen;cell.ambiguous=false;cell.estimated=true;
    cell.neighborRatio=choice.ratio;cell.neighborSupport=choice.support;cell.neighborTotal=choice.total;
  }

  // 3) Merge adjacent cells into large display blocks.  First merge each row, then extend
  // identical runs vertically.  Any remaining touching blocks have no internal stroke, so
  // they read visually as one service area rather than a checkerboard of cells.
  const finished=[];let active=new Map();
  for(let iy=0;iy<ny;iy++){
    const runs=mergedRowRuns(grid[iy].filter(Boolean));
    const next=new Map();
    for(const run of runs){
      const id=`${run.sig}|${run.x0}|${run.x1}`;
      const prev=active.get(id);
      if(prev&&prev.iy1===iy-1){
        prev.iy1=iy;prev.lat1=run.lat1;
        if(prev.estimated){
          prev.neighborSupport+=(+run.neighborSupport||0);
          prev.neighborTotal+=(+run.neighborTotal||0);
          prev.neighborRatio=prev.neighborTotal?prev.neighborSupport/prev.neighborTotal:(+prev.neighborRatio||0);
        }
        next.set(id,prev);
      }else{
        next.set(id,{...run,iy0:iy,iy1:iy});
      }
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
      ambiguous:false,estimated:!!rect.estimated,neighborRatio:+rect.neighborRatio||0,neighborSupport:+rect.neighborSupport||0,neighborTotal:+rect.neighborTotal||0,automatic:true,rural,gridMerged:true
    });
  }
}'''
s=s[:start]+new_block+s[end:]

# Hide internal outlines only for these merged automatic grid blocks. Different routes remain
# distinguishable by their fill, while hovering/clicking still works on the polygon itself.
start=s.find('function addServiceZonePolygon(')
end=s.find('\nfunction ',start+1)
if start>0 and end>start:
    block=s[start:end]
    block,n1=re.subn(r'strokeWeight\s*:\s*([^,}\n]+)',r'strokeWeight:meta.gridMerged?0:\1',block,count=1)
    block,n2=re.subn(r'strokeOpacity\s*:\s*([^,}\n]+)',r'strokeOpacity:meta.gridMerged?0:\1',block,count=1)
    s=s[:start]+block+s[end:]

if s==orig:
    raise SystemExit('no changes made')
p.write_text(s,encoding='utf-8')
print('merged automatic zone blocks patch applied')
