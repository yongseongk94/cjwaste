from pathlib import Path
import re
p=Path('index.html')
t=p.read_text(encoding='utf-8')
terms=['95오0147','공항로 84번길','이랜드해가든','내덕2동','CONTRACT_SPECIAL_POINTS','CONTRACT_ROUTES','contractExactScheduleMatch']
out=[]
for term in terms:
    out.append(f'## {term} count={t.count(term)}')
    starts=[m.start() for m in re.finditer(re.escape(term),t)]
    for i,pos in enumerate(starts[:12],1):
        a=max(0,pos-900); b=min(len(t),pos+1800)
        out.append(f'--- {term} #{i} @ {pos} ---\n'+t[a:b])
Path('tools/naedeok2_contract_diag.txt').write_text('\n\n'.join(out),encoding='utf-8')
