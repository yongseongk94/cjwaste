from pathlib import Path
import re, json, base64, hashlib

p=Path("index.html")
s=p.read_text(encoding="utf-8")
before_bytes=len(s.encode("utf-8"))

# 1) Externalize embedded landing JPEG.
img_pat=re.compile(r'data:image/jpeg;base64,([A-Za-z0-9+/=]+)')
m=img_pat.search(s)
if not m:
    raise SystemExit("embedded landing JPEG not found")
img=base64.b64decode(m.group(1))
assets=Path("assets")
assets.mkdir(exist_ok=True)
img_path=assets/"landing-bg.jpg"
img_path.write_bytes(img)
s=s[:m.start()]+"assets/landing-bg.jpg"+s[m.end():]

# 2) Externalize huge bundled precomputed JSON.
bundle_pat=re.compile(r'<script id="bundledPrecomputed" type="application/json">(.*?)</script>',re.S)
m=bundle_pat.search(s)
if not m:
    raise SystemExit("bundledPrecomputed script not found")
raw_bundle=m.group(1).strip()
data=json.loads(raw_bundle)
version=str(data.get("version") or "unknown")
safe_version=re.sub(r'[^A-Za-z0-9._-]+','-',version).strip('-') or "unknown"
data_dir=Path("data")
data_dir.mkdir(exist_ok=True)
bundle_path=data_dir/f"precomputed-{safe_version}.json"
bundle_text=json.dumps(data,ensure_ascii=False,separators=(",",":"))
bundle_path.write_text(bundle_text,encoding="utf-8")
marker=f'<script id="bundledPrecomputed" type="application/json" data-src="{bundle_path.as_posix()}"></script>'
s=s[:m.start()]+marker+s[m.end():]

# 3) Convert bundled-data reader to cache-first lazy external loader.
old_reader="""function bundledPrecomputedData(){
  try{
    const el=document.getElementById('bundledPrecomputed');
    if(!el)return null;
    const raw=String(el.textContent||'').trim();
    if(!raw||raw==='null')return null;
    return JSON.parse(raw);
  }catch(e){console.warn('내장 사전계산 데이터 읽기 실패',e);return null}
}
function hydrateBundledPrecomputedData(){
  const data=bundledPrecomputedData();"""
new_reader="""let bundledPrecomputedExternal=null;
let bundledPrecomputedExternalPromise=null;
function bundledPrecomputedData(){
  try{
    if(bundledPrecomputedExternal)return bundledPrecomputedExternal;
    const el=document.getElementById('bundledPrecomputed');
    if(!el)return null;
    const raw=String(el.textContent||'').trim();
    if(!raw||raw==='null')return null;
    return JSON.parse(raw);
  }catch(e){console.warn('사전계산 데이터 읽기 실패',e);return null}
}
async function loadExternalBundledPrecomputedData(){
  if(bundledPrecomputedExternal)return bundledPrecomputedExternal;
  const inline=bundledPrecomputedData();
  if(inline)return inline;
  if(bundledPrecomputedExternalPromise)return bundledPrecomputedExternalPromise;
  bundledPrecomputedExternalPromise=(async()=>{
    try{
      const el=document.getElementById('bundledPrecomputed');
      const src=String(el?.dataset?.src||'').trim();
      if(!src)return null;
      const res=await fetch(src,{cache:'force-cache'});
      if(!res.ok)throw new Error('HTTP '+res.status);
      const data=await res.json();
      bundledPrecomputedExternal=data;
      return data;
    }catch(e){
      console.warn('외부 사전계산 데이터 로드 실패',e);
      return null;
    }finally{
      bundledPrecomputedExternalPromise=null;
    }
  })();
  return bundledPrecomputedExternalPromise;
}
async function hydrateExternalBundledPrecomputedData(){
  const data=await loadExternalBundledPrecomputedData();
  return data?hydrateBundledPrecomputedData(data):false;
}
function hydrateBundledPrecomputedData(dataOverride=null){
  const data=dataOverride||bundledPrecomputedData();"""
if old_reader not in s:
    raise SystemExit("bundled reader block not found")
s=s.replace(old_reader,new_reader,1)

# 4) When external bundle is used, persist its routes into IndexedDB.
old_create="""        createDongRouteOverlay(spec,{...(r.data||{}),fromCache:true,fromBundle:true});
      }
      hydrated=true;"""
new_create="""        const bundleRouteData={...(r.data||{})};
        createDongRouteOverlay(spec,{...bundleRouteData,fromCache:true,fromBundle:true});
        putCachedDongRoute(spec,bundleRouteData).catch(e=>console.warn('사전계산 노선 IndexedDB 저장 실패',spec,e));
      }
      hydrated=true;"""
if old_create not in s:
    raise SystemExit("bundle create route block not found")
s=s.replace(old_create,new_create,1)

