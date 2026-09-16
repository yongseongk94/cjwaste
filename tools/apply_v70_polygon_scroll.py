from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')
orig=s

# 1) New cache version: bundled polygon geometry + persistent layer visibility.
old="const SERVICE_ZONE_CACHE_VERSION=`zone-v69-merged-grid-blocks|${DONG_ROUTE_CACHE_VERSION}`;"
new="const SERVICE_ZONE_CACHE_VERSION=`zone-v70-dong-polygons-persist|${DONG_ROUTE_CACHE_VERSION}`;"
if old not in s:
    raise SystemExit('v69 service-zone version marker not found')
s=s.replace(old,new,1)

# 2) Persist display rings and exact hit-test rings through bundle export and IndexedDB.
pat=r"points:z\.points\.map\(p=>\(\{lat:\+p\.lat,lng:\+p\.lng\}\)\),"
rep=("points:z.points.map(p=>({lat:+p.lat,lng:+p.lng})),"
     "rings:(Array.isArray(z.rings)&&z.rings.length?z.rings:[z.points]).map(r=>r.map(p=>({lat:+p.lat,lng:+p.lng}))),"
     "hitRings:(Array.isArray(z.hitRings)&&z.hitRings.length?z.hitRings:(Array.isArray(z.rings)&&z.rings.length?z.rings:[z.points])).map(r=>r.map(p=>({lat:+p.lat,lng:+p.lng}))),")
s,n=re.subn(pat,rep,s)
if n<2:
    raise SystemExit(f'zone point serialization markers found {n}, expected >=2')

# Keep polygonized marker in serialized metadata.
marker='groupOutline:!!z.groupOutline,gridMerged:!!z.gridMerged'
if marker not in s:
    raise SystemExit('gridMerged serialization marker missing')
s=s.replace(marker,marker+',polygonized:!!z.polygonized')

# 3) A zone with holes uses exact hit rings for schedule lookup; display rings may be simplified only visually.
old="return pointInSimplePolygon(lat,lng,z.points||[]);"
if old not in s:
    raise SystemExit('serviceZoneOverlayMatch point marker missing')
s=s.replace(old,"return pointInZonePolygon(lat,lng,z);",1)

old="function pointInSimplePolygon(lat,lng,points){return pointInRing([+lng,+lat],(points||[]).map(p=>[+p.lng,+p.lat]))}"
new=r'''function pointInSimplePolygon(lat,lng,points){return pointInRing([+lng,+lat],(points||[]).map(p=>[+p.lng,+p.lat]))}
function pointInZonePolygon(lat,lng,zone){
  const rings=(Array.isArray(zone?.hitRings)&&zone.hitRings.length)?zone.hitRings:((Array.isArray(zone?.rings)&&zone.rings.length)?zone.rings:[zone?.points||[]]);
  if(!rings.length||!pointInSimplePolygon(lat,lng,rings[0]))return false;
  for(let i=1;i<rings.length;i++)if(pointInSimplePolygon(lat,lng,rings[i]))return false;
  return true;
}'''
if old not in s:
    raise SystemExit('pointInSimplePolygon marker missing')
s=s.replace(old,new,1)

# 4) Render nested Kakao Polygon paths (outer ring + holes) while preserving exact hit geometry.
old="""  const polygon=new kakao.maps.Polygon({\n    path:points.map(p=>new kakao.maps.LatLng(+p.lat,+p.lng)),"""
new=r'''  const displayRings=(Array.isArray(meta.rings)&&meta.rings.length?meta.rings:[points]).filter(r=>Array.isArray(r)&&r.length>=3);
  if(!displayRings.length)return null;
  const normalizedDisplayRings=displayRings.map(r=>r.map(p=>({lat:+p.lat,lng:+p.lng})));
  const polygonPath=normalizedDisplayRings.length>1
    ? normalizedDisplayRings.map(r=>r.map(p=>new kakao.maps.LatLng(p.lat,p.lng)))
    : normalizedDisplayRings[0].map(p=>new kakao.maps.LatLng(p.lat,p.lng));
  const polygon=new kakao.maps.Polygon({
    path:polygonPath,'''
if old not in s:
    raise SystemExit('addServiceZonePolygon path marker missing')
s=s.replace(old,new,1)

