from pathlib import Path
import json,collections
p=next(Path("data").glob("precomputed-routes-*.json"))
d=json.loads(p.read_text(encoding="utf-8"))
rows=d.get("routes") or []
by=collections.defaultdict(list)
for x in rows:
    k=f"{x.get('type')}|{x.get('vehicle')}|{x.get('day')}"
    by[k].append(x)
out=[]
out.append(f"total={len(rows)}")
out.append(f"unique_keys={len(by)}")
dups={k:v for k,v in by.items() if len(v)>1}
out.append(f"duplicate_keys={len(dups)}")
for k,v in sorted(dups.items()):
    vals=[]
    for x in v:
        data=x.get("data") or {}
        segs=data.get("segments") or []
        pts=sum(len(s) for s in segs)
        vals.append({
            "districtLabel":data.get("districtLabel"),
            "segments":len(segs),
            "points":pts,
            "missingTerms":data.get("missingTerms"),
            "outsideTerms":data.get("outsideTerms")
        })
    out.append(json.dumps({"key":k,"records":vals},ensure_ascii=False))
Path("tools/route-bundle-key-report.txt").write_text("\n".join(out)+"\n",encoding="utf-8")
print("\n".join(out[:12]))
