from pathlib import Path
import json, gzip
p=Path("data/precomputed-v76-layer-visibility-refresh.json")
d=json.loads(p.read_text(encoding="utf-8"))
def enc(x): return json.dumps(x,ensure_ascii=False,separators=(",",":")).encode("utf-8")
parts={
 "full":d,
 "routes":d.get("routes") or [],
 "zones":d.get("zones") or {},
 "zones_general":(d.get("zones") or {}).get("general") or [],
 "zones_recycle":(d.get("zones") or {}).get("recycle") or [],
}
out=[]
for k,v in parts.items():
 b=enc(v)
 out.append(f"{k}_bytes={len(b)}")
 out.append(f"{k}_gzip_bytes={len(gzip.compress(b,compresslevel=9))}")
out.append(f"top_keys={list(d.keys())}")
out.append(f"route_count={len(d.get('routes') or [])}")
Path("tools/precomputed-size-report.txt").write_text("\n".join(out)+"\n",encoding="utf-8")
print("\n".join(out))
