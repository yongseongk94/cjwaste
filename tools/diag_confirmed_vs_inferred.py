from pathlib import Path

lines=Path('index.html').read_text(encoding='utf-8').splitlines()
terms=['renderNearbyRouteSchedule(','const measures=specs.map','inferredZoneMatchForAddress(','contractExactScheduleMatch(type,ctx)','ensureServiceZoneMatch(type,ctx)','renderScheduleFor','addressSchedule','resolveAddress']
out=[f'lines={len(lines)}']
for term in terms:
    hits=[i for i,s in enumerate(lines) if term in s]
    for i in hits[:20]:
        a=max(0,i-90); b=min(len(lines),i+220)
        out.append(f'\n===== {term} @ {i+1} =====')
        for n in range(a,b):
            t=lines[n]
            if len(t)>2200:t=t[:2200]+' ...[CUT]'
            out.append(f'{n+1}: {t}')
Path('tools/confirmed_vs_inferred_diag.txt').write_text('\n'.join(out),encoding='utf-8')
