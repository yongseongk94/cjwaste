from pathlib import Path
p=Path("index.html")
s=p.read_text(encoding="utf-8")

old="""let bundledPrecomputedExternal=null;
let bundledPrecomputedExternalPromise=null;"""
new="""let bundledPrecomputedExternal=null;
let bundledPrecomputedExternalPromise=null;
let bundledPrecomputedHydrated=false;"""
if old not in s: raise SystemExit("bundle vars marker missing")
s=s.replace(old,new,1)

old="""async function hydrateExternalBundledPrecomputedData(){
  const data=await loadExternalBundledPrecomputedData();
  return data?hydrateBundledPrecomputedData(data):false;
}
function hydrateBundledPrecomputedData(dataOverride=null){
  const data=dataOverride||bundledPrecomputedData();
  if(!data)return false;
  let hydrated=false;
  try{
    // 노선 좌표는 기존 v65 캐시를 그대로 재사용합니다. v66은 수거권역 구조만 변경합니다.
    if(data.version===DONG_ROUTE_CACHE_VERSION){
      const specMap=new Map(allDongRouteSpecs().map(s=>[`${s.type}|${s.vehicle}|${s.day}`,s]));
      for(const r of (data.routes||[])){
        const spec=specMap.get(`${r.type}|${r.vehicle}|${r.day}`);
        if(!spec||existingDongRouteOverlay(spec))continue;
        const bundleRouteData={...(r.data||{})};
        createDongRouteOverlay(spec,{...bundleRouteData,fromCache:true,fromBundle:true});
        putCachedDongRoute(spec,bundleRouteData).catch(e=>console.warn('사전계산 노선 IndexedDB 저장 실패',spec,e));
      }
      hydrated=true;
    }"""
new="""async function hydrateExternalBundledPrecomputedData(){
  if(bundledPrecomputedHydrated)return true;
  const data=await loadExternalBundledPrecomputedData();
  const ok=data?hydrateBundledPrecomputedData(data):false;
  if(ok)bundledPrecomputedHydrated=true;
  return ok;
}
function bundleRouteRecordSpec(record,specs){
  const candidates=(specs||[]).filter(s=>s.type===record?.type&&s.vehicle===record?.vehicle&&s.day===record?.day);
  if(!candidates.length)return null;

  // v79 이후 번들은 담당권역까지 저장하므로 정확히 같은 scope를 우선 복원합니다.
  const savedScope=String(record?.scopeSignature||'').trim();
  if(savedScope){
    const exact=candidates.find(s=>routeScopeSignature(s)===savedScope);
    if(exact)return exact;
  }
  if(Array.isArray(record?.districts)&&record.districts.length){
    const wanted=[...new Set(record.districts.map(canonicalDistrict).filter(Boolean))].sort().join('|');
    const exact=candidates.find(s=>routeScopeSignature(s)===wanted);
    if(exact)return exact;
  }

  // 구형 v76 번들은 scope 메타데이터가 없었습니다.
  // 당시 base 노선과 오창 전용 rural 노선 중 실제 districtLabel과 맞는 후보를 찾고,
  // Stage 3에서 뒤늦게 추가된 내수·북이 rural 스펙에 예전 base 노선을 잘못 붙이지 않습니다.
  const labels=String(record?.data?.districtLabel||'')
    .split(/[·,]/).map(canonicalDistrict).filter(Boolean);
  const compatible=candidates.filter(s=>{
    const allowed=routeAllowedDistricts(s);
    return !labels.length||labels.every(d=>allowed.includes(d));
  });
  if(compatible.length===1)return compatible[0];
  const base=(compatible.length?compatible:candidates).find(s=>s.scopeKind==='base');
  return base||(compatible[0]||candidates[0]);
}
function hydrateBundledPrecomputedData(dataOverride=null){
  const data=dataOverride||bundledPrecomputedData();
  if(!data)return false;
  let hydrated=false;
  try{
    if(data.version===DONG_ROUTE_CACHE_VERSION){
      const specs=allDongRouteSpecs();
      for(const r of (data.routes||[])){
        const spec=bundleRouteRecordSpec(r,specs);
        if(!spec||existingDongRouteOverlay(spec))continue;
        const bundleRouteData={...(r.data||{})};
        const audit=finalRouteCoordinateAudit(spec,bundleRouteData);
        if(!audit.ok){
          console.warn('사전계산 노선 scope 불일치로 복원을 건너뜁니다.',r.type,r.vehicle,r.day,audit);
          continue;
        }
        createDongRouteOverlay(spec,{...bundleRouteData,fromCache:true,fromBundle:true});
        putCachedDongRoute(spec,bundleRouteData).catch(e=>console.warn('사전계산 노선 IndexedDB 저장 실패',spec,e));
      }
      hydrated=true;
    }"""
if old not in s: raise SystemExit("hydrate block marker missing")
s=s.replace(old,new,1)

old="""function createDongRouteOverlay(spec,data){
  let segments=Array.isArray(data.segments)?data.segments:[];"""
new="""function createDongRouteOverlay(spec,data){
  // 캐시·외부번들·백그라운드 계산이 동시에 끝나도 같은 차량×요일×권역을 중복 생성하지 않습니다.
  const already=existingDongRouteOverlay(spec);
  if(already)return already;
  let segments=Array.isArray(data.segments)?data.segments:[];"""
if old not in s: raise SystemExit("create overlay marker missing")
s=s.replace(old,new,1)

old="""    data.distance=Number(item.roadResult?.distance)||0;
    routes.push({type,vehicle:item.vehicle,day:item.day,data});"""
new="""    data.distance=Number(item.roadResult?.distance)||0;
    routes.push({
      type,vehicle:item.vehicle,day:item.day,
      districts:[...routeAllowedDistricts(item)],
      scopeKind:item.scopeKind||'',
      scopeSignature:routeScopeSignature(item),
      data
    });"""
if old not in s: raise SystemExit("export route marker missing")
s=s.replace(old,new,1)

# User-visible / code-comment stale 30m wording. Actual logic is 0.020km for all target districts.
n30=s.count("30m")
s=s.replace("30m","20m")

p.write_text(s,encoding="utf-8")
Path("tools/runtime-optimize-result.txt").write_text(
    "RUNTIME OPTIMIZATION\n"
    f"stale_30m_replacements={n30}\n"
    "bundle_hydration_idempotent=true\n"
    "overlay_creation_dedup=true\n"
    "bundle_scope_metadata_export=true\n"
    "legacy_bundle_scope_matching=true\n",
    encoding="utf-8"
)
print("PATCH_OK", "30m_replacements", n30)
