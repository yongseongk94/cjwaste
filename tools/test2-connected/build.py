"""Build explicit estimated service areas and road-network connections for TEST2.
Service geometry is preserved except verified expressway overlaps. Connections never certify collection addresses.
"""
import json,subprocess
from pathlib import Path
import networkx as nx
import numpy as np
from shapely.geometry import LineString,Point,shape
from shapely.ops import unary_union
from shapely.strtree import STRtree
from road_graph import ROOT,SCALE,xy,point,load_graph,scoped_graph,allowed,add_existing_public_roads
BUNDLE=ROOT/'cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json'
OUT=ROOT/'tools/test2-connected'
BASE=json.loads(subprocess.check_output(['git','show','a2b405a1f576875af6cfb265546e8f52098d8527:cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json']));BASE['version']='v76-test2-connected-v12';CTX=json.loads((OUT/'context.json').read_text())
G,POS,WAYS,BLOCKED=load_graph()
G,POS,WAYS=add_existing_public_roads(G,POS,WAYS,BLOCKED)
G,IDS,TREE,POLY,COMPONENTS=scoped_graph(G,POS,list(CTX['districts'].values()))
G=G.to_undirected()
print('GRAPH',len(G),G.number_of_edges(),flush=True)
blocked_lines=[LineString([(p['lon']*SCALE[0],p['lat']*SCALE[1]) for p in w['geometry']]) for w in BLOCKED]
BTREE=STRtree(blocked_lines)
USED_WAYS=set();REPORT=[]
APPROX={
 '도암리':{'center':[127.4693,36.7326],'radius':380,'village':'오창읍|도암리','basis':'도암길 49-2~64와 도암리 취락 주변 일반도로','sourceUrl':'http://place.map.kakao.com/17204747'},
 '장재문화마을':{'center':[127.562886,36.748285],'radius':350,'village':'북이면|장재리','basis':'장재마을회관·장재토성길 주변 취락도로를 문화마을 대체 범위로 추정','sourceUrl':'http://place.map.kakao.com/23985320'},
 '초정구길':{'center':[127.6050,36.7200],'radius':500,'road':'초정길','basis':'초정길·초정리 취락도로를 원본 초정구길의 대체 구간으로 추정','sourceUrl':'https://www.openstreetmap.org/way/658976440'},
 '3산업단지':{'center':[127.341896,36.731188],'radius':650,'basis':'오창제3산업단지 위치 주변 일반 진입도로와 공개 도로망 내부도로','sourceUrl':'http://place.map.kakao.com/27455429'},
 '증평IC':{'center':[127.5059,36.7713],'radius':400,'road':'여천3길','basis':'증평IC 바깥 여천3길·주변 사업장 접근도로. 고속도로와 진출입 램프 제외','sourceUrl':'http://place.map.kakao.com/10781507'}
}
# Use the exact observed hall URL rather than guessing the place identity.
for r in CTX['lookups']['북이면 장재리 마을회관']:
 if r['place_name']=='장재마을회관':APPROX['장재문화마을']['sourceUrl']=r['place_url']

def blocked_overlap(segment):
 line=LineString([xy(p) for p in segment]);bad=[]
 for i in BTREE.query(line.buffer(8)):
  overlap=line.intersection(blocked_lines[int(i)].buffer(8)).length
  if overlap>45:bad.append({'way':BLOCKED[int(i)]['id'],'name':BLOCKED[int(i)]['tags'].get('name',''),'overlapM':round(overlap,1)})
 return bad


def edge_segments(edges):
 """Merge road-edge chains; preserve every road vertex and junction."""
 graph=nx.Graph();graph.add_edges_from(edges);seen=set();out=[]
 for start in graph:
  if graph.degree(start)==2:continue
  for nxt in graph[start]:
   edge=frozenset((start,nxt))
   if edge in seen:continue
   path=[start,nxt];seen.add(edge);prev,cur=start,nxt
   while graph.degree(cur)==2:
    after=next(n for n in graph[cur] if n!=prev);e=frozenset((cur,after))
    if e in seen:break
    seen.add(e);path.append(after);prev,cur=cur,after
   out.append([point(POS[n]) for n in path])
 for a,b in graph.edges:
  e=frozenset((a,b))
  if e in seen:continue
  path=[a,b];seen.add(e);prev,cur=a,b
  while True:
   candidates=[n for n in graph[cur] if frozenset((cur,n)) not in seen]
   if not candidates:break
   n=candidates[0];seen.add(frozenset((cur,n)));path.append(n);prev,cur=cur,n
  out.append([point(POS[n]) for n in path])
 return out

