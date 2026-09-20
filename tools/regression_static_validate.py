from pathlib import Path
import re,json
s=Path("index.html").read_text(encoding="utf-8")
out=[]
checks={
 "index_bytes":Path("index.html").stat().st_size,
 "landing_bg_exists":Path("assets/landing-bg.jpg").exists(),
 "landing_bg_bytes":Path("assets/landing-bg.jpg").stat().st_size if Path("assets/landing-bg.jpg").exists() else 0,
 "indexeddb_db": "cjwaste-dong-route-cache" in s,
 "cache_version_v76":"const DONG_ROUTE_CACHE_VERSION='v76-layer-visibility-refresh'" in s,
 "match_20m":"const RURAL_ROUTE_MATCH_KM=0.020" in s,
 "rural_inferred_three":"new Set(['오창읍','내수읍','북이면'])" in s,
 "external_loader":"async function loadExternalBundledPrecomputedData()" in s,
 "external_hydrator":"async function hydrateExternalBundledPrecomputedData()" in s,
 "cache_first_preload":"await hydrateCachedRouteOverlays(specs);" in s,
 "external_on_miss":"if(specs.some(s=>!existingDongRouteOverlay(s)))await hydrateExternalBundledPrecomputedData();" in s,
 "background_external":"assets/landing-bg.jpg" in s,
 "embedded_jpeg_absent":"data:image/jpeg;base64," not in s,
}
m=re.search(r'data-src="(data/precomputed-routes-[^"]+\.json)"',s)
checks["bundle_ref"]=m.group(1) if m else ""
if m and Path(m.group(1)).exists():
 d=json.loads(Path(m.group(1)).read_text(encoding="utf-8"))
 checks["bundle_exists"]=True
 checks["bundle_bytes"]=Path(m.group(1)).stat().st_size
 checks["bundle_routes"]=len(d.get("routes") or [])
 checks["bundle_has_zones"]="zones" in d
else: checks["bundle_exists"]=False
# crude syntax extraction
scripts=re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',s,re.S|re.I)
main=max(scripts,key=len)
Path("/tmp/cjwaste-main.js").write_text(main,encoding="utf-8")
for k,v in checks.items(): out.append(f"{k}={v}")
Path("tools/regression-static-report.txt").write_text("\n".join(out)+"\n",encoding="utf-8")
print("\n".join(out))