old="  const zone={polygon,type,...meta,points:points.map(p=>({lat:+p.lat,lng:+p.lng}))};"
new=r'''  const exactRings=(Array.isArray(meta.hitRings)&&meta.hitRings.length?meta.hitRings:normalizedDisplayRings).map(r=>r.map(p=>({lat:+p.lat,lng:+p.lng})));
  const zone={polygon,type,...meta,points:[...(exactRings[0]||[])],rings:normalizedDisplayRings,hitRings:exactRings};'''
if old not in s:
    raise SystemExit('addServiceZonePolygon zone marker missing')
s=s.replace(old,new,1)

# 5) Visibility sync no longer blindly removes every service polygon first.
start=s.find('function syncServiceZoneVisibility(type){')
if start<0: raise SystemExit('syncServiceZoneVisibility start missing')
end=s.find('\nfunction ',start+1)
if end<0: raise SystemExit('syncServiceZoneVisibility end missing')
new_sync=r'''function syncServiceZoneVisibility(type,forceRedraw=false){
  const provider=selectedVehicle[type]||'전체',day=activeDay||'전체';
  for(const t of ['general','recycle']){
    for(const z of (serviceZoneOverlays[t]||[])){
      const zoneVehicles=(z.vehicles||[]).length?z.vehicles:[z.vehicle];
      const providerOk=provider==='전체'||zoneVehicles.some(v=>routeSelectedBy(provider,v))||provider===(z.provider||'');
      const dayOk=day==='전체'||(z.days||[]).includes(day);
      const visible=t===type&&activeLayer===type&&serviceLayerState.zone&&providerOk&&dayOk;
      if(!visible){if(z.polygon?.getMap())z.polygon.setMap(null);continue}
      const contract=!!z.contractLayer;
      const color=z.manual?'#0f172a':(z.ambiguous?'#94a3b8':(contract?OCHANG_CONTRACT_COLOR:(day!=='전체'?(DAY_COLORS[day]||'#64748b'):serviceZoneColor(z.days,type))));
      const rural=!!z.rural||RI_LAYER_DISTRICTS.has(z.district||'');
      z.polygon.setOptions({
        fillColor:color,
        fillOpacity:z.manual?.28:(z.ambiguous?.18:(contract?.36:(rural?.30:.22))),
        strokeWeight:z.gridMerged?0:(z.manual?2:(contract?2:(rural?1:0))),
        strokeColor:z.manual?'#111827':color,
        strokeOpacity:z.gridMerged?0:(z.manual?.95:(contract?.86:(rural?.42:0)))
      });
      if(forceRedraw&&z.polygon.getMap()===map)z.polygon.setMap(null);
      if(z.polygon.getMap()!==map)z.polygon.setMap(map);
    }
  }
}
let serviceLayerRefreshSeq=0,serviceLayerHardRefresh=false;
function queueActiveServiceLayerRefresh(force=false){
  if(force)serviceLayerHardRefresh=true;
  const seq=++serviceLayerRefreshSeq;
  requestAnimationFrame(()=>{
    if(seq!==serviceLayerRefreshSeq)return;
    if(activeLayer!=='general'&&activeLayer!=='recycle')return;
    const hard=serviceLayerHardRefresh;serviceLayerHardRefresh=false;
    syncServiceZoneVisibility(activeLayer,hard);
  });
}'''
s=s[:start]+new_sync+s[end:]

# 6) Reassert selected layer after mouse-wheel zoom / map idle and ordinary page scrolling.
old="  kakao.maps.event.addListener(map,'click',handleMapClick);"
new=r'''  kakao.maps.event.addListener(map,'click',handleMapClick);
  kakao.maps.event.addListener(map,'zoom_start',()=>{serviceLayerHardRefresh=true;queueActiveServiceLayerRefresh(false)});
  kakao.maps.event.addListener(map,'zoom_changed',()=>queueActiveServiceLayerRefresh(false));
  kakao.maps.event.addListener(map,'idle',()=>queueActiveServiceLayerRefresh(serviceLayerHardRefresh));
  window.addEventListener('scroll',()=>queueActiveServiceLayerRefresh(false),{passive:true});'''
if old not in s:
    raise SystemExit('map click listener marker missing')
s=s.replace(old,new,1)

if s==orig:
    raise SystemExit('no v70 changes made')
p.write_text(s,encoding='utf-8')
print('v70 polygon display + persistent layer patch applied')
