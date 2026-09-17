from pathlib import Path
import re,json
p=Path('index.html')
t=p.read_text(encoding='utf-8')
# Force fresh bundle/cache namespace without changing route/zone data.
t=t.replace('v75-naedeok2-apartment-only','v76-layer-visibility-refresh')
t=t.replace('zone-v75-naedeok2-apartment-only','zone-v76-layer-visibility-refresh')
# Add a reliable re-attachment helper immediately before setLayer.
needle='function setLayer(layer){'
helper="""function forceActiveServiceLayerVisibility(layer){
  if(layer!=='general'&&layer!=='recycle')return;
  try{
    if(serviceLayerState.zone)syncServiceZoneVisibility(layer,true);
    if(serviceLayerState.route)syncDongRouteVisibility(layer);
  }catch(e){console.warn('레이어 강제 재표시 실패',e)}
}
function setLayer(layer){"""
if needle not in t: raise SystemExit('setLayer not found')
t=t.replace(needle,helper,1)
# Re-attach immediately and twice after render/layout settles.
needle2='  updateMapBadge();\n}\nfunction updateMapBadge(custom){'
replacement="""  updateMapBadge();
  if(service){
    forceActiveServiceLayerVisibility(layer);
    setTimeout(()=>{if(activeLayer===layer)forceActiveServiceLayerVisibility(layer)},120);
    setTimeout(()=>{if(activeLayer===layer)forceActiveServiceLayerVisibility(layer)},700);
  }
}
function updateMapBadge(custom){"""
if needle2 not in t: raise SystemExit('setLayer tail not found')
t=t.replace(needle2,replacement,1)
# Ensure bundle/current cache strings now match.
if "const DONG_ROUTE_CACHE_VERSION='v76-layer-visibility-refresh'" not in t: raise SystemExit('route cache version not updated')
if '"version":"v76-layer-visibility-refresh"' not in t: raise SystemExit('bundled version not updated')
if 'zone-v76-layer-visibility-refresh|v76-layer-visibility-refresh' not in t: raise SystemExit('zone version not updated')
p.write_text(t,encoding='utf-8')
Path('tools/v76_layer_visibility_report.json').write_text(json.dumps({'version':'v76-layer-visibility-refresh','fix':['fresh cache namespace','immediate service-layer reattach','120ms reattach','700ms reattach'],'preserve':'existing v75 Naedeok2 contractor classification and bundled route/zone geometry'},ensure_ascii=False,indent=2),encoding='utf-8')
