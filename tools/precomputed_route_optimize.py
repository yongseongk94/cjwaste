from pathlib import Path
import re, json, hashlib, gzip

idx=Path("index.html")
s=idx.read_text(encoding="utf-8")
m=re.search(r'<script id="bundledPrecomputed" type="application/json" data-src="([^"]+)"></script>',s)
if not m:
    raise SystemExit("external bundledPrecomputed marker not found")
old_path=Path(m.group(1))
if not old_path.exists():
    raise SystemExit(f"bundle file missing: {old_path}")

old_bytes=old_path.stat().st_size
data=json.loads(old_path.read_text(encoding="utf-8"))
routes=data.get("routes") or []
if not routes:
    raise SystemExit("routes missing from precomputed bundle")

# Zones in the current external file are v76 while the page uses zone-v77; they are never hydrated.
# Keep only immutable route precompute data. Service zones continue to rebuild/cache through their own v77 path.
route_only={
    "version":data.get("version"),
    "generatedAt":data.get("generatedAt"),
    "routes":routes,
    "restoredFrom":data.get("restoredFrom"),
}
route_text=json.dumps(route_only,ensure_ascii=False,separators=(",",":"))
route_bytes=route_text.encode("utf-8")
content_hash=hashlib.sha256(route_bytes).hexdigest()[:12]
safe_version=re.sub(r'[^A-Za-z0-9._-]+','-',str(data.get("version") or "unknown")).strip('-') or "unknown"
new_path=Path("data")/f"precomputed-routes-{safe_version}-{content_hash}.json"
new_path.write_bytes(route_bytes)

new_marker=f'<script id="bundledPrecomputed" type="application/json" data-src="{new_path.as_posix()}"></script>'
s=s[:m.start()]+new_marker+s[m.end():]
idx.write_text(s,encoding="utf-8")

# Remove obsolete generated precomputed files from the working tree.
for p in Path("data").glob("precomputed*.json"):
    if p!=new_path:
        p.unlink()

report=[
    "PRECOMPUTED ROUTE PAYLOAD OPTIMIZATION",
    f"old_bundle_bytes={old_bytes}",
    f"new_route_bundle_bytes={len(route_bytes)}",
    f"saved_bytes={old_bytes-len(route_bytes)}",
    f"saved_percent={(old_bytes-len(route_bytes))*100/old_bytes:.2f}",
    f"new_route_bundle_gzip_bytes={len(gzip.compress(route_bytes,compresslevel=9))}",
    f"route_count={len(routes)}",
    f"removed_general_zone_count={len((data.get('zones') or {}).get('general') or [])}",
    f"removed_recycle_zone_count={len((data.get('zones') or {}).get('recycle') or [])}",
    f"bundle_path={new_path.as_posix()}",
    f"content_hash={content_hash}",
    "cache_busting=content hash in filename",
]
Path("tools/precomputed-route-optimize-result.txt").write_text("\n".join(report)+"\n",encoding="utf-8")
print("\n".join(report))
