from pathlib import Path
import re
p=Path('index.html')
t=p.read_text(encoding='utf-8')
old="const exactAddr=normalizeRouteAddress('공항로84번길 30');\n      const exactName=normalizeRouteAddress('이랜드해가든');"
new="const exactAddr=contractAddressNorm('공항로84번길 30');\n      const exactName=contractAddressNorm('이랜드해가든');"
if old not in t:
    raise SystemExit('v75 normalizer bug pattern not found')
t=t.replace(old,new,1)
if "normalizeRouteAddress('공항로84번길 30')" in t:
    raise SystemExit('stale normalizer call remains')
p.write_text(t,encoding='utf-8')
