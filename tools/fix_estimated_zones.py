from pathlib import Path
import re
p=Path("index.html"); s=p.read_text(encoding="utf-8")
# Restore zone payload as a separate lazy-loaded asset. Route-only optimization accidentally removed
# the only precomputed zone source while zone cache version moved to v77.
route_m=re.search(r'<script id="bundledPrecomputed" type="application/json" data-src="([^"]+)"></script>',s)
if not route_m: raise SystemExit("route bundle marker missing")
marker=route_m.group(0)
zone_marker='<script id="bundledServiceZones" type="application/json" data-src="data/service-zones-v77-rural-estimated-regions.json"></script>'
if 'id="bundledServiceZones"' not in s:
 s=s.replace(marker, marker+"\n"+zone_marker)

# inject zone loader immediately before route external loader state
needle="let bundledPrecomputedExternal=null;"
if needle not in s: raise SystemExit("bundle loader state missing")
zonejs=r'''
let bundledServiceZonesExternal=null;
let bundledServiceZonesExternalPromise=null;
async function loadExternalBundledServiceZones(){
  if(bundledServiceZonesExternal)return bundledServiceZonesExternal;
  if(bundledServiceZonesExternalPromise)return bundledServiceZonesExternalPromise;
  const el=document.getElementById('bundledServiceZones');
  const src=el&&el.dataset?el.dataset.src:'';
  if(!src)return null;
  bundledServiceZonesExternalPromise=fetch(src,{cache:'force-cache'})
    .then(r=>{if(!r.ok)throw new Error('service zone bundle '+r.status);return r.json();})
    .then(data=>bundledServiceZonesExternal=data)
    .catch(err=>{console.warn('추정권역 데이터 로드 실패',err);return null;})
    .finally(()=>{bundledServiceZonesExternalPromise=null;});
  return bundledServiceZonesExternalPromise;
}
async function hydrateExternalBundledServiceZones(){
  const data=await loadExternalBundledServiceZones();
  if(!data)return false;
  return hydrateBundledPrecomputedData(data);
}
'''
if "async function loadExternalBundledServiceZones()" not in s:
 s=s.replace(needle,zonejs+"\n"+needle)

# Ensure zones are hydrated at map startup/preload independently from route bundle.
# Add after cache hydration in preloadAllDongRoutes (first exact occurrence in function).
m=re.search(r'(async function preloadAllDongRoutes\(\)\{.*?await hydrateCachedRouteOverlays\(specs\);)',s,re.S)
if not m: raise SystemExit("preloadAllDongRoutes cache hydration not found")
block=m.group(1)
if 'hydrateExternalBundledServiceZones' not in block:
 s=s[:m.start(1)]+block+"\n  await hydrateExternalBundledServiceZones();"+s[m.end(1):]

p.write_text(s,encoding="utf-8")
print("patched")
