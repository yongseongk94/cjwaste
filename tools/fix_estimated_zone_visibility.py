from pathlib import Path
p=Path('index.html')
s=p.read_text(encoding='utf-8')
old="""      z.polygon.setOptions({
        fillColor:color,
        fillOpacity:z.manual?.28:(z.ambiguous?.18:(contract?.36:(rural?.30:.22))),
        strokeWeight:z.gridMerged?0:(z.manual?2:(contract?2:(rural?1:0))),
        strokeColor:z.manual?'#111827':color,
        strokeOpacity:z.gridMerged?0:(z.manual?.95:(contract?.86:(rural?.42:0)))
      });"""
new=old.replace("strokeOpacity:z.gridMerged?0:(z.manual?.95:(contract?.86:(rural?.42:0)))", "strokeOpacity:z.gridMerged?0:(z.manual?.95:(contract?.86:(rural?.42:0))),\n        zIndex:3")
assert old in s
s=s.replace(old,new,1)
anchor='function syncServiceZoneVisibility(type,forceRedraw=false){'
helper="""function ensureBundledServiceZones(type){
  if((serviceZoneOverlays[type]||[]).some(z=>!z.manual))return true;
  const data=bundledPrecomputedData();
  const zones=Array.isArray(data?.zones?.[type])?data.zones[type]:[];
  if(!zones.length)return false;
  for(const z of zones)addServiceZonePolygon(type,z.points,{...z,automatic:true,fromCache:true,fromBundle:true});
  rebuildManualZoneOverlays(type);
  serviceZoneBuilt[type]=true;
  return true;
}
"""
assert anchor in s
s=s.replace(anchor,helper+anchor,1)
oldset="""  }else{
    syncBoundaryVisibility();
    if(serviceLayerState.zone)buildServiceZones(layer).then(()=>syncServiceZoneVisibility(layer)).catch(e=>console.warn('수거권역 생성 실패',e));"""
newset="""  }else{
    syncBoundaryVisibility();
    if(serviceLayerState.zone){
      ensureBundledServiceZones(layer);
      syncServiceZoneVisibility(layer,true);
      buildServiceZones(layer).then(()=>syncServiceZoneVisibility(layer,true)).catch(e=>console.warn('수거권역 생성 실패',e));
    }"""
assert oldset in s
s=s.replace(oldset,newset,1)
p.write_text(s,encoding='utf-8')
print('ESTIMATED_ZONE_VISIBILITY_FIX_OK')
