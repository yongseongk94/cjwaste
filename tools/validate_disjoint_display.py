import json,sys
from shapely.geometry import shape,Polygon,box
from shapely.ops import unary_union
features=[f for f in json.load(open(sys.argv[1]))['features'] if '청원구' in f['properties'].get('sggnm','')]
area=unary_union([shape(f['geometry']) for f in features])
data=json.load(open(sys.argv[2]));outputs=data['viewports']
max_overlap=max_gap=max_outside=0
for case in outputs:
 polys=[Polygon([(p['lng'],p['lat']) for p in z['rings'][0]], [[(p['lng'],p['lat']) for p in r] for r in z['rings'][1:]]) for z in case['zones']]
 assert all(p.is_valid for p in polys)
 union=unary_union(polys)
 e=case['extent'];target=area.intersection(box(e['minLng'],e['minLat'],e['maxLng'],e['maxLat']))
 overlap=max(0,sum(p.area for p in polys)-union.area)
 gap=target.difference(union).area
 outside=union.difference(area).area
 max_overlap=max(max_overlap,overlap);max_gap=max(max_gap,gap);max_outside=max(max_outside,outside)
 assert overlap<1e-12,(case['type'],case['sample'],'overlap',overlap)
 assert gap<1e-12,(case['type'],case['sample'],'gap',gap)
 assert outside<1e-12,(case['type'],case['sample'],'outside',outside)
print(json.dumps({'viewports':len(outputs),'polygons':sum(len(c['zones']) for c in outputs),'max_overlap_deg2':max_overlap,'max_gap_deg2':max_gap,'max_outside_deg2':max_outside}))

for case in data['scenarios']:
 def polys(zones):
  return [Polygon([(p['lng'],p['lat']) for p in z['rings'][0]], [[(p['lng'],p['lat']) for p in r] for r in z['rings'][1:]]) for z in zones]
 expected=unary_union(polys(case['expected']))
 actual_polys=polys(case['actual']);actual=unary_union(actual_polys)
 assert all(p.is_valid for p in actual_polys),case['label']
 assert abs(sum(p.area for p in actual_polys)-actual.area)<1e-12,(case['label'],'overlap')
 assert expected.symmetric_difference(actual).area<1e-12,(case['label'],'changed footprint')
print('PASS',len(data['scenarios']),'filter/manual scenarios')
