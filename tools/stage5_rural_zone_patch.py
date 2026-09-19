from pathlib import Path

p = Path("index.html")
s = p.read_text(encoding="utf-8")

old = "const SERVICE_ZONE_CACHE_VERSION=`zone-v76-layer-visibility-refresh|${DONG_ROUTE_CACHE_VERSION}`;"
new = "const SERVICE_ZONE_CACHE_VERSION=`zone-v77-rural-estimated-regions|${DONG_ROUTE_CACHE_VERSION}`;"

if old not in s:
    raise SystemExit("old SERVICE_ZONE_CACHE_VERSION marker not found")

s = s.replace(old, new, 1)

# Keep the bundled v76 zoneVersion unchanged on purpose.
# The mismatch forces the old embedded/cached service-zone polygons to be skipped,
# so Ochang/Naesu/Bugi estimated regions are rebuilt from the Stage 3 route logic
# and then saved under the new zone cache version.
p.write_text(s, encoding="utf-8")

print("STAGE5_RURAL_ZONE_CACHE_BUMP_OK")
