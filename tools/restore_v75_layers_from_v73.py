from pathlib import Path
import json,re,subprocess

CURRENT_VERSION='v75-naedeok2-apartment-only'
CURRENT_ZONE_VERSION=f'zone-{CURRENT_VERSION}|{CURRENT_VERSION}'
OLD_COMMIT='9763d90510fc73eab031f4f2d28d294f5e986c80'

p=Path('index.html')
text=p.read_text(encoding='utf-8')
old=subprocess.check_output(['git','show',f'{OLD_COMMIT}:index.html'],text=True)
m=re.search(r'<script id="bundledPrecomputed" type="application/json">(.*?)</script>',old,re.S)
if not m:
    raise SystemExit('last valid v73 bundle not found')
data=json.loads(m.group(1))

before_routes=len(data.get('routes',[]))
# 내덕2동 95오0147은 원자료 해석 오류였던 단독주택 항목. 현재 v75에서는 이랜드해가든 공동주택 정확주소만 별도 일정매칭한다.
data['routes']=[r for r in data.get('routes',[]) if not (
    r.get('type')=='general' and '95오0147' in str(r.get('vehicle','')) and '내덕2동' in str(r.get('vehicle',''))
)]
removed=before_routes-len(data['routes'])
if removed!=3:
    raise SystemExit(f'expected 3 bad Naedeok2 routes, removed {removed}')

# v73 권역에는 해당 잘못된 노선 기반 권역이 없음을 재검증한다.
for typ,arr in (data.get('zones') or {}).items():
    bad=[z for z in arr if '95오0147' in json.dumps(z,ensure_ascii=False) and '내덕2동' in json.dumps(z,ensure_ascii=False)]
    if bad:
        raise SystemExit(f'unexpected bad {typ} zones: {len(bad)}')

data['version']=CURRENT_VERSION
data['zoneVersion']=CURRENT_ZONE_VERSION
data['restoredFrom']='v73 verified bundle 9763d905; removed Naedeok2 95오0147 road-evidence entries'

payload=json.dumps(data,ensure_ascii=False,separators=(',',':'))
pat=r'(<script id="bundledPrecomputed" type="application/json">).*?(</script>)'
text,n=re.subn(pat,lambda mm:mm.group(1)+payload+mm.group(2),text,count=1,flags=re.S)
if n!=1:
    raise SystemExit('bundledPrecomputed slot not found')

# 두 구조 레이어를 모두 기본 표시한다.
old_state='const serviceLayerState={zone:true,route:false};'
new_state='const serviceLayerState={zone:true,route:true};'
if old_state in text:
    text=text.replace(old_state,new_state,1)
elif new_state not in text:
    raise SystemExit('serviceLayerState definition not found')

old_btn='<button data-structure="route">② 동지역 근거노선</button>'
new_btn='<button class="active" data-structure="route">② 근거노선</button>'
if old_btn in text:
    text=text.replace(old_btn,new_btn,1)
elif new_btn not in text:
    raise SystemExit('route structure button not found')

# 설명도 현재 실제 동작과 맞춘다.
text=text.replace('② 근거노선은 우암동·내덕1동·내덕2동·오근장동·율량사천동의 직영코스만 표시합니다. 읍·면 근거노선은 표시·선택 대상에서 제외했습니다.',
                  '② 근거노선은 원본 코스표에서 실제 도로망으로 확인된 수거구간을 표시합니다. 확인되지 않은 구간을 임의 직선으로 연결하지 않습니다.')

p.write_text(text,encoding='utf-8')

report={
    'version':CURRENT_VERSION,
    'zoneVersion':CURRENT_ZONE_VERSION,
    'restoredFrom':OLD_COMMIT,
    'routesBefore':before_routes,
    'routesAfter':len(data['routes']),
    'removedNaedeok2BadRoutes':removed,
    'generalZones':len(data.get('zones',{}).get('general',[])),
    'recycleZones':len(data.get('zones',{}).get('recycle',[])),
    'defaultLayers':{'zone':True,'route':True}
}
Path('tools/v75_layer_restore_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
