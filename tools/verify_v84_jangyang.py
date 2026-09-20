import json
from collections import Counter, defaultdict
from pathlib import Path

out={}
for t in ['general','recycle']:
    d=json.loads(Path(f'data/service-zones-v84-{t}-all.json').read_text(encoding='utf-8'))
    north=[z for z in d.get('zones',[]) if z.get('district')=='북이면']
    ri=Counter(str(z.get('riName') or '') for z in north)
    vehicle_days=Counter((str(z.get('vehicle') or ''),tuple(z.get('days') or []),str(z.get('riName') or '')) for z in north)
    out[t]={
        'northTotal':len(north),
        'riCounts':dict(sorted(ri.items())),
        '6138or6544':[
            {'vehicle':k[0],'days':list(k[1]),'riName':k[2],'count':v}
            for k,v in vehicle_days.items() if k[0] in {'6138','6544'}
        ]
    }
Path('tools/v84-jangyang-validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
