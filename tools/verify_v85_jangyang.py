import json
from pathlib import Path

expected='zone-v85-village-waypoints|v76-layer-visibility-refresh'
targets={'general':('6138','수'),'recycle':('6544','수')}
out={}
for t,(vehicle,day) in targets.items():
    d=json.loads(Path(f'data/service-zones-v85-{t}-all.json').read_text(encoding='utf-8'))
    if d.get('zoneVersion')!=expected:
        raise SystemExit(f'{t}: wrong zoneVersion')
    zs=[z for z in d.get('zones',[]) if z.get('district')=='북이면' and z.get('riName')=='장양리']
    matches=[z for z in zs if str(z.get('vehicle'))==vehicle and day in (z.get('days') or [])]
    if not matches:
        raise SystemExit(f'{t}: missing 장양리 {vehicle}/{day}')
    if not any(z.get('estimated') for z in matches):
        raise SystemExit(f'{t}: no estimated cells')
    if not any(z.get('gridMerged') for z in matches):
        raise SystemExit(f'{t}: no grid merged cells')
    if any(z.get('riGrouped') for z in matches):
        raise SystemExit(f'{t}: legacy riGrouped remains')
    if any(z.get('noSchedule') for z in matches):
        raise SystemExit(f'{t}: noSchedule remains')
    out[t]={
        'jangyangZoneCount':len(zs),
        'matchedCount':len(matches),
        'vehicle':vehicle,
        'day':day,
        'estimatedCount':sum(bool(z.get('estimated')) for z in matches),
        'gridMergedCount':sum(bool(z.get('gridMerged')) for z in matches),
        'riGroupedCount':sum(bool(z.get('riGrouped')) for z in matches),
        'noScheduleCount':sum(bool(z.get('noSchedule')) for z in matches),
        'groupKeys':sorted(set(str(z.get('groupKey') or '') for z in matches))
    }
Path('tools/v85-jangyang-validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
