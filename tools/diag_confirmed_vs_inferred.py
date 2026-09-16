from pathlib import Path

lines=Path('index.html').read_text(encoding='utf-8').splitlines()
needles=[
 'function buildServiceZones','async function buildServiceZones','function serviceGroupsForRegion','function classifyServiceGroups',
 'function buildGridServiceZonesForRegion','function buildRouteBuffer','sourceOnly','routeBuffer','exact','DIRECT_RI_DAYS',
 'RURAL_INFERRED_ROUTE_DISTRICTS','contractExactScheduleMatch','function ensureServiceZoneMatch','function serviceZoneOverlayMatch',
 'function renderSchedule','restoredRuralRiSchedule','30m','0.030','const measures=specs.map','renderNearbyRouteSchedule(',
 'ensureDistrictRouteItems(type,district)','inferredZoneMatchForAddress(','await inferredZoneMatchForAddress','contractExactScheduleMatch(type,ctx)'
]
out=[f'lines={len(lines)}']
used=[]
for needle in needles:
    hits=[i for i,s in enumerate(lines) if needle in s]
    for i in hits[:12]:
        if any(abs(i-j)<8 for j in used): continue
        used.append(i)
        a=max(0,i-60); b=min(len(lines),i+180)
        out.append(f'\n===== {needle} @ {i+1} =====')
        for n in range(a,b):
            t=lines[n]
            if len(t)>2000:t=t[:2000]+' ...[CUT]'
            out.append(f'{n+1}: {t}')
Path('tools/confirmed_vs_inferred_diag.txt').write_text('\n'.join(out),encoding='utf-8')
