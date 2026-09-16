from pathlib import Path

text=Path('index.html').read_text(encoding='utf-8')
marker='function routeDescriptorsForMap(raw){'
start=text.find(marker)
if start<0:
    raise SystemExit('routeDescriptorsForMap not found')

i=start
brace=0
in_s=None
esc=False
while i<len(text):
    ch=text[i]
    if in_s:
        if esc:
            esc=False
        elif ch=='\\':
            esc=True
        elif ch==in_s:
            in_s=None
    else:
        if ch in "'\"`":
            in_s=ch
        elif ch=='{':
            brace+=1
        elif ch=='}':
            brace-=1
            if brace==0:
                i+=1
                break
    i+=1
func=text[start:i]
checks=[]
for needle in [
    'splitTopLevelRouteParts(src)',
    'splitRouteLocationUnits(part)',
    'src.split(/[,\\n]/)',
    "String(part||'').split(/\\s*및\\s*|\\s*\\/\\s*/)",
    'for(const inside of parens)',
    'for(const inside of parens.flatMap'
]:
    checks.append(f'{needle}: {needle in func}')

# also locate the special 95오0147 fragments in the whole file
specials=[]
for needle in [
    '"address":"공항로 84번길"',
    '"address":"이랜드해가든아파트"',
    '"address":"공항로 84번길, 이랜드해가든아파트"',
    '공항로 84번길, 이랜드해가든아파트'
]:
    specials.append(f'{needle}: {text.count(needle)}')

out='\n'.join(checks)+'\n\n'+func+'\n\nSPECIAL COUNTS\n'+'\n'.join(specials)+'\n'
Path('tools/v74_route_parser_diag.txt').write_text(out,encoding='utf-8')
