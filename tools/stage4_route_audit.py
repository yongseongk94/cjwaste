from pathlib import Path
import re, json
p=Path("index.html")
s=p.read_text(encoding="utf-8")

m=re.search(r'const DIRECT_ROUTES=(\{.*?\});\nconst DIRECT_INFERRED_REGIONS=',s,re.S)
if not m: raise SystemExit("DIRECT_ROUTES not found")
routes=json.loads(m.group(1))
expected={(typ,str(r["vehicle"]),day) for typ,arr in routes.items() for r in arr for day in r.get("days",{})}

bm=re.search(r'const BUNDLED_PRECOMPUTED=(\{.*?\});\nconst DONG_ROUTE_CACHE_VERSION=',s,re.S)
if not bm: raise SystemExit("BUNDLED_PRECOMPUTED not found")
bundle=json.loads(bm.group(1))
actual={(str(x.get("type")),str(x.get("vehicle")),str(x.get("day"))) for x in bundle.get("routes",[])}

missing=sorted(expected-actual)
extra=sorted(actual-expected)
print("expected",len(expected),"actual",len(actual),"missing",len(missing),"extra",len(extra))
print("MISSING",missing)
print("EXTRA",extra)

# Stage 4 guards: v76 direct vehicle/day coverage and contractor source coverage must remain present.
if missing:
    raise SystemExit("Stage 4 failed: bundled direct vehicle/day routes are missing")
for token in ["현대환경|95오0125|내덕1동|단독","제일환경|95오0147|오창읍|단독","제일환경|88저7478|오창읍|단독"]:
    if token not in s: raise SystemExit("Stage 4 failed: contractor route missing: "+token)
print("STAGE4_OK")
