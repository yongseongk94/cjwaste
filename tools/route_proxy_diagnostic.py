import json,urllib.request,urllib.error
from pathlib import Path

url="https://cjwaste-route.yseong22.workers.dev/route"
payload={
  "points":[
    {"x":127.4866,"y":36.6515,"name":"A"},
    {"x":127.4920,"y":36.6550,"name":"B"}
  ],
  "priority":"RECOMMEND"
}
req=urllib.request.Request(
  url,
  data=json.dumps(payload).encode("utf-8"),
  headers={"Content-Type":"application/json","User-Agent":"cjwaste-diagnostic/1.0"},
  method="POST"
)
out={"url":url}
try:
  with urllib.request.urlopen(req,timeout=30) as r:
    body=r.read().decode("utf-8","replace")
    out.update({"status":r.status,"body":body[:4000],"headers":dict(r.headers)})
except urllib.error.HTTPError as e:
  body=e.read().decode("utf-8","replace")
  out.update({"status":e.code,"body":body[:4000],"headers":dict(e.headers)})
except Exception as e:
  out.update({"status":None,"error":repr(e)})
Path("tools/route-proxy-diagnostic.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2))
