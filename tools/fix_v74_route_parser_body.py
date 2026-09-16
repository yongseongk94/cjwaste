from pathlib import Path

p=Path('index.html')
text=p.read_text(encoding='utf-8')
marker='function routeDescriptorsForMap(raw){'
start=text.find(marker)
if start<0: raise SystemExit('routeDescriptorsForMap not found')

i=start
brace=0
quote=None
esc=False
while i<len(text):
    ch=text[i]
    if quote:
        if esc: esc=False
        elif ch=='\\': esc=True
        elif ch==quote: quote=None
    else:
        if ch in "'\"`": quote=ch
        elif ch=='{': brace+=1
        elif ch=='}':
            brace-=1
            if brace==0:
                i+=1
                break
    i+=1
if brace!=0: raise SystemExit('unbalanced parser function')

new=r'''function routeDescriptorsForMap(raw){
  const src=expandRouteShorthand(expandKnownMultiLocationSource(raw));
  const out=[];

  // 최상위 쉼표/줄바꿈만 위치 구분자로 사용합니다.
  // 괄호 안의 '쉐보레부품,더좋은하우스' 같은 복수 시설은 아래에서 따로 분리합니다.
  splitTopLevelRouteParts(src).forEach(part=>{
    // '/', '및', 'A~B'는 실제 복수 위치/구간으로 분리합니다.
    splitRouteLocationUnits(part).forEach(unit=>{
      const original=String(unit||'').trim();
      if(!original)return;
      const bareOriginal=original.replace(/\([^)]*\)/g,' ').trim();

      // '및 원룸지역'처럼 범위어만 떨어져 적힌 경우 직전 항목의 범위 의미로 흡수합니다.
      if(/^(원룸지역|상가지역|주거지역)$/.test(bareOriginal)){
        if(out.length){
          out[out.length-1].scope='range';
          out[out.length-1].raw=`${out[out.length-1].raw} + ${bareOriginal}`;
        }
        return;
      }

      const hasRange=/(일대|일원|원룸지역|상가지역|주거지역)/.test(original);
      const hasLine=/(간선|주요간선도로)/.test(original);
      const parens=[...original.matchAll(/\(([^)]+)\)/g)]
        .map(m=>m[1].trim())
        .filter(Boolean)
        .flatMap(x=>String(x).split(/\s*,\s*|\s*\/\s*|\s*및\s*/))
        .map(x=>x.trim())
        .filter(Boolean);
      const outer=cleanRouteTerm(bareOriginal);

      if(outer){
        let scope=hasRange?'range':(hasLine?'line':'point');
        if(isRoadRouteTerm(outer))scope='road';
        else if(isRoadAddressPointTerm(outer))scope=hasRange?'road-address-range':'road-address';
        // '내덕2동주요간선도로' 같이 실제 도로명이 아닌 포괄문구는 선을 만들지 않습니다.
        if(/주요간선도로$/.test(outer))scope='broad';
        out.push({term:outer,scope,raw:original});
      }

      // 괄호 안 도로명/시설명도 원문 위치의 독립 수거지점으로 취급합니다.
      for(const inside of parens){
        const pt=cleanRouteTerm(inside);
        if(!pt)continue;
        const scope=isRoadRouteTerm(pt)?'road':(isRoadAddressPointTerm(pt)?'road-address':'point');
        out.push({term:pt,scope,raw:original,parent:outer||''});
      }
    });
  });

  // 연속 중복만 정리합니다. 원본 순서와 반복 방문은 유지합니다.
  return out.filter((d,i)=>i===0 || routeNorm(d.term)!==routeNorm(out[i-1].term) || d.scope!==out[i-1].scope);
}'''

text=text[:start]+new+text[i:]
for required in [
    'splitTopLevelRouteParts(src).forEach(part=>{',
    'splitRouteLocationUnits(part).forEach(unit=>{',
    '.flatMap(x=>String(x).split(/\\s*,\\s*|\\s*\\/\\s*|\\s*및\\s*/))'
]:
    if required not in text: raise SystemExit('missing '+required)
p.write_text(text,encoding='utf-8')
