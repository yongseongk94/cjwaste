from pathlib import Path

lines=Path('index.html').read_text(encoding='utf-8').splitlines()
needles=[
    'scroll','wheel','resize','setMap(null)','serviceZoneOverlays','clearServiceZone','clearServiceZones',
    'buildGridServiceZonesForRegion','mergedRowRuns','gridMerged','addServiceZonePolygon','activeLayer','renderServiceZoneSchedule'
]
out=[f'lines={len(lines)}']
seen=set()
for needle in needles:
    for i,s in enumerate(lines):
        if needle in s:
            key=(needle,i)
            if key in seen: continue
            seen.add(key)
            a=max(0,i-12); b=min(len(lines),i+40)
            out.append(f'\n===== {needle} @ {i+1} =====')
            for n in range(a,b):
                t=lines[n]
                if len(t)>1800:t=t[:1800]+' ...[CUT]'
                out.append(f'{n+1}: {t}')
Path('tools/scroll_polygon_diag.txt').write_text('\n'.join(out),encoding='utf-8')
