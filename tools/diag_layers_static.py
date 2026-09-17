from pathlib import Path
import re,json
text=Path('index.html').read_text(encoding='utf-8')
terms=['bundledPrecomputed','SERVICE_ZONE_CACHE_VERSION','근거노선','추정권역','수거권역','v75-naedeok2-apartment-only']
out={'counts':{t:text.count(t) for t in terms}}
m=re.search(r'<script id="bundledPrecomputed" type="application/json">(.*?)</script>',text,re.S)
if m:
    try:
        obj=json.loads(m.group(1))
        out['bundled']={'version':obj.get('version'),'zoneVersion':obj.get('zoneVersion'),'routes':len(obj.get('routes',[])),'general':len(obj.get('zones',{}).get('general',[])),'recycle':len(obj.get('zones',{}).get('recycle',[]))}
    except Exception as e: out['bundled']={'error':str(e)}
else: out['bundled']={'missing':True}
for name in ['DONG_ROUTE_CACHE_VERSION','SERVICE_ZONE_CACHE_VERSION']:
    mm=re.search(rf'const {name}=(.*?);',text)
    out[name]=mm.group(1) if mm else None
for term in ['hydrateBundledPrecomputedData()','syncServiceZoneVisibility(','syncRouteVisibility(','setMap(null)','serviceZoneLayerEnabled','routeLayerEnabled']:
    occ=[]; s=0
    while True:
        i=text.find(term,s)
        if i<0: break
        occ.append(text[max(0,i-500):i+1200]); s=i+len(term)
    out[term]={'count':len(occ),'contexts':occ[:12]}
Path('tools/layers_static_report.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
