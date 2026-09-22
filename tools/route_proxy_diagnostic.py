import json,urllib.request,urllib.error,math
from pathlib import Path

url="https://cjwaste-route.yseong22.workers.dev/route"
pairs=[
  ("ochang-west-east",(127.380555707194,36.7476151193569),(127.4435,36.7165)),
  ("naesu-east",(127.568929431992,36.6894591403847),(127.605657843844,36.7182037046216)),
  ("ochang-cross",(127.40557544907274,36.734853785340896),(127.4730,36.7060)),
]

def call(a,b,avoid=None):
    payload={
      "points":[
        {"x":a[0],"y":a[1],"name":"A"},
        {"x":b[0],"y":b[1],"name":"B"}
      ],
      "priority":"RECOMMEND"
    }
    if avoid is not None:
        payload["avoid"]=avoid
    req=urllib.request.Request(
      url,
      data=json.dumps(payload).encode("utf-8"),
      headers={"Content-Type":"application/json","User-Agent":"cjwaste-diagnostic/1.0"},
      method="POST"
    )
    try:
      with urllib.request.urlopen(req,timeout=45) as r:
        body=r.read().decode("utf-8","replace")
        data=json.loads(body or "{}")
        return {"status":r.status,"data":data}
    except urllib.error.HTTPError as e:
      return {"status":e.code,"body":e.read().decode("utf-8","replace")[:2000]}
    except Exception as e:
      return {"status":None,"error":repr(e)}

def length(path):
    if not isinstance(path,list): return 0.0
    total=0.0
    for i in range(1,len(path)):
      try:
        x1,y1=path[i-1];x2,y2=path[i]
        dy=(y2-y1)*111
        dx=(x2-x1)*88
        total+=math.hypot(dx,dy)
      except Exception: pass
    return total

out={"url":url,"pairs":[]}
for name,a,b in pairs:
    normal=call(a,b)
    avoid=call(a,b,"motorway")
    np=(normal.get("data") or {}).get("path") or []
    ap=(avoid.get("data") or {}).get("path") or []
    out["pairs"].append({
      "name":name,"normalStatus":normal.get("status"),"avoidStatus":avoid.get("status"),
      "normalPoints":len(np),"avoidPoints":len(ap),
      "normalKm":round(length(np),4),"avoidKm":round(length(ap),4),
      "identical":np==ap,
      "normalFirstLast":[np[0],np[-1]] if len(np)>=2 else None,
      "avoidFirstLast":[ap[0],ap[-1]] if len(ap)>=2 else None,
      "normalError":normal.get("error") or normal.get("body"),
      "avoidError":avoid.get("error") or avoid.get("body"),
    })
Path("tools/route-proxy-diagnostic.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2))
