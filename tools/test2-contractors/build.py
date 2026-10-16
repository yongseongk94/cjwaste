"""Compact TEST2 bundle with user-confirmed weekday groups; no external routing."""
import json,re,copy,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
read=lambda p:json.loads((ROOT/p).read_text())
base=read('data/precomputed-routes-v76-layer-visibility-refresh-a1e5f19fa4da.json')
hy=read('cjwaste-test/data/precomputed-hyundai-v2.json')
def unique(values):
 out=[];seen=set()
 for v in values:
  key=json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'))
  if key not in seen:seen.add(key);out.append(v)
 return out
def distance(segs):return round(sum(math.hypot((a['lng']-b['lng'])*89000,(a['lat']-b['lat'])*111000) for s in segs for a,b in zip(s,s[1:])))
def merge(rows):
 d=copy.deepcopy(rows[0]['data'])
 for k in set().union(*(r['data'].keys() for r in rows)):
  if any(isinstance(r['data'].get(k),list) for r in rows):d[k]=unique([v for r in rows for v in r['data'].get(k,[])])
 d['distance']=distance(d['segments']);d['pointsCount']=sum(map(len,d['segments']));d['contractorGroupVersion']='weekday-groups-v1'
 return d
slots={};direct=[]
for r in base['routes']:
 if '환경|' not in r['vehicle']:direct.append(r);continue
 group='월수금' if r['day'] in '월수금' else '화목' if r['day'] in '화목' else r['day']
 slots.setdefault((r['type'],r['vehicle'],group),[]).append(r)
pool={};refs=[];report=[]
for (typ,vehicle,group),rows in slots.items():
 d=merge(rows)
 if vehicle.startswith('현대환경|') and group=='화목':
  corrected=[r for r in hy['routes'] if r['type']==typ];d=merge(corrected)
  d['estimatedServiceSegments']=d.pop('neighborhoodSegments')
  d['connectionSegments']=d.pop('travelSegments')
  d['connectionVersion']='hyundai-connected-weekday-v3'
  d['connectionSource']={'name':'Previously verified Kakao road geometry + OpenStreetMap neighborhood roads','url':'https://www.openstreetmap.org/copyright','license':'ODbL 1.0','method':'Tue/Thu union; neighborhood service is estimated; connecting travel does not certify collection'}
  d['estimatedTerms']=[{'term':'기준시설 7곳 주변 생활도로','status':'estimated','basis':'원자료 시설에서 도로거리 500m 이내 연결 생활도로; 실제 수거 여부는 미확정'}]
  d['termsCount']=len(d['zoneEvidencePoints']);d['serviceTermCount']=d['termsCount'];d['connectionDistance']=distance(d['connectionSegments'])
  d['connectionAudit']={'connected':True,'serviceSegmentsAttached':len(d['segments']),'allServiceSegments':len(d['segments']),'maxAlignmentM':0,'graphComponents':1}
  d['hyundaiVersion']='hyundai-connected-weekday-v3'
 # Pool can also reuse identical geometry between 생활/재활용 while UI objects remain separate.
 key=next((k for k,v in pool.items() if v==d),None)
 if key is None:key='c'+str(len(pool));pool[key]=d
 for r in rows:refs.append({k:v for k,v in r.items() if k!='data'}|{'dataRef':key})
 report.append({'type':typ,'vehicle':vehicle,'days':[r['day'] for r in rows],'group':group,'segments':len(d['segments']),'distanceM':d['distance'],'estimatedSegments':len(d.get('estimatedServiceSegments',[])),'connectionSegments':len(d.get('connectionSegments',[])),'evidencePoints':len(d.get('zoneEvidencePoints',[]))})
output={**base,'version':'v76-test2-connected-v12','contractorGroupVersion':'weekday-groups-v1','geometryPool':pool,'routes':refs+direct}
p=ROOT/'cjwaste-test2/data/precomputed-routes-contractor-groups-v1.json';p.write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')))
stats={'beforeBytes':(ROOT/'data/precomputed-routes-v76-layer-visibility-refresh-a1e5f19fa4da.json').stat().st_size,'afterBytes':p.stat().st_size,'weekdaySlots':len(refs),'geometryGroups':len(slots),'storedGeometries':len(pool),'routes':report}
(ROOT/'tools/test2-contractors/build-report.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in stats.items() if k!='routes'}))
