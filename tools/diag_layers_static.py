from pathlib import Path
import re,json
text=Path('index.html').read_text(encoding='utf-8')
out={}
for pat,name in [
 (r'function\s+setRouteItemMap\([^)]*\)\{[\s\S]{0,2500}','setRouteItemMap'),
 (r'function\s+createDongRouteOverlay\([^)]*\)\{[\s\S]{0,5000}','createDongRouteOverlay'),
 (r'function\s+addServiceZonePolygon\([^)]*\)\{[\s\S]{0,5000}','addServiceZonePolygon'),
 (r'function\s+syncServiceZoneVisibility\([^)]*\)\{[\s\S]{0,5000}','syncServiceZoneVisibility')]:
    mm=re.search(pat,text)
    out[name]=mm.group(0)[:5000] if mm else None
Path('tools/layers_static_report.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
