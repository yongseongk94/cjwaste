from pathlib import Path
import re, json
s=Path("index.html").read_text(encoding="utf-8")

start=s.find("const DIRECT_ROUTES=")
end=s.find("\nconst DIRECT_INFERRED_REGIONS=",start)
if start<0 or end<0: raise SystemExit("DIRECT_ROUTES not found")
raw=s[start+len("const DIRECT_ROUTES="):end].strip()
if raw.endswith(";"): raw=raw[:-1]
routes=json.loads(raw)
expected={(typ,str(r["vehicle"]),day) for typ,arr in routes.items() for r in arr for day in r.get("days",{})}

bm=re.search(r'<script id="bundledPrecomputed" type="application/json">(.*?)</script>',s,re.S)
if not bm: raise SystemExit("bundledPrecomputed script not found")
bundle=json.loads(bm.group(1))
actual={(str(x.get("type")),str(x.get("vehicle")),str(x.get("day"))) for x in bundle.get("routes",[])}

missing=sorted(expected-actual)
extra=sorted(actual-expected)
print("expected",len(expected),"actual",len(actual),"missing",len(missing),"extra",len(extra))
print("MISSING",missing)
print("EXTRA",extra)

if missing:
    raise SystemExit("Stage 4 failed: bundled direct vehicle/day routes are missing")
for token in ["현대환경|95오0125|내덕1동|단독","제일환경|95오0147|오창읍|단독","제일환경|88저7478|오창읍|단독"]:
    if token not in s: raise SystemExit("Stage 4 failed: contractor route missing: "+token)
print("STAGE4_OK")
