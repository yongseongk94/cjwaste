from pathlib import Path
from shapely.geometry import LineString, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union
import json,re,datetime,math

p=Path('index.html')
s=p.read_text(encoding='utf-8')
m=re.search(r'(<script id="bundledPrecomputed" type="application/json">)(.*?)(</script>)',s,re.S)
if not m: raise SystemExit('bundledPrecomputed not found')
data=json.loads(m.group(2))

DONGS={'우암동','내덕1동','내덕2동','오근장동','율량사천동'}
TYPES=('general','recycle')
KM_X=88.0
KM_Y=111.0
BUFFER_KM=0.020

def xy(p): return (float(p['lng'])*KM_X,float(p['lat'])*KM_Y)
def ll(x,y): return {'lat':y/KM_Y,'lng':x/KM_X}

def zone_geom(z):
    rings=z.get('hitRings') or z.get('rings') or [z.get('points') or []]
    rings=[r for r in rings if isinstance(r,list) and len(r)>=3]
    if not rings:return None
    try:
        g=Polygon([xy(q) for q in rings[0]], [[xy(q) for q in r] for r in rings[1:]])
        if not g.is_valid:g=g.buffer(0)
        return g if not g.is_empty else None
    except Exception:
        return None

def poly_parts(g):
    if g is None or g.is_empty:return []
    if isinstance(g,Polygon):return [g]
    if isinstance(g,MultiPolygon):return list(g.geoms)
    if isinstance(g,GeometryCollection):
        out=[]
        for q in g.geoms:out.extend(poly_parts(q))
        return out
    return []

def poly_to_zone(base,poly,part_idx):
    # 1m simplification removes tiny staircase noise but preserves holes/topology.
    poly=poly.simplify(0.001,preserve_topology=True)
    if not isinstance(poly,Polygon) or poly.is_empty:return None
    ext=list(poly.exterior.coords)
    if len(ext)>1 and ext[0]==ext[-1]:ext=ext[:-1]
    if len(ext)<3:return None
    rings=[]
    outer=[ll(x,y) for x,y in ext]
    rings.append(outer)
    for interior in poly.interiors:
        rr=list(interior.coords)
        if len(rr)>1 and rr[0]==rr[-1]:rr=rr[:-1]
        if len(rr)>=3:rings.append([ll(x,y) for x,y in rr])
    z=dict(base)
    z['points']=outer
    z['rings']=rings
    z['hitRings']=rings
    z['estimated']=True
    z['ambiguous']=False
    z['polygonized']=True
    z['gridMerged']=False
    z['sourceOnly']=False
    z['estimateReason']='outside-confirmed-route'
    z['confirmedRouteExcluded']=True
    z['groupKey']=f"{base.get('groupKey','')}|v71e{part_idx}"
    return z

# Build exact displayed-route corridors from the bundled route geometry already shipped with the page.
route_lines={t:[] for t in TYPES}
for r in data.get('routes',[]):
    typ=r.get('type')
    if typ not in route_lines:continue
    for seg in (r.get('data') or {}).get('segments') or []:
        pts=[xy(q) for q in seg if isinstance(q,dict) and math.isfinite(float(q.get('lat',0))) and math.isfinite(float(q.get('lng',0)))]
        if len(pts)>=2:
            try: route_lines[typ].append(LineString(pts))
            except Exception: pass
route_buffers={t:(unary_union(route_lines[t]).buffer(BUFFER_KM,cap_style=1,join_style=1) if route_lines[t] else None) for t in TYPES}

stats={}
for typ in TYPES:
    old=list((data.get('zones') or {}).get(typ) or [])
    new=[]
    dong_input=0; dong_output=0; removed_empty=0
    before_area=0.0; after_area=0.0; overlap_after=0.0
    routebuf=route_buffers[typ]
    for z in old:
        district=str(z.get('district') or '')
        # Keep 읍·면, contractor and special non-dong structures unchanged.
        if district not in DONGS or z.get('manual') or z.get('routeBuffer'):
            new.append(z);continue
        g=zone_geom(z)
        if g is None:
            continue
        dong_input+=1;before_area+=g.area
        diff=g.difference(routebuf) if routebuf is not None else g
        if not diff.is_valid:diff=diff.buffer(0)
        parts=[q for q in poly_parts(diff) if q.area>=0.000003]
        if not parts:
            removed_empty+=1;continue
        for i,q in enumerate(parts):
            zz=poly_to_zone(z,q,i)
            if not zz:continue
            new.append(zz);dong_output+=1;after_area+=q.area
            if routebuf is not None:overlap_after+=q.intersection(routebuf).area
    data['zones'][typ]=new
    stats[typ]={
        'all_before':len(old),'all_after':len(new),'dong_input':dong_input,'dong_output':dong_output,
        'removed_empty':removed_empty,'dong_area_before_km2':round(before_area,4),'dong_area_after_km2':round(after_area,4),
        'excluded_confirmed_corridor_km2':round(max(0,before_area-after_area),4),'post_overlap_km2':round(overlap_after,8)
    }
    if overlap_after>1e-7: raise SystemExit(f'{typ}: inferred zones still overlap confirmed route buffer: {overlap_after}')
    bad=[z for z in new if str(z.get('district') or '') in DONGS and not z.get('estimated')]
    if bad: raise SystemExit(f'{typ}: non-estimated dong zones remain: {len(bad)}')

version=data.get('version','')
data['zoneVersion']='zone-v71-confirmed-route-excluded|'+version
data['generatedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
data['v71ConfirmedRouteExclusion']={'bufferMeters':20,'stats':stats}
new_json=json.dumps(data,ensure_ascii=False,separators=(',',':'))
s=s[:m.start(2)]+new_json+s[m.end(2):]
p.write_text(s,encoding='utf-8')
print('V71_CONFIRMED_ROUTE_EXCLUSION',json.dumps(stats,ensure_ascii=False))