# 5) Selection path: IndexedDB first, external bundle only on cache miss, API build last.
old_select="""  // 1차: IndexedDB에 저장된 선을 먼저 복원하여 클릭 즉시 보여줍니다.
  await hydrateCachedRouteOverlays(specs);
  syncDongRouteVisibility(type);
  // 2차: 캐시에 없는 노선만 뒤에서 계산하며, 완성되는 선부터 바로 추가합니다.
  const missing=specs.filter(s=>!existingDongRouteOverlay(s));
  await mapWithConcurrency(missing,3,async spec=>{"""
new_select="""  // 1차: IndexedDB에 저장된 선을 먼저 복원하여 클릭 즉시 보여줍니다.
  await hydrateCachedRouteOverlays(specs);
  // 2차: 캐시가 비어 있는 새 브라우저에서만 외부 사전계산 묶음을 1회 불러오고 IndexedDB에 저장합니다.
  if(specs.some(s=>!existingDongRouteOverlay(s)))await hydrateExternalBundledPrecomputedData();
  syncDongRouteVisibility(type);
  // 3차: 사전계산 묶음에도 없는 노선만 실제 도로망으로 계산합니다.
  const missing=specs.filter(s=>!existingDongRouteOverlay(s));
  await mapWithConcurrency(missing,3,async spec=>{"""
if old_select not in s:
    raise SystemExit("selection cache block not found")
s=s.replace(old_select,new_select,1)

# 6) Background preload path: IndexedDB first, external bundle only if anything remains missing.
old_preload="""  // v63: index.html 내장본을 최우선 사용합니다. 내장본이 없거나 일부 누락된 경우에만 IndexedDB를 확인합니다.
  const bundled=hydrateBundledPrecomputedData();
  if(!bundled)await hydrateCachedRouteOverlays(specs);
  if(activeLayer==='general'||activeLayer==='recycle')syncDongRouteVisibility(activeLayer);

  // 캐시에 없는 노선만 백그라운드에서 준비합니다. 인위적인 120ms 대기는 제거했습니다.
  const missing=specs.filter(s=>!existingDongRouteOverlay(s));"""
new_preload="""  // v78: 대용량 사전계산 데이터는 index.html에서 분리합니다.
  // IndexedDB를 먼저 복원하고, 새 브라우저처럼 누락 노선이 있을 때만 외부 묶음을 1회 불러옵니다.
  await hydrateCachedRouteOverlays(specs);
  if(specs.some(s=>!existingDongRouteOverlay(s)))await hydrateExternalBundledPrecomputedData();
  if(activeLayer==='general'||activeLayer==='recycle')syncDongRouteVisibility(activeLayer);

  // IndexedDB와 외부 사전계산 묶음에도 없는 노선만 백그라운드에서 실제 계산합니다.
  const missing=specs.filter(s=>!existingDongRouteOverlay(s));"""
if old_preload not in s:
    raise SystemExit("preload block not found")
s=s.replace(old_preload,new_preload,1)

# 7) Update stale comments describing in-index embedding.
s=s.replace(
"// 빌드 시 확정된 노선/수거권역 좌표를 index.html 안에 직접 내장합니다.\n// 새 PC/새 브라우저에서도 IndexedDB 생성이나 길찾기 API 계산을 기다리지 않고 즉시 복원됩니다.",
"// 빌드 시 확정된 노선 좌표는 외부 정적 JSON으로 분리합니다.\n// 기존 브라우저는 IndexedDB를 우선 사용하고, 새 브라우저만 외부 사전계산 데이터를 1회 받아 캐시에 저장합니다."
)

p.write_text(s,encoding="utf-8")
after_bytes=len(s.encode("utf-8"))

# Validation and report.
if 'data:image/jpeg;base64,' in s:
    raise SystemExit("embedded JPEG still present")
if raw_bundle[:120] in s:
    raise SystemExit("large bundled JSON still embedded")
if 'data-src="'+bundle_path.as_posix()+'"' not in s:
    raise SystemExit("external bundle marker missing")
if 'assets/landing-bg.jpg' not in s:
    raise SystemExit("external landing image reference missing")
if json.loads(bundle_path.read_text(encoding="utf-8")).get("version")!=version:
    raise SystemExit("external bundle JSON validation failed")

report=[
    "INDEX OPTIMIZATION RESULT",
    f"before_bytes={before_bytes}",
    f"after_bytes={after_bytes}",
    f"saved_bytes={before_bytes-after_bytes}",
    f"saved_percent={(before_bytes-after_bytes)*100/before_bytes:.2f}",
    f"landing_image_bytes={len(img)}",
    f"landing_image_sha256={hashlib.sha256(img).hexdigest()}",
    f"bundle_file={bundle_path.as_posix()}",
    f"bundle_bytes={bundle_path.stat().st_size}",
    f"bundle_version={version}",
    f"bundle_routes={len(data.get('routes') or [])}",
    f"bundle_general_zones={len((data.get('zones') or {}).get('general') or [])}",
    f"bundle_recycle_zones={len((data.get('zones') or {}).get('recycle') or [])}",
    "load_order=IndexedDB -> external precomputed JSON on cache miss -> live road build for remaining misses",
]
Path("tools/index-optimize-result.txt").write_text("\n".join(report)+"\n",encoding="utf-8")
print("\n".join(report))
