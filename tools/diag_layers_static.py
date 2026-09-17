from pathlib import Path
import re,json
text=Path('index.html').read_text(encoding='utf-8')
terms=['bundledPrecomputed','SERVICE_ZONE_CACHE_VERSION','근거노선','추정권역','수거권역','v75-naedeok2-apartment-only']
out={'counts':{t:text.count(t) for t in terms}}
m=re.search(r'<script id="bundledPrecomputed" type="application/json">(.*?)</script>',text,re.S)
if m:
    try:
        obj=json.loads(m.group(1))
        out['bundled']={
          'version':obj.get('version'),'zoneVersion':obj.get('zoneVersion'),
          'routes':len(obj.get('routes',[])),'general':len(obj.get('zones',{}).get('general',[])),'recycle':len(obj.get('zones',{}).get('recycle',[])),
          'sampleRouteKeys':['|'.join([str(r.get('type')),str(r.get('vehicle')),str(r.get('day'))]) for r in obj.get('routes',[])[:8]]
        }
    except Exception as e: out['bundled']={'error':str(e)}
else: out['bundled']={'missing':True}
# Extract current cache constants
for name in ['DONG_ROUTE_CACHE_VERSION','SERVICE_ZONE_CACHE_VERSION']:
    mm=re.search(rf'const {name}=(.*?);',text)
    out[name]=mm.group(1) if mm else None
# Hydrator conditions
hm=re.search(r'function hydrateBundledPrecomputedData\(\)\{(.*?)\n\}',text,re.S)
out['hydrator']=hm.group(1)[:5000] if hm else None
Path('tools/layers_static_report.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
