from pathlib import Path
import json,re
from collections import defaultdict
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.geometry.polygon import orient

p=Path('index.html')
s=p.read_text(encoding='utf-8')
m=re.search(r'(<script id="bundledPrecomputed" type="application/json">)(.*?)(</script>)',s,re.S)
if not m: raise SystemExit('bundledPrecomputed missing')
data=json.loads(m.group(2))

RURAL={'내수읍','오창읍','북이면'}
SPECIAL=('sourceOnly','riGrouped','contractLayer','routeBuffer','noSchedule','groupOutline')

def can_polygonize(z):
    return bool(z.get('automatic') and z.get('gridMerged') and z.get('groupKey') and z.get('district') not in RURAL and not any(z.get(k) for k in SPECIAL) and len(z.get('points') or [])>=3)

def signature(z):
    certainty='E' if z.get('estimated') else ('A' if z.get('ambiguous') else 'C')
    return (z.get('district',''),z.get('riName',''),z.get('groupKey',''),z.get('vehicle',''),z.get('provider',''),tuple(z.get('days') or []),certainty)

def zone_poly(z):
    pts=z.get('hitRings') or z.get('rings') or [z.get('points') or []]
    outer=pts[0] if pts else []
    holes=pts[1:] if len(pts)>1 else []
    if len(outer)<3:return None
    try:
        poly=Polygon([(float(q['lng']),float(q['lat'])) for q in outer], [[(float(q['lng']),float(q['lat'])) for q in h] for h in holes if len(h)>=3])
        if not poly.is_valid: poly=poly.buffer(0)
        return poly if not poly.is_empty else None
    except Exception:
        return None

def ring(coords):
    arr=list(coords)
    if len(arr)>1 and arr[0]==arr[-1]:arr=arr[:-1]
    return [{'lat':round(float(y),9),'lng':round(float(x),9)} for x,y in arr]

def rings_of(poly):
    poly=orient(poly,sign=1.0)
    return [ring(poly.exterior.coords)]+[ring(r.coords) for r in poly.interiors]

def split_polys(g):
    if g.geom_type=='Polygon':return [g]
    if g.geom_type=='MultiPolygon':return list(g.geoms)
    return [x for x in getattr(g,'geoms',[]) if x.geom_type=='Polygon']

def polygonize(zones):
    fixed=[];groups=defaultdict(list)
    for z in zones:
        if can_polygonize(z):
            poly=zone_poly(z)
            if poly is not None:groups[signature(z)].append((z,poly));continue
        fixed.append(z)
    output=list(fixed)
    stats={'input':len(zones),'candidates':sum(len(v) for v in groups.values()),'components':0,'polygonized':0}
    for sig,items in groups.items():
        merged=unary_union([poly for _,poly in items])
        for component in split_polys(merged):
            if component.is_empty or component.area<=0:continue
            touching=[(z,poly) for z,poly in items if component.intersection(poly).area>1e-14]
            src=(touching or items)[0][0]
            exact=rings_of(component)
            # Visual-only simplification removes the obvious box-grid feel. Exact hitRings stay untouched.
            display_geom=component.simplify(0.00010,preserve_topology=True)
            if display_geom.geom_type!='Polygon' or display_geom.is_empty:display_geom=component
            display=rings_of(display_geom)
            z=dict(src)
            z['points']=exact[0]
            z['hitRings']=exact
            z['rings']=display
            z['gridMerged']=True
            z['polygonized']=True
            support=sum(float(a.get('neighborSupport') or 0) for a,_ in touching)
            total=sum(float(a.get('neighborTotal') or 0) for a,_ in touching)
            z['neighborSupport']=support
            z['neighborTotal']=total
            if z.get('estimated') and total:z['neighborRatio']=support/total
            output.append(z)
            stats['components']+=1;stats['polygonized']+=1
    return output,stats

summary={}
for typ in ('general','recycle'):
    new,st=polygonize(data.get('zones',{}).get(typ) or [])
    data['zones'][typ]=new
    summary[typ]=st|{'output':len(new)}

version=data.get('version','')
data['zoneVersion']='zone-v70-dong-polygons-persist|'+version
new_json=json.dumps(data,ensure_ascii=False,separators=(',',':'))
s=s[:m.start(2)]+new_json+s[m.end(2):]
p.write_text(s,encoding='utf-8')
print('DONG_POLYGONIZE',json.dumps(summary,ensure_ascii=False))
