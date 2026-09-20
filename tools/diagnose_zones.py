from pathlib import Path
import re
s=Path("index.html").read_text(encoding="utf-8")
terms=["SERVICE_ZONE_CACHE_VERSION","serviceZone","zoneCache","hydrateBundledPrecomputedData","ensureService","buildService","inferred","추정"]
for t in terms:
 print("\n###",t)
 for m in list(re.finditer(re.escape(t),s,re.I))[:30]:
  a=max(0,m.start()-500); b=min(len(s),m.end()+900)
  print(s[a:b].replace("\n"," ")[:1600])
