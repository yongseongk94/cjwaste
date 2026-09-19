from pathlib import Path
p=Path("index.html")
s=p.read_text(encoding="utf-8")
def once(a,b,label):
    global s
    n=s.count(a)
    if n!=1: raise SystemExit(f"{label}: {n}")
    s=s.replace(a,b,1)

once("const RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍']);",
     "const RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍','내수읍','북이면']);","all rural")
once("const RURAL_ROUTE_MATCH_KM=0.030;",
     "const RURAL_ROUTE_MATCH_KM=0.020;","20m")
once("if(region.district==='오창읍'){\n    const groups=await serviceRouteGroups(type,region.district,region.riName||'');",
     "if(RURAL_ROUTE_LAYER_DISTRICTS.has(region.district)){\n    const groups=await serviceRouteGroups(type,region.district,region.riName||'');","all rural zones")
once("if(district==='오창읍'){\n      const near=await nearestRouteMatchesForAddress(type,{...ctx,district,legalEmd:district});",
     "if(RURAL_ROUTE_LAYER_DISTRICTS.has(district)){\n      const near=await nearestRouteMatchesForAddress(type,{...ctx,district,legalEmd:district});","all rural address")
once("function routeMatchLimitKm(district){const d=canonicalDistrict(district);return RURAL_ROUTE_LAYER_DISTRICTS.has(d)?MAX_ADDRESS_ROUTE_DISTANCE_KM:(RURAL_INFERRED_ROUTE_DISTRICTS.has(d)?RURAL_ROUTE_MATCH_KM:MAX_ADDRESS_ROUTE_DISTANCE_KM)} // 3단계: 오창 20m, 내수·북이는 기존 30m 유지",
     "function routeMatchLimitKm(district){const d=canonicalDistrict(district);return RURAL_ROUTE_LAYER_DISTRICTS.has(d)?MAX_ADDRESS_ROUTE_DISTANCE_KM:(RURAL_INFERRED_ROUTE_DISTRICTS.has(d)?RURAL_ROUTE_MATCH_KM:MAX_ADDRESS_ROUTE_DISTANCE_KM)} // 오창·내수·북이 20m","comment")
# Preserve Gwangam -> Geumam inheritance already present in v76; assert it exists.
if "광암리" not in s or "금암리" not in s: raise SystemExit("Gwangam/Geumam rule missing")
p.write_text(s,encoding="utf-8")
