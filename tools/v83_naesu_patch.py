from pathlib import Path
p=Path("index.html")
s=p.read_text(encoding="utf-8")

def once(old,new,label):
    global s
    n=s.count(old)
    if n!=1:
        raise SystemExit(f"{label}: expected 1 match, found {n}")
    s=s.replace(old,new,1)

once(
"const RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍']);",
"const RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍','내수읍']);",
"enable Naesu rural route layer"
)

once(
"function routeMatchLimitKm(district){const d=canonicalDistrict(district);return d==='오창읍'?MAX_ADDRESS_ROUTE_DISTANCE_KM:(RURAL_INFERRED_ROUTE_DISTRICTS.has(d)?RURAL_ROUTE_MATCH_KM:MAX_ADDRESS_ROUTE_DISTANCE_KM)} // 오창 20m, 내수·북이는 이번 단계에서 기존 30m 유지",
"function routeMatchLimitKm(district){const d=canonicalDistrict(district);return RURAL_ROUTE_LAYER_DISTRICTS.has(d)?MAX_ADDRESS_ROUTE_DISTANCE_KM:(RURAL_INFERRED_ROUTE_DISTRICTS.has(d)?RURAL_ROUTE_MATCH_KM:MAX_ADDRESS_ROUTE_DISTANCE_KM)} // 활성화된 읍·면은 20m, 아직 미활성 북이는 기존 30m 유지",
"Naesu 20m route match"
)

once(
"if(region.district==='오창읍'){\n    // v83-1: 오창은 실제 차량×요일 수거노선을 근거로 빈 공간을 ① 추정지역으로 나눕니다.",
"if(region.district==='오창읍'||region.district==='내수읍'){\n    // v83-2: 오창·내수는 실제 차량×요일 수거노선을 근거로 빈 공간을 ① 추정지역으로 나눕니다.",
"Naesu estimated area"
)

once(
"if(district==='오창읍'){\n      // v83-1: 오창은 동지역과 동일하게 20m 실제 수거노선을 우선하고,\n      // 그 밖의 주소는 노선 기반 ① 추정지역으로 판정합니다.",
"if(district==='오창읍'||district==='내수읍'){\n      // v83-2: 오창·내수는 동지역과 동일하게 20m 실제 수거노선을 우선하고,\n      // 그 밖의 주소는 노선 기반 ① 추정지역으로 판정합니다.",
"Naesu address schedule"
)

once(
"const SERVICE_ZONE_CACHE_VERSION=`zone-v83-1a-scope-separated|${DONG_ROUTE_CACHE_VERSION}`;",
"const SERVICE_ZONE_CACHE_VERSION=`zone-v83-2-naesu-route-estimate|${DONG_ROUTE_CACHE_VERSION}`;",
"Naesu service zone cache"
)

required=[
  "const RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍','내수읍']);",
  "region.district==='오창읍'||region.district==='내수읍'",
  "district==='오창읍'||district==='내수읍'",
  "zone-v83-2-naesu-route-estimate",
]
for token in required:
    if token not in s:
        raise SystemExit(f"missing required token: {token}")

p.write_text(s,encoding="utf-8")
