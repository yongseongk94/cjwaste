"""Validate output geometry independently of builder connectivity metadata."""
import json
from pathlib import Path
from shapely.geometry import LineString
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[2]
bundle=json.loads((ROOT/'cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json').read_text())
rows=[]
for r in bundle['routes']:
 d=r['data'];groups={k:[LineString([(p['lng']*89000,p['lat']*111000) for p in s]) for s in d[k] if len(s)>1] for k in ['segments','estimatedServiceSegments','connectionSegments']}
 lines=sum(groups.values(),[])
 # Sub-metre rounding tolerance, far below the 20m address-certification threshold.
 area=unary_union([line.buffer(.5) for line in lines]);components=len(area.geoms) if area.geom_type=='MultiPolygon' else 1
 connections=unary_union(groups['connectionSegments'])
 gaps=[line.distance(connections) for line in groups['segments']+groups['estimatedServiceSegments']]
 row={'vehicle':r['vehicle'],'day':r['day'],'geometryComponents':components,'maxServiceToConnectionGapM':round(max(gaps),3),'estimatedServiceMeters':round(sum(x.length for x in groups['estimatedServiceSegments'])),'ok':components==1 and max(gaps)<1}
 rows.append(row)
report={'toleranceM':.5,'all20Connected':len(rows)==20 and all(r['ok'] for r in rows),'rows':rows}
(ROOT/'tools/test2-connected/geometry-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2));assert report['all20Connected']
