import json
from pathlib import Path
from shapely.geometry import LineString
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[2]
b=json.loads((ROOT/'cjwaste-test2/data/precomputed-routes-contractor-groups-v1.json').read_text())
rows=[]
for r in b['routes']:
 if not r['vehicle'].startswith('현대환경|') or r['day'] not in ['화','목']:continue
 d=b['geometryPool'][r['dataRef']];lines=[LineString([(p['lng']*89000,p['lat']*111000) for p in s]) for k in ['segments','estimatedServiceSegments','connectionSegments'] for s in d[k]]
 geom=unary_union([l.buffer(.5) for l in lines]);components=len(geom.geoms) if geom.geom_type=='MultiPolygon' else 1
 anchors={p['name'] for p in d['zoneEvidencePoints']}
 rows.append({'type':r['type'],'day':r['day'],'components':components,'anchors':sorted(anchors),'ok':components==1 and len(anchors)==7})
report={'rows':rows,'ok':len(rows)==4 and all(r['ok'] for r in rows)}
(ROOT/'tools/test2-contractors/geometry-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False));assert report['ok']
