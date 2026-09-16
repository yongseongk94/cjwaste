from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')

pat=re.compile(r"function contractExactScheduleMatch\(type,ctx\)\{.*?\n\}",re.S)
m=pat.search(s)
if not m:
    raise SystemExit('contractExactScheduleMatch not found')

new=r'''function contractExactScheduleMatch(type,ctx){
  const district=canonicalDistrict(ctx?.legalEmd||ctx?.district||'');
  const target=contractAddressNorm(ctx?.address||'');
  if(!target)return null;
  let best=null,bestLen=0;

  // 대행업체 원본 차량×요일 노선표의 주소목록을 직접 검색주소와 대조합니다.
  // 별도 특수지점만 보던 기존 로직 때문에 원본 일정이 있어도 '요일 확인 필요'로 빠지던 문제를 보완합니다.
  for(const r of (CONTRACT_ROUTES[type]||[])){
    if(!(r.districts||[]).some(d=>canonicalDistrict(d)===district))continue;
    let localBestLen=0,matchedAddress='';
    const matchedDays=[];
    for(const [day,raw] of Object.entries(r.days||{})){
      for(const part of String(raw||'').split(/[,/]/)){
        const key=contractAddressNorm(part);
        if(key.length<5)continue;
        const score=Math.min(key.length,target.length);
        if((target.includes(key)||key.includes(target))&&score>=5){
          if(!matchedDays.includes(day))matchedDays.push(day);
          if(score>localBestLen){localBestLen=score;matchedAddress=part.trim()}
        }
      }
    }
    if(matchedDays.length&&localBestLen>bestLen){
      const meta=contractRouteMeta(r.vehicle)||{};
      best={
        provider:r.provider||meta.provider||'',
        vehicle:r.plate||meta.plate||r.vehicle||'',
        days:DAYS.filter(d=>matchedDays.includes(d)),
        address:matchedAddress,
        housing:r.housing||meta.housing||'single',
        type
      };
      bestLen=localBestLen;
    }
  }

  // 특수주소 직접매칭은 그대로 유지하고, 더 구체적인 주소가 있으면 우선합니다.
  const rows=[];
  if(type==='general')rows.push(...CONTRACT_APARTMENTS.map(x=>({...x,housing:'apartment',type:'general'})));
  rows.push(...CONTRACT_SPECIAL_POINTS.filter(x=>x.type===type).map(x=>({...x,housing:'single'})));
  for(const x of rows){
    if(canonicalDistrict(x.district)!==district)continue;
    for(const key of contractAddressCandidates(x.address)){
      const score=Math.min(key.length,target.length);
      if((target.includes(key)||key.includes(target))&&score>bestLen){best=x;bestLen=score}
    }
  }
  return best;
}'''

s=s[:m.start()]+new+s[m.end():]

required=[
  '대행업체 원본 차량×요일 노선표의 주소목록을 직접 검색주소와 대조합니다.',
  'for(const r of (CONTRACT_ROUTES[type]||[]))',
  'matchedDays',
  'contractRouteMeta(r.vehicle)',
  'function renderContractExactSchedule(type,row,ctx)'
]
for x in required:
    if x not in s:
        raise SystemExit('required marker missing: '+x)

p.write_text(s,encoding='utf-8')
print('contractor schedule direct-match patch applied')
