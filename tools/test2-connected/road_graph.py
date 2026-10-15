"""Offline road connections, excluding motorways and motor-vehicle-only roads."""
import json,math,gzip,subprocess
from pathlib import Path
import networkx as nx
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import shape,Point,LineString
from shapely.ops import unary_union
from shapely import contains_xy
ROOT=Path(__file__).resolve().parents[2]
SCALE=np.array([89000.,111000.])
ALLOWED={'trunk','trunk_link','primary','primary_link','secondary','secondary_link','tertiary','tertiary_link','unclassified','residential','living_street','service'}
def allowed(tags):
 access=tags.get('motor_vehicle',tags.get('vehicle',tags.get('access','yes')))
 return (tags.get('highway') in ALLOWED or (tags.get('highway')=='track' and tags.get('surface') in {'asphalt','concrete','paved'} and tags.get('tracktype','grade1')=='grade1')) and tags.get('expressway')!='yes' and tags.get('motorroad')!='yes' and not (tags.get('highway','').startswith('trunk') and tags.get('foot')=='no') and access not in {'no','private','agricultural','forestry','emergency'}
def xy(p):return np.array([p['lng'],p['lat']])*SCALE
def point(v):return {'lat':round(float(v[1]/SCALE[1]),8),'lng':round(float(v[0]/SCALE[0]),8)}
def load_graph():
 source=json.loads(gzip.decompress((ROOT/'tools/test2-connected/road-source.json.gz').read_bytes()));g=nx.DiGraph();positions={};ways={};blocked=[]
 for way in source['elements']:
  tags=way['tags']
  if not allowed(tags):
   if tags.get('highway') in {'motorway','motorway_link','trunk','trunk_link'} or tags.get('motorroad')=='yes':blocked.append(way)
   continue
  ways[way['id']]=way
  direction=tags.get('oneway','yes' if tags.get('junction')=='roundabout' else 'no')
  for i,(a,b) in enumerate(zip(way['geometry'],way['geometry'][1:])):
   av=np.array([a['lon'],a['lat']])*SCALE;bv=np.array([b['lon'],b['lat']])*SCALE;length=float(np.linalg.norm(bv-av))
   if length<.001:continue
   n=max(1,math.ceil(length/25));ids=[way['nodes'][i]]+[f"{way['id']}:{i}:{j}" for j in range(1,n)]+[way['nodes'][i+1]]
   for j,node in enumerate(ids):positions[node]=av+(bv-av)*j/n
   for u,v in zip(ids,ids[1:]):
    kwargs={'weight':length/n,'way':way['id']}
    if direction not in {'-1','reverse'}:g.add_edge(u,v,**kwargs)
    if direction not in {'yes','1','true'}:g.add_edge(v,u,**kwargs)
 return g,positions,ways,blocked

def scoped_graph(graph,positions,features):
 polygon=unary_union([shape(f['geometry']) for f in features]).buffer(.0005)
 ids=list(graph);coords=np.array([positions[n]/SCALE for n in ids]);mask=contains_xy(polygon,coords[:,0],coords[:,1]);nodes=[n for n,ok in zip(ids,mask) if ok]
 local=graph.subgraph(nodes).copy();components=list(nx.weakly_connected_components(local));components.sort(key=len,reverse=True)
 # Keep the connected public road network; facility dead ends are handled by existing service geometry.
 local=local.subgraph(components[0]).copy()
 ids=list(local);tree=cKDTree(np.array([positions[n] for n in ids]))
 return local,ids,tree,polygon,[(len(c)) for c in components[:8]]
if __name__=='__main__':
 g,pos,ways,blocked=load_graph();print('graph',len(g),g.number_of_edges(),'ways',len(ways),'blocked',len(blocked),flush=True)
 ctx=json.loads((ROOT/'tools/test2-connected/context.json').read_text());bundle=json.loads((ROOT/'cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json').read_text());cache={}
 for r in bundle['routes']:
  key=r['scopeSignature']
  if key not in cache:cache[key]=scoped_graph(g,pos,list(ctx['districts'].values()))
  local,ids,tree,poly,comps=cache[key];dist=[]
  for seg in r['data']['segments']:
   distances,index=tree.query(np.array([xy(p) for p in seg]));j=int(np.argmin(distances));dist.append(round(float(distances[j]),1))
  print(r['vehicle'],r['day'],'graph',len(local),'components',comps,'snap',max(dist),'>25',sum(d>25 for d in dist),'>80',sum(d>80 for d in dist),flush=True)

def add_existing_public_roads(graph,positions,ways,blocked):
 """Reuse published Kakao road geometry locally; remove highway-overlapping edges.
 No route coordinates are sent to any external endpoint.
 """
 from shapely.strtree import STRtree
 ids=list(graph);tree=cKDTree(np.array([positions[n] for n in ids]));blines=[LineString([(p['lon']*SCALE[0],p['lat']*SCALE[1]) for p in w['geometry']]) for w in blocked];btree=STRtree(blines)
 files=['cjwaste-test/data/precomputed-village-connected-v2.json','data/precomputed-routes-v76-layer-visibility-refresh-a1e5f19fa4da.json','cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json']
 count=0
 for file in files:
  bundle=json.loads(subprocess.check_output(['git','show','a2b405a1f576875af6cfb265546e8f52098d8527:'+file]))
  for r in bundle.get('routes',[]):
   if str(r.get('vehicle')) not in {'3344','6138','6544','0262'}:continue
   for seg in r['data'].get('travelSegments',[])+r['data'].get('segments',[]):
    wayid=-(count+1);count+=1;nodes=[];geometry=[]
    for p in seg:
     n=f"published:{round(p['lng'],7)}:{round(p['lat'],7)}";positions[n]=xy(p);nodes.append(n);geometry.append({'lat':p['lat'],'lon':p['lng']})
    ways[wayid]={'id':wayid,'tags':{'highway':'service','source':'published-kakao-road','sourceFile':file},'nodes':nodes,'geometry':geometry}
    for a,b in zip(nodes,nodes[1:]):
     av,bv=positions[a],positions[b];length=float(np.linalg.norm(bv-av))
     if length<.01:continue
     line=LineString([av,bv]);is_blocked=False
     for i in btree.query(line.buffer(10)):
      other=blines[int(i)];overlap=line.intersection(other.buffer(10)).length
      # A perpendicular crossing is permitted. Travel along a highway is not.
      if overlap>min(35,length*.75):
       pa=other.interpolate(other.project(Point(*av)));pb=other.interpolate(other.project(Point(*bv)))
       direction=np.array(pb.coords[0])-np.array(pa.coords[0]);norm=np.linalg.norm(direction)
       if norm>1 and abs(np.dot(direction,bv-av))/(norm*length)>.8:is_blocked=True;break
     if is_blocked:continue
     graph.add_edge(a,b,weight=length,way=wayid)
     # Published service geometry is a road reference, not turn-by-turn instructions.
     # Return direction is allowed only when the matched OSM road is not one-way.
     for n in [a,b]:
      dist,index=tree.query(positions[n]);osm=ids[int(index)]
      if dist<=20:
       graph.add_edge(n,osm,weight=max(.01,float(dist)),way=wayid)
       graph.add_edge(osm,n,weight=max(.01,float(dist)),way=wayid)
 return graph,positions,ways
