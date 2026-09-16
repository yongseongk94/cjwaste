from pathlib import Path
import json,re,math

p=Path('index.html')
s=p.read_text(encoding='utf-8')
m=re.search(r'(<script id="bundledPrecomputed" type="application/json">)(.*?)(</script>)',s,re.S)
if not m:
    raise SystemExit('bundledPrecomputed not found')
data=json.loads(m.group(2))

SPECIAL_FLAGS=('sourceOnly','riGrouped','contractLayer','routeBuffer','noSchedule','groupOutline')

def rect_bounds(z):
    pts=z.get('points') or []
    if len(pts)!=4:return None
    lats=[float(q.get('lat',0)) for q in pts]
    lngs=[float(q.get('lng',0)) for q in pts]
    lo,hi=min(lngs),max(lngs); bot,top=min(lats),max(lats)
    eps=1e-9
    # Four axis-aligned corners only.
    expected={(round(bot,9),round(lo,9)),(round(bot,9),round(hi,9)),(round(top,9),round(hi,9)),(round(top,9),round(lo,9))}
    actual={(round(float(q['lat']),9),round(float(q['lng']),9)) for q in pts}
    if actual!=expected:return None
    return lo,hi,bot,top

def mergeable(z):
    if not z.get('automatic'):return False
    if any(z.get(k) for k in SPECIAL_FLAGS):return False
    if not z.get('groupKey'):return False
    return rect_bounds(z) is not None

def sig(z):
    certainty='E' if z.get('estimated') else ('A' if z.get('ambiguous') else 'C')
    return (
        z.get('district',''),z.get('riName',''),z.get('groupKey',''),
        z.get('vehicle',''),z.get('provider',''),tuple(z.get('days') or []),certainty
    )

def merge_zone_list(zones):
    fixed=[]; groups={}
    for z in zones:
        if not mergeable(z):
            fixed.append(z);continue
        b=rect_bounds(z)
        key=sig(z)+(round(b[0],9),round(b[1],9))
        groups.setdefault(key,[]).append((b,z))
    merged=[]
    for key,items in groups.items():
        items.sort(key=lambda t:(t[0][2],t[0][3]))
        cur=None
        for b,z in items:
            lo,hi,bot,top=b
            if cur is not None and abs(cur['_top']-bot)<=2e-8:
                cur['_top']=top
                cur['neighborSupport']=float(cur.get('neighborSupport') or 0)+float(z.get('neighborSupport') or 0)
                cur['neighborTotal']=float(cur.get('neighborTotal') or 0)+float(z.get('neighborTotal') or 0)
                if cur.get('estimated') and cur['neighborTotal']:
                    cur['neighborRatio']=cur['neighborSupport']/cur['neighborTotal']
            else:
                if cur is not None: merged.append(cur)
                cur=dict(z)
                cur['_lo']=lo;cur['_hi']=hi;cur['_bot']=bot;cur['_top']=top
                cur['gridMerged']=True
        if cur is not None:merged.append(cur)
    for z in merged:
        lo,hi,bot,top=z.pop('_lo'),z.pop('_hi'),z.pop('_bot'),z.pop('_top')
        z['points']=[{'lat':bot,'lng':lo},{'lat':bot,'lng':hi},{'lat':top,'lng':hi},{'lat':top,'lng':lo}]
    return fixed+merged

before={}
after={}
for typ in ('general','recycle'):
    zones=data.get('zones',{}).get(typ) or []
    before[typ]=len(zones)
    data['zones'][typ]=merge_zone_list(zones)
    after[typ]=len(data['zones'][typ])

version=data.get('version','')
data['zoneVersion']='zone-v69-merged-grid-blocks|'+version
new_json=json.dumps(data,ensure_ascii=False,separators=(',',':'))
s=s[:m.start(2)]+new_json+s[m.end(2):]
p.write_text(s,encoding='utf-8')
print('BUNDLED_ZONE_MERGE',json.dumps({'before':before,'after':after},ensure_ascii=False))