def estimated(term,record):
 cfg=APPROX[term];center=np.array(cfg['center'])*SCALE;radius=cfg['radius'];scope=unary_union([shape(CTX['districts'][d]['geometry']) for d in record['districts']]).buffer(.000001)
 village=shape(CTX['villages'][cfg['village']]['geometry']) if cfg.get('village') else None
 edges=set()
 for u,v,data in G.edges(data=True):
  if data["way"]<0:continue  # Use one authoritative road geometry for estimated neighborhoods.
  mid=(POS[u]+POS[v])/2
  if np.linalg.norm(mid-center)>radius:continue
  ll=Point(*(mid/SCALE))
  if not all(scope.covers(Point(*(POS[n]/SCALE))) for n in [u,v]) or village is not None and not all(village.covers(Point(*(POS[n]/SCALE))) for n in [u,v]):continue
  tags=WAYS[data['way']]['tags']
  if tags['highway'].startswith(('trunk','primary')):continue
  if cfg.get('road') and tags.get('name')!=cfg['road'] and tags['highway'] not in {'residential','living_street','service','unclassified'}:continue
  edges.add((u,v))
 if not edges:raise ValueError('no estimated roads '+term)
 graph=nx.Graph();graph.add_edges_from(edges)
 component=min(nx.connected_components(graph),key=lambda c:min(np.linalg.norm(POS[n]-center) for n in c))
 edges=[e for e in edges if e[0] in component and e[1] in component]
 for a,b in edges:USED_WAYS.add(G.get_edge_data(a,b,G.get_edge_data(b,a))['way'])
 center_node=min(component,key=lambda n:np.linalg.norm(POS[n]-center))
 return edges,{'term':term,'status':'estimated','basis':cfg['basis'],'sourceUrl':cfg['sourceUrl'],'radiusM':radius,**point(POS[center_node]),'segmentCount':len(edge_segments(edges)),'source':'user-authorized-estimate','villageTerm':'도암리' if term=='도암리' else ''}

def attach(segment):
 coords=np.array([xy(p) for p in segment]);dist,idx=TREE.query(coords);j=int(np.argmin(dist));node=IDS[int(idx[j])];start=segment[j];target=point(POS[node]);distance=float(dist[j])
 if distance<=35:return node,[start,target],{'kind':'map-alignment','gapM':round(distance,2),'maxSeamM':round(distance,2)}
 raise ValueError('Offline attachment exceeds 35 m '+str(start)+' distance '+str(distance))

def remove_expressway_edges(segments):
 kept=[];removed=[]
 for si,seg in enumerate(segments):
  chain=[]
  for a,b in zip(seg,seg[1:]):
   av,bv=xy(a),xy(b);length=float(np.linalg.norm(bv-av));line=LineString([av,bv]);bad=None
   if length>.01:
    for i in BTREE.query(line.buffer(10)):
     other=blocked_lines[int(i)];overlap=line.intersection(other.buffer(10)).length
     pa=other.interpolate(other.project(Point(*av)));pb=other.interpolate(other.project(Point(*bv)));direction=np.array(pb.coords[0])-np.array(pa.coords[0]);norm=np.linalg.norm(direction)
     if overlap>min(35,length*.75) and norm>1 and abs(np.dot(direction,bv-av))/(norm*length)>.8:
      bad=BLOCKED[int(i)];break
   if bad:
    if len(chain)>1:kept.append(chain)
    chain=[];removed.append({'segment':si,'meters':round(length,2),'way':bad['id'],'tags':bad['tags']})
   else:
    if not chain:chain=[a]
    chain.append(b)
  if len(chain)>1:kept.append(chain)
 return kept,removed

