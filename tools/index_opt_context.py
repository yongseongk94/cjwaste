from pathlib import Path
import re
s=Path("index.html").read_text(encoding="utf-8")
terms=[
 "bundledPrecomputed","BUNDLED","precomputed","DONG_ROUTE_CACHE_VERSION",
 "indexedDB","openRouteDb","hydrate","routeCache","SERVICE_ZONE_CACHE_VERSION"
]
out=[]
for term in terms:
    out.append(f"===== {term} =====")
    for i,m in enumerate(re.finditer(re.escape(term),s,re.I),1):
        a=max(0,m.start()-700); b=min(len(s),m.end()+1300)
        sn=s[a:b].replace("\r","")
        line=s.count("\n",0,m.start())+1
        out.append(f"--- occurrence {i} line {line} ---")
        out.append(sn)
        if i>=12: break
Path("tools/index-opt-context-report.txt").write_text("\n".join(out),encoding="utf-8")
