import json
from pathlib import Path

expected='zone-v84-latest-route-evidence|v76-layer-visibility-refresh'
targets={
    'general':('6138','수'),
    'recycle':('6544','수'),
}
out={}
for t,(vehicle,day) in targets.items():
    p=Path(f'data/service-zones-v84-{t}-all.json')
    d=json.loads(p.read_text(encoding='utf-8'))
    if d.get('zoneVersion')!=expected:
        raise SystemExit(f'{t}: wrong zoneVersion {d.get("zoneVersion")}')
    zs=[z for z in d.get('zones',[]) if z.get('district')=='북이면' and z.get('riName')=='장양리']
    if not zs:
        raise SystemExit(f'{t}: no Jangyang zones')
    matching=[z for z in zs if str(z.get('vehicle'))==vehicle and day in (z.get('days') or [])]
    if not matching:
        raise SystemExit(f'{t}: no {vehicle}/{day} Jangyang zones')
    if not any(z.get('estimated') for z in matching):
        raise SystemExit(f'{t}: no estimated {vehicle}/{day} zones')
    if not any(z.get('gridMerged') for z in matching):
        raise SystemExit(f'{t}: no gridMerged {vehicle}/{day} zones')
    if all(z.get('riGrouped') for z in matching):
        raise SystemExit(f'{t}: still riGrouped')
    if all(z.get('noSchedule') for z in matching):
        raise SystemExit(f'{t}: still noSchedule')
    out[t]={
        'jangyangTotal':len(zs),
        'matchingCount':len(matching),
        'vehicle':vehicle,
        'day':day,
        'estimatedCount':sum(bool(z.get('estimated')) for z in matching),
        'gridMergedCount':sum(bool(z.get('gridMerged')) for z in matching),
        'riGroupedCount':sum(bool(z.get('riGrouped')) for z in matching),
        'noScheduleCount':sum(bool(z.get('noSchedule')) for z in matching),
        'groupKeys':sorted(set(str(z.get('groupKey') or '') for z in matching))[:20],
        'sample':{
            'days':matching[0].get('days'),
            'estimated':matching[0].get('estimated'),
            'gridMerged':matching[0].get('gridMerged'),
            'riGrouped':matching[0].get('riGrouped'),
            'noSchedule':matching[0].get('noSchedule'),
            'neighborRatio':matching[0].get('neighborRatio'),
        }
    }
Path('tools/v84-jangyang-validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
