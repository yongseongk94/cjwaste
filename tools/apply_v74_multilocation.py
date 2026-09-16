from pathlib import Path
import re, json
p=Path('index.html')
text=p.read_text(encoding='utf-8')
pat=r'(<script id="bundledPrecomputed" type="application/json">).*?(</script>)'
text,n=re.subn(pat,lambda m:m.group(1)+'{}'+m.group(2),text,count=1,flags=re.S)
if n!=1: raise SystemExit('bundledPrecomputed slot missing')
text=text.replace('v73-partial-road-segments','v74-source-multilocation')
text=text.replace('zone-v73-partial-road-segments','zone-v74-source-multilocation')
text=text.replace('공항로 84번길 해가든','공항로 84번길, 이랜드해가든아파트')
old='{"type":"general","provider":"제일환경","district":"내덕2동","address":"공항로 84번길, 이랜드해가든아파트","name":"","days":["화","목","토"],"vehicle":"95오0147","time":"0.48958333333333331","freq":"주3회"}'
new='{"type":"general","provider":"제일환경","district":"내덕2동","address":"공항로 84번길","name":"공항로 84번길 일대","days":["화","목","토"],"vehicle":"95오0147","time":"0.48958333333333331","freq":"주3회"},{"type":"general","provider":"제일환경","district":"내덕2동","address":"이랜드해가든아파트","name":"이랜드해가든아파트","days":["화","목","토"],"vehicle":"95오0147","time":"0.48958333333333331","freq":"주3회"}'
if old in text: text=text.replace(old,new)
helper=r'''
// v74: 원본 한 셀에 여러 실제 수거위치가 병기된 경우를 서로 다른 위치로 해석합니다.
const ROUTE_SOURCE_MULTI_LOCATION_REPLACEMENTS=[
  ['공항로 84번길 해가든','공항로 84번길, 이랜드해가든아파트'],
  ['중앙로 47-8 각리초.중학교','중앙로 47-8, 각리초등학교, 각리중학교'],
  ['내덕로 22 일대','내덕로 22 일대, 장미여관, 평화상가'],
  ['중심상업로 17','중심상업로 17, 신한은행, 오창프라자2'],
  ['대성로 288번길 37 주변','대성로 288번길 37 주변, 대성빌, 샤론빌'],
  ['향군로 56번길 ~ 내덕로 24-1 일대','향군로 56번길 ~ 내덕로 24-1 일대, 송죽칼국수'],
  ['양청택지 3길 29-5 ~ 35  원룸촌 일대','양청택지 3길 29-5 ~ 35 원룸촌 일대, 낙원하우스, 호암빌리지'],
  ['양청1길 45-22 원룸촌 일대','양청1길 45-22 원룸촌 일대, 금당빌라, 미도캐슬'],
  ['양청1길 93-13 원룸촌 일대','양청1길 93-13 원룸촌 일대, 노블레스, 청와빌'],
  ['양청 2안길 62-3 원룸촌 일대','양청 2안길 62-3 원룸촌 일대, 현하우스, 세리빌라'],
  ['주성 3길 8-2 원룸촌 일대','주성 3길 8-2 원룸촌 일대, 어울림빌, 휘영빌'],
  ['양청택지로 124-5 원룸촌 일대','양청택지로 124-5 원룸촌 일대, 극동빌, 부광빌']
];
function expandKnownMultiLocationSource(raw){
  let s=String(raw||'');
  for(const [from,to] of ROUTE_SOURCE_MULTI_LOCATION_REPLACEMENTS){ if(from!==to)s=s.split(from).join(to); }
  return s;
}
function splitTopLevelRouteParts(src){
  const out=[]; let buf=''; let depth=0;
  for(const ch of String(src||'')){
    if(ch==='(')depth++;
    if(ch===')'&&depth>0)depth--;
    if((ch===','||ch==='\n')&&depth===0){ if(buf.trim())out.push(buf.trim()); buf=''; continue; }
    buf+=ch;
  }
  if(buf.trim())out.push(buf.trim());
  return out;
}
function splitRouteRangeUnit(unit){
  const s=String(unit||'').trim(); if(!s)return [];
  if(/\d{1,2}:\d{2}\s*[~～]\s*\d{1,2}:\d{2}/.test(s))return [s];
  if(!/[~～]/.test(s))return [s];
  const parts=s.split(/\s*[~～]\s*/,2);
  let left=String(parts[0]||'').trim(), right=String(parts[1]||'').trim();
  if(!left)return right?[right]:[];
  if(!right)return [left];
  if(/^\d+(?:-\d+)?(?:\s*(?:일대|일원|주변|원룸촌\s*일대))?$/.test(right)){
    const m=left.match(/^(.*?(?:대로|로|길|번길))\s*\d+(?:-\d+)?/);
    if(m)right=`${m[1]} ${right}`;
  }
  return [left,right];
}
function splitRouteLocationUnits(part){
  const out=[];
  for(const base of String(part||'').split(/\s*및\s*|\s*\/\s*/)){
    for(const x of splitRouteRangeUnit(base))if(String(x||'').trim())out.push(String(x).trim());
  }
  return out;
}
'''
marker='function routeDescriptorsForMap(raw){'
if 'function splitTopLevelRouteParts(src)' not in text:
    idx=text.find(marker)
    if idx<0: raise SystemExit('routeDescriptorsForMap missing')
    text=text[:idx]+helper+text[idx:]
text=text.replace('const src=expandRouteShorthand(raw);','const src=expandRouteShorthand(expandKnownMultiLocationSource(raw));',1)
text=text.replace('src.split(/[,\\n]/).forEach(part=>{','splitTopLevelRouteParts(src).forEach(part=>{',1)
text=text.replace("String(part||'').split(/\\s*및\\s*|\\s*\\/\\s*/).forEach(unit=>{","splitRouteLocationUnits(part).forEach(unit=>{",1)
text=text.replace('for(const inside of parens){','for(const inside of parens.flatMap(x=>String(x).split(/\\s*,\\s*|\\s*\\/\\s*|\\s*및\\s*/))){',1)
for x in ['splitTopLevelRouteParts(src).forEach(part=>{','splitRouteLocationUnits(part).forEach(unit=>{','이랜드해가든아파트','낙원하우스, 호암빌리지','대성빌, 샤론빌']:
    if x not in text: raise SystemExit('missing patch marker: '+x)
p.write_text(text,encoding='utf-8')
audit={
  'version':'v74-source-multilocation',
  'policy':'Split only evidence-backed multiple locations; keep ordinary address+landmark descriptions together.',
  'user_confirmed':['공항로 84번길','이랜드해가든아파트'],
  'explicit_multi_address':['율량로 17(주공1단지) / 율량로 47(주공2단지)'],
  'range_endpoints':['사북로 145~121','우암오거리~청대사거리','대성로 303~239','향군로 118~우암동 369-20','교서로 134~216','무심동로 500~교서로 221','향군로 56번길~내덕로 24-1','양청택지3길 29-5~35','양청2길 32~36','대성로257번길~상당로232번길'],
  'multi_poi_rows':['쉐보레부품 / 더좋은하우스','각리초등학교 / 각리중학교','장미여관 / 평화상가','신한은행 / 오창프라자2','대성빌 / 샤론빌','낙원하우스 / 호암빌리지','금당빌라 / 미도캐슬','노블레스 / 청와빌','현하우스 / 세리빌라','어울림빌 / 휘영빌','극동빌 / 부광빌']
}
Path('tools/v74_multilocation_source_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
