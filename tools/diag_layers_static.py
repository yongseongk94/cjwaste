from pathlib import Path
import re,json
text=Path('index.html').read_text(encoding='utf-8')
out={}
m=re.search(r'<script id="bundledPrecomputed" type="application/json">(.*?)</script>',text,re.S)
if m:
    obj=json.loads(m.group(1)); out['bundled']={'version':obj.get('version'),'zoneVersion':obj.get('zoneVersion'),'routes':len(obj.get('routes',[])),'general':len(obj.get('zones',{}).get('general',[])),'recycle':len(obj.get('zones',{}).get('recycle',[]))}
for pat,name in [
 (r'(?:const|let|var)\s+serviceLayerState\s*=\s*([^;]+);','serviceLayerState'),
 (r'(?:const|let|var)\s+activeLayer\s*=\s*([^;]+);','activeLayer'),
 (r'id="structureControl"[\s\S]{0,2500}','structureControl'),
 (r'function\s+setLayer\([^)]*\)\{[\s\S]{0,6000}','setLayer'),
 (r'function\s+syncDongRouteVisibility\([^)]*\)\{[\s\S]{0,5000}','syncDongRouteVisibility')]:
    mm=re.search(pat,text)
    out[name]=mm.group(0 if name in ['structureControl','setLayer','syncDongRouteVisibility'] else 1)[:6000] if mm else None
Path('tools/layers_static_report.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
