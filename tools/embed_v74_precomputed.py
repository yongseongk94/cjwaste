from pathlib import Path
import re,json
p=Path('index.html')
text=p.read_text(encoding='utf-8')
# v75 이상 로직이 반영된 뒤에는 오래 실행 중이던 v74 작업이 번들 데이터를 덮어쓰지 못하게 막습니다.
if 'v75-naedeok2-apartment-only' in text:
    raise SystemExit('stale v74 freeze blocked: v75 is already active')
data=Path('/tmp/v74-precomputed.json').read_text(encoding='utf-8')
obj=json.loads(data)
if obj.get('version')!='v74-source-multilocation': raise SystemExit('wrong export version')
pat=r'(<script id="bundledPrecomputed" type="application/json">).*?(</script>)'
text,n=re.subn(pat,lambda m:m.group(1)+data+m.group(2),text,count=1,flags=re.S)
if n!=1: raise SystemExit('precomputed slot missing')
p.write_text(text,encoding='utf-8')
scripts='\n'.join(re.findall(r'<script>(.*?)</script>',text,flags=re.S))
Path('/tmp/index-inline.js').write_text(scripts,encoding='utf-8')
