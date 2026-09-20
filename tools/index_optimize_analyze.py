from pathlib import Path
import re, gzip, hashlib, base64, json

p=Path("index.html")
raw=p.read_bytes()
text=raw.decode("utf-8")
lines=text.splitlines()

report=[]
report.append("INDEX SIZE ANALYSIS")
report.append(f"bytes={len(raw)}")
report.append(f"chars={len(text)}")
report.append(f"lines={len(lines)}")
report.append(f"gzip_bytes={len(gzip.compress(raw, compresslevel=9))}")
report.append("")

# Base64/data URI inventory
pat=re.compile(r'data:([a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]+)')
items=[]
for i,m in enumerate(pat.finditer(text),1):
    mime=m.group(1)
    b64=m.group(2)
    try:
        decoded=base64.b64decode(b64, validate=False)
        decoded_len=len(decoded)
        sha=hashlib.sha256(decoded).hexdigest()[:16]
    except Exception:
        decoded_len=-1
        sha="decode-error"
    line_no=text.count("\n",0,m.start())+1
    before=text[max(0,m.start()-140):m.start()].replace("\n"," ")
    after=text[m.end():min(len(text),m.end()+80)].replace("\n"," ")
    items.append({
        "n":i,"line":line_no,"mime":mime,"uri_chars":len(m.group(0)),
        "decoded_bytes":decoded_len,"sha":sha,
        "context_before":before[-140:],"context_after":after[:80]
    })

report.append(f"data_uri_count={len(items)}")
report.append(f"data_uri_total_chars={sum(x['uri_chars'] for x in items)}")
report.append(f"data_uri_unique_payloads={len(set((x['mime'],x['sha']) for x in items))}")
report.append("DATA_URIS")
for x in sorted(items,key=lambda z:z["uri_chars"],reverse=True):
    report.append(json.dumps(x,ensure_ascii=False))
report.append("")

# Largest lines. Keep content excerpts only.
largest=sorted(enumerate(lines,1),key=lambda t:len(t[1]),reverse=True)[:30]
report.append("LARGEST_LINES")
for no,line in largest:
    compact=line.replace("\t"," ")
    report.append(json.dumps({
        "line":no,
        "chars":len(line),
        "prefix":compact[:220],
        "suffix":compact[-220:] if len(compact)>220 else ""
    },ensure_ascii=False))
report.append("")

# Rough tag block sizes
for tag in ("script","style"):
    blocks=list(re.finditer(fr'<{tag}\b[^>]*>(.*?)</{tag}>',text,re.I|re.S))
    report.append(f"{tag}_blocks={len(blocks)}")
    for idx,m in enumerate(sorted(blocks,key=lambda m:len(m.group(1)),reverse=True)[:10],1):
        body=m.group(1)
        report.append(json.dumps({
            "tag":tag,"rank":idx,"chars":len(body),
            "start_line":text.count("\n",0,m.start())+1,
            "prefix":body.lstrip()[:180].replace("\n"," ")
        },ensure_ascii=False))
report.append("")

# Frequent identifiers / likely route-data markers
markers=[
    "DONG_ROUTE","ROUTE_CACHE","SERVICE_ZONE","route","routes","coordinates",
    "GeoJSON","FeatureCollection","base64","ADMIN_ZONE","RURAL_ROUTE"
]
report.append("MARKER_COUNTS")
for k in markers:
    report.append(f"{k}={text.count(k)}")

# Potential savings by externalizing unique data URIs
unique={}
for m in pat.finditer(text):
    mime=m.group(1); b64=m.group(2)
    try: sha=hashlib.sha256(base64.b64decode(b64,validate=False)).hexdigest()
    except Exception: sha=hashlib.sha256(b64.encode()).hexdigest()
    unique[(mime,sha)]=m.group(0)
replacement_total=0
for (mime,sha),uri in unique.items():
    replacement_total += len(uri)-len(f"assets/embedded-{sha[:16]}.bin")
report.append("")
report.append(f"estimated_index_savings_externalize_unique_data_uris={replacement_total}")
report.append(f"estimated_index_after_externalize={len(raw)-replacement_total}")

Path("tools/index-size-report.txt").write_text("\n".join(report)+"\n",encoding="utf-8")
print("\n".join(report[:12]))
