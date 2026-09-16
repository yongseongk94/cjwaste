from pathlib import Path

text=Path('index.html').read_text(encoding='utf-8')
markers=['function routeDescriptorsForMap(raw){','function splitTopLevelRouteParts(src){','function splitRouteRangeUnit(unit){','function splitRouteLocationUnits(part){']
lines=[]
for m in markers:
    poss=[]; s=0
    while True:
        i=text.find(m,s)
        if i<0: break
        poss.append(i); s=i+1
    lines.append(f'{m} COUNT={len(poss)} POS={poss}')

# extract every routeDescriptorsForMap function body with simple quote-aware brace matching
marker='function routeDescriptorsForMap(raw){'
s=0; n=0
while True:
    start=text.find(marker,s)
    if start<0: break
    i=start; brace=0; quote=None; esc=False
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
                    i+=1; break
        i+=1
    n+=1
    lines.append(f'\n--- ROUTE FUNCTION {n} @ {start} ---\n{text[start:i]}')
    s=i

# extract helper definitions too
for fname in ['splitTopLevelRouteParts','splitRouteRangeUnit','splitRouteLocationUnits']:
    marker=f'function {fname}'
    start=text.find(marker)
    if start<0: continue
    i=text.find('{',start); brace=0; quote=None; esc=False
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
                    i+=1; break
        i+=1
    lines.append(f'\n--- HELPER {fname} ---\n{text[start:i]}')

Path('tools/v74_duplicate_diag.txt').write_text('\n'.join(lines),encoding='utf-8')
