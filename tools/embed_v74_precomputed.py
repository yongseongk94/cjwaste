from pathlib import Path
import re,json
p=Path('index.html')
text=p.read_text(encoding='utf-8')
data=Path('/tmp/v74-precomputed.json').read_text(encoding='utf-8')
obj=json.loads(data)
if obj.get('version')!='v74-source-multilocation': raise SystemExit('wrong export version')
pat=r'(<script id="bundledPrecomputed" type="application/json">).*?(</script>)'
text,n=re.subn(pat,lambda m:m.group(1)+data+m.group(2),text,count=1,flags=re.S)
if n!=1: raise SystemExit('precomputed slot missing')
p.write_text(text,encoding='utf-8')
scripts='\n'.join(re.findall(r'<script>(.*?)</script>',text,flags=re.S))
Path('/tmp/index-inline.js').write_text(scripts,encoding='utf-8')
