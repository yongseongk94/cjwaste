from pathlib import Path

lines=Path('index.html').read_text(encoding='utf-8').splitlines()
needles=[
    'scroll','wheel','resize','zoom_changed','bounds_changed','center_changed','idle','dragend',
    'kakao.maps.event.addListener(map','setMap(null)','serviceZoneOverlays','clearServiceZone','clearServiceZones',
    'syncServiceZoneVisibility','buildServiceZones','buildGridServiceZonesForRegion','mergedRowRuns','gridMerged',
    'addServiceZonePolygon','activeLayer','renderServiceZoneSchedule','setLayer('
]
out=[f'lines={len(lines)}']
seen=set()
for needle in needles:
    for i,s in enumerate(lines):
        if needle in s:
            key=(needle,i)
            if key in seen: continue
            seen.add(key)
            a=max(0,i-15); b=min(len(lines),i+55)
            out.append(f'\n===== {needle} @ {i+1} =====')
            for n in range(a,b):
                t=lines[n]
                if len(t)>2200:t=t[:2200]+' ...[CUT]'
                out.append(f'{n+1}: {t}')
Path('tools/scroll_polygon_diag.txt').write_text('\n'.join(out),encoding='utf-8')
