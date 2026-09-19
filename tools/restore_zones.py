from pathlib import Path
p=Path('index.html')
s=p.read_text(encoding='utf-8')
old="const SERVICE_ZONE_CACHE_VERSION=`zone-v78-rural-estimated-regions-fix|${DONG_ROUTE_CACHE_VERSION}`;"
new="const SERVICE_ZONE_CACHE_VERSION=`zone-v76-layer-visibility-refresh|${DONG_ROUTE_CACHE_VERSION}`;"
assert old in s, 'marker missing'
p.write_text(s.replace(old,new,1),encoding='utf-8')