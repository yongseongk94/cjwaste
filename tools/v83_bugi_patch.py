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
"// v67: 내수·북이는 표시된 수거노선에서 30m 이내만 자동 수거대상으로 인정합니다.\nconst RURAL_INFERRED_ROUTE_DISTRICTS=new Set(['오창읍','내수읍','북이면']);\n// 실제 ② 수거노선 레이어에 단계적으로 공개할 읍·면. 먼저 오창만 활성화합니다.\nconst RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍','내수읍']);\nconst RURAL_ROUTE_MATCH_KM=0.030;",
"// 오창·내수·북이는 표시된 실제 수거노선 20m 이내를 우선 확정하고, 그 밖은 ① 추정지역으로 판정합니다.\nconst RURAL_INFERRED_ROUTE_DISTRICTS=new Set(['오창읍','내수읍','북이면']);\nconst RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍','내수읍','북이면']);\nconst RURAL_ROUTE_MATCH_KM=0.020;",
"enable Bugi and 20m"
)

once(
"if(region.district==='오창읍'||region.district==='내수읍'){\n    // v83-2: 오창·내수는 실제 차량×요일 수거노선을 근거로 빈 공간을 ① 추정지역으로 나눕니다.",
"if(RURAL_ROUTE_LAYER_DISTRICTS.has(region.district)){\n    // v83-3: 오창·내수·북이는 실제 차량×요일 수거노선을 근거로 빈 공간을 ① 추정지역으로 나눕니다.",
"Bugi estimated area"
)

once(
"if(district==='오창읍'||district==='내수읍'){\n      // v83-2: 오창·내수는 동지역과 동일하게 20m 실제 수거노선을 우선하고,\n      // 그 밖의 주소는 노선 기반 ① 추정지역으로 판정합니다.",
"if(RURAL_ROUTE_LAYER_DISTRICTS.has(district)){\n      // v83-3: 오창·내수·북이는 동지역과 동일하게 20m 실제 수거노선을 우선하고,\n      // 그 밖의 주소는 노선 기반 ① 추정지역으로 판정합니다.",
"Bugi address schedule"
)

once(
"const SERVICE_ZONE_CACHE_VERSION=`zone-v83-2-naesu-route-estimate|${DONG_ROUTE_CACHE_VERSION}`;",
"const SERVICE_ZONE_CACHE_VERSION=`zone-v83-3-all-rural-route-estimate|${DONG_ROUTE_CACHE_VERSION}`;",
"Bugi service zone cache"
)

s=s.replace(
"// 주소점에서 실제 표시 수거선까지 동지역 20m, 내수·북이 30m 이내인 노선만 후보로 인정합니다.",
"// 주소점에서 실제 표시 수거선까지 동지역·오창·내수·북이 모두 20m 이내인 노선만 후보로 인정합니다."
)
s=s.replace(
"' 내수·북이는 원본 코스 순서를 따라 추정한 차량이동 도로구간도 수거노선에 포함합니다.'",
"' 오창·내수·북이는 원본 코스 순서를 따라 추정한 차량이동 도로구간도 수거노선에 포함합니다.'"
)
s=s.replace(" · 내수·북이 차량이동 추정 "," · 읍·면 차량이동 추정 ")
s=s.replace("내수·북이 차량이동 추정 ","읍·면 차량이동 추정 ")
s=s.replace("// 내수·북이는 원본 항목 순서를 보존해 각 리/도로/시설 사이 차량 이동경로를 도로망으로 추정합니다.",
"// 오창·내수·북이는 원본 항목 순서를 보존해 각 리/도로/시설 사이 차량 이동경로를 도로망으로 추정합니다.")

required=[
  "const RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍','내수읍','북이면']);",
  "const RURAL_ROUTE_MATCH_KM=0.020;",
  "if(RURAL_ROUTE_LAYER_DISTRICTS.has(region.district)){",
  "if(RURAL_ROUTE_LAYER_DISTRICTS.has(district)){",
  "zone-v83-3-all-rural-route-estimate",
]
for token in required:
    if token not in s:
        raise SystemExit(f"missing required token: {token}")

p.write_text(s,encoding="utf-8")
