from pathlib import Path
import re, json

p=Path('index.html')
text=p.read_text(encoding='utf-8')

# 1) 버전 갱신: 오래된 v74 번들/IndexedDB를 재사용하지 않도록 합니다.
text=text.replace('v74-source-multilocation','v75-naedeok2-apartment-only')
text=text.replace('zone-v74-source-multilocation','zone-v75-naedeok2-apartment-only')

# 2) '공항로 84번길 해가든'은 도로+시설 두 위치가 아니라,
#    공항로84번길 30의 이랜드해가든 공동주택 1개 수거지점으로 해석합니다.
old_repl="['공항로 84번길 해가든','공항로 84번길, 이랜드해가든아파트']"
new_repl="['공항로 84번길 해가든','공항로84번길 30 이랜드해가든']"
if old_repl not in text:
    raise SystemExit('old Haegadeun replacement not found')
text=text.replace(old_repl,new_repl)

# 3) 원본에 잘못 '단독'으로 추출된 95오0147 내덕2동 행을 공동주택 단일지점으로 재분류합니다.
old_route='{"vehicle":"제일환경|95오0147|내덕2동|단독","provider":"제일환경","plate":"95오0147","districts":["내덕2동"],"housing":"single","zoneEligible":false,"days":{"화":"공항로 84번길, 이랜드해가든아파트","목":"공항로 84번길, 이랜드해가든아파트","토":"공항로 84번길, 이랜드해가든아파트"}}'
new_route='{"vehicle":"제일환경|95오0147|내덕2동|공동|이랜드해가든","provider":"제일환경","plate":"95오0147","districts":["내덕2동"],"housing":"apartment","zoneEligible":false,"days":{"화":"공항로84번길 30 이랜드해가든","목":"공항로84번길 30 이랜드해가든","토":"공항로84번길 30 이랜드해가든"}}'
if old_route not in text:
    raise SystemExit('old 95오0147 Naedeok2 route object not found')
text=text.replace(old_route,new_route)

old_meta='"제일환경|95오0147|내덕2동|단독":{"provider":"제일환경","plate":"95오0147","district":"내덕2동","housing":"single","zoneEligible":false}'
new_meta='"제일환경|95오0147|내덕2동|공동|이랜드해가든":{"provider":"제일환경","plate":"95오0147","district":"내덕2동","housing":"apartment","zoneEligible":false}'
if old_meta not in text:
    raise SystemExit('old 95오0147 Naedeok2 meta not found')
text=text.replace(old_meta,new_meta)

# 4) v74가 만든 잘못된 두 특수지점(도로 일대 + 아파트명)을 하나의 정확한 공동주택 지점으로 합칩니다.
old_special='{"type":"general","provider":"제일환경","district":"내덕2동","address":"공항로 84번길","name":"공항로 84번길 일대","days":["화","목","토"],"vehicle":"95오0147","time":"0.48958333333333331","freq":"주3회"},{"type":"general","provider":"제일환경","district":"내덕2동","address":"이랜드해가든아파트","name":"이랜드해가든아파트","days":["화","목","토"],"vehicle":"95오0147","time":"0.48958333333333331","freq":"주3회"}'
new_special='{"type":"general","provider":"제일환경","district":"내덕2동","address":"공항로84번길 30","name":"이랜드해가든","days":["화","목","토"],"vehicle":"95오0147","time":"0.48958333333333331","freq":"주3회","housing":"apartment"}'
if old_special not in text:
    raise SystemExit('old split special points not found')
text=text.replace(old_special,new_special)

# 5) 공동주택 노선은 계속 지도 선에서 제외하되, 이랜드해가든 1개 정확 지점만 일정 직접매칭 예외로 허용합니다.
old_filter="const CONTRACT_SPECIAL_POINTS=(CONTRACT_SOURCE_DATA.special||[]).filter(r=>r.housing!=='apartment');"
new_filter="const CONTRACT_SPECIAL_POINTS=(CONTRACT_SOURCE_DATA.special||[]).filter(r=>r.housing!=='apartment' || (r.district==='내덕2동' && r.vehicle==='95오0147' && /이랜드해가든/.test(String(r.name||r.address||''))));"
if old_filter not in text:
    raise SystemExit('CONTRACT_SPECIAL_POINTS filter not found')
text=text.replace(old_filter,new_filter)

old_map="CONTRACT_SPECIAL_POINTS.filter(x=>x.type===type).map(x=>({...x,housing:'single'}))"
new_map="CONTRACT_SPECIAL_POINTS.filter(x=>x.type===type).map(x=>({...x,housing:x.housing||'single'}))"
if old_map not in text:
    raise SystemExit('special point housing map not found')
text=text.replace(old_map,new_map)

# 6) 이랜드해가든 예외는 도로명만 같다고 매칭하지 않고 정확 주소(30번) 또는 단지명일 때만 허용합니다.
needle="for(const x of rows){\n    if(canonicalDistrict(x.district)!==district)continue;"
insert="for(const x of rows){\n    if(canonicalDistrict(x.district)!==district)continue;\n    if(x.provider==='제일환경' && x.district==='내덕2동' && x.vehicle==='95오0147' && /이랜드해가든/.test(String(x.name||x.address||''))){\n      const exactAddr=contractAddressNorm('공항로84번길 30');\n      const exactName=contractAddressNorm('이랜드해가든');\n      if(!target.includes(exactAddr) && !target.includes(exactName))continue;\n    }"
if needle not in text:
    raise SystemExit('special point match loop not found')
text=text.replace(needle,insert,1)

# 7) 검증 마커
checks={
 'version': 'v75-naedeok2-apartment-only',
 'bad_single_route': '제일환경|95오0147|내덕2동|단독',
 'good_apartment_route': '제일환경|95오0147|내덕2동|공동|이랜드해가든',
 'exact_address': '공항로84번길 30',
}
if checks['version'] not in text: raise SystemExit('v75 marker missing')
if checks['bad_single_route'] in text: raise SystemExit('bad Naedeok2 single route still present')
if checks['good_apartment_route'] not in text: raise SystemExit('apartment-only source route missing')
if '"address":"공항로 84번길","name":"공항로 84번길 일대"' in text: raise SystemExit('bad road special point still present')
if '"address":"공항로84번길 30","name":"이랜드해가든"' not in text: raise SystemExit('exact Haegadeun point missing')

p.write_text(text,encoding='utf-8')
Path('tools/v75_naedeok2_patch_report.json').write_text(json.dumps({
  'version':'v75-naedeok2-apartment-only',
  'classification':{
    'naedeok2_single_general':'direct',
    'naedeok2_single_recycle':'direct',
    'naedeok2_apartment_general':'contractor',
    'haegadeun':{'provider':'제일환경','vehicle':'95오0147','days':['화','목','토'],'address':'공항로84번길 30','mapGeometry':'exact-point-only'}
  }
},ensure_ascii=False,indent=2),encoding='utf-8')
