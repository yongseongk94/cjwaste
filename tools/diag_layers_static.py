from pathlib import Path
import re,json
text=Path('index.html').read_text(encoding='utf-8')
terms=['bundledPrecomputed','SERVICE_ZONE_CACHE_VERSION','loadBundled','precomputedRoutes','serviceZoneData','근거노선','추정권역','수거권역','v75-naedeok2-apartment-only']
out={}
for term in terms:
    pos=[]; s=0
    while True:
        i=text.find(term,s)
        if i<0: break
        pos.append(i); s=i+len(term)
    out[term]={'count':len(pos),'samples':[text[max(0,i-300):i+700] for i in pos[:4]]}
# bundled JSON summary
m=re.search(r'<script id="bundledPrecomputed" type="application/json">(.*?)</script>',text,re.S)
if m:
    try:
        obj=json.loads(m.group(1))
        out['bundled']={'version':obj.get('version'),'routes':len(obj.get('routes',[])),'general':len(obj.get('zones',{}).get('general',[])),'recycle':len(obj.get('zones',{}).get('recycle',[]))}
    except Exception as e: out['bundled']={'error':str(e)}
else: out['bundled']={'missing':True}
Path('tools/layers_static_report.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