for record in BASE['routes']:
 data=record['data'];label=record['vehicle']+' '+record['day'];print('ROUTE',label,flush=True)
 data['segments'],removed=remove_expressway_edges(data['segments'])
 print('REMOVED_EXPRESSWAY',round(sum(x['meters'] for x in removed)),len(removed),flush=True)
 data['estimatedServiceSegments']=[];data['estimatedTerms']=[];estimated_edges=[]
 for term in list(data['missingTerms']):
  if term not in APPROX:raise ValueError('unexpected unresolved '+term)
  edges,evidence=estimated(term,record);estimated_edges.extend(edges);data['estimatedServiceSegments'].extend(edge_segments(edges));data['estimatedTerms'].append(evidence)
  data['zoneEvidencePoints'].append({**evidence,'name':term+' 추정 기준점','district':next(d for d in record['districts'] if shape(CTX['districts'][d]['geometry']).covers(Point(evidence['lng'],evidence['lat'])))})
 data['missingTerms']=[];data['estimatedRoadTerms']=list(data.get('missingRoadTerms',[]));data['missingRoadTerms']=[]
 terminals=[];seams=[];attachments=[]
 for segment in data['segments']:
  node,seam,info=attach(segment);terminals.append(node);seams.append(seam);attachments.append(info)
 for a,b in estimated_edges:terminals.extend([a,b])
 spec=next(s for s in CTX['specs'] if s['type']==record['type'] and s['vehicle']==record['vehicle'] and s['day']==record['day'])
 ordered=[]
 for desc in spec['descriptors']:
  candidates=[p for p in data['zoneEvidencePoints'] if p.get('term')==desc['term']]
  if not candidates:continue
  # One representative per original term; local branches are attached separately below.
  preferred=next((p for p in candidates if 'verified' in p.get('source','') or 'village' in p.get('source','')),candidates[0])
  node=min(terminals,key=lambda n:np.linalg.norm(POS[n]-xy(preferred)))
  if not ordered or node!=ordered[-1]:ordered.append(node)
 if not ordered:ordered=[terminals[0]]
 edges=set(estimated_edges);core={ordered[0]};ordered_paths=[]
 for a,b in zip(ordered,ordered[1:]):
  path=nx.shortest_path(G,a,b,weight='weight');ordered_paths.append([point(POS[n]) for n in path]);edges.update(zip(path,path[1:]));core.update(path)
 _,paths=nx.multi_source_dijkstra(G,core,weight='weight')
 for terminal in set(terminals):
  path=paths[terminal];edges.update(zip(path,path[1:]));core.update(path)
 for a,b in edges:USED_WAYS.add(G.get_edge_data(a,b,G.get_edge_data(b,a))['way'])
 connections=edge_segments(edges)+[s for s in seams if np.linalg.norm(xy(s[0])-xy(s[-1]))>.02 or len(s)>2]
 data['distance']=round(sum(LineString([xy(p) for p in seg]).length for seg in data['segments']))
 data['pointsCount']=sum(map(len,data['segments']))
 record['audit'].update(segments=len(data['segments']),evidence=len(data['zoneEvidencePoints']))
 data['connectionSegments']=connections
 data['connectionVersion']='road-network-v1'
 data['connectionSource']={'name':'OpenStreetMap + existing published Kakao road geometry','url':'https://www.openstreetmap.org/copyright','license':'ODbL 1.0','retrievedAt':'2026-10-15','method':'undirected road-network display connections in source order; not turn-by-turn driving instructions','excluded':['motorway','motorway_link','motorroad=yes','trunk foot=no','expressway=yes','private/no motor access']}
 data['connectionWaypoints']=[point(POS[n]) for n in ordered]
 data['connectionDistance']=round(sum(LineString([xy(p) for p in s]).length for s in connections))
 graph=nx.Graph();graph.add_edges_from(edges)
 assert nx.is_connected(graph)
 data['connectionAudit']={'connected':True,'serviceSegmentsAttached':len(attachments),'allServiceSegments':len(data['segments']),'maxAlignmentM':max(a['maxSeamM'] for a in attachments),'navigationAccessSegments':sum(a['kind']=='kakao-driving' for a in attachments),'motorwayEdges':0,'graphComponents':1}
 record['audit'].update(missingTerms=[],missingRoadTerms=[],estimatedTerms=[p['term'] for p in data['estimatedTerms']],connectionAudit=data['connectionAudit'])
 REPORT.append({'vehicle':record['vehicle'],'day':record['day'],'type':record['type'],'estimatedTerms':data['estimatedTerms'],'connections':len(connections),'distanceM':data['connectionDistance'],'audit':data['connectionAudit'],'attachments':attachments,'removedExpresswayMeters':round(sum(x['meters'] for x in removed)), 'removedExpresswayWays':sorted(set(x['way'] for x in removed))})
 print('DONE',label,len(connections),data['connectionAudit'],flush=True)
 (OUT/'connected-bundle.json').write_text(json.dumps(BASE,ensure_ascii=False,separators=(',',':')))
 (OUT/'build-report.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2))
(OUT/'used-roads.json').write_text(json.dumps({'source':'https://overpass-api.de/api/interpreter','license':'ODbL 1.0 — © OpenStreetMap contributors','retrievedAt':'2026-10-15','query':'[out:json][timeout:45];way[highway](36.66,127.29,36.86,127.68);out geom;','ways':[WAYS[w] for w in sorted(USED_WAYS)]},ensure_ascii=False,separators=(',',':')))
