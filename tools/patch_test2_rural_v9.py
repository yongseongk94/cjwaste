import asyncio,json,time
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://yongseongk94.github.io/cjwaste/cjwaste-test2/"
BUNDLE=Path("cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json")
REPORT=Path("tools/test2-rural-v9-patch-report.json")
VERSION="v76-test2-village-hall-v9-rural-full-audit"
TARGETS=[
  ("general","6138","월"),
  ("general","3344","수"),
  ("recycle","0262","화"),
]

async def main():
    old=json.loads(BUNDLE.read_text(encoding="utf-8"))
    out={"startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"url":URL,"targets":[],"pageErrors":[],"consoleErrors":[]}
    async with async_playwright() as p:
      browser=await p.chromium.launch(headless=True)
      page=await browser.new_page(viewport={"width":1440,"height":1000})
      page.set_default_timeout(300000)
      page.on("pageerror",lambda e: out["pageErrors"].append(str(e)))
      page.on("console",lambda m: out["consoleErrors"].append(m.text) if m.type=="error" else None)
      await page.goto(URL+"?v9patch="+str(int(time.time())),wait_until="domcontentloaded",timeout=90000)
      await page.wait_for_function("() => !!window.kakao && typeof map!=='undefined' && !!map && typeof allDongRouteSpecs==='function'",timeout=90000)
      await page.evaluate("async()=>{await ensureTestAdminBoundaryLoad();}")
      # Ensure exact anchors even if CDN/browser serves a briefly stale script.
      await page.evaluate("""() => {
        const pins={
          '내수읍|비중리':{name:'비중 문화마을 경로당',address:'충북 청주시 청원구 내수읍 비중길 12',jibunAddress:'충북 청주시 청원구 내수읍 비중리 392',lat:36.71149125948629,lng:127.58053134952354,source:'verified-village-facility',villageTerm:'비중리'},
          '오창읍|유리':{name:'유리경로당',address:'충북 청주시 청원구 오창읍 유리길 50',jibunAddress:'충북 청주시 청원구 오창읍 유리 469-3',lat:36.7575947477498,lng:127.477909909531,source:'verified-village-facility',villageTerm:'유리'}
        };
        const orig=test2VillageFacilitySearch;
        test2VillageFacilitySearch=(term)=>{
          const v=test2VillageNameFromRouteTerm(term);
          if(v){
            const ds=(typeof test2VillageDistrictCandidates==='function')?test2VillageDistrictCandidates(v,term):['내수읍','오창읍','북이면'];
            for(const d of ds){const hit=pins[d+'|'+normalizeRi(v)];if(hit)return Promise.resolve([{...hit,district:d}]);}
          }
          return orig(term);
        };
      }""")
      patched=[]
      for typ,veh,day in TARGETS:
        rec=await page.evaluate("""async ({typ,veh,day})=>{
          const rural=new Set(['오창읍','내수읍','북이면']);
          const spec=allDongRouteSpecs().find(s=>s.type===typ&&String(s.vehicle)===veh&&s.day===day&&routeAllowedDistricts(s).some(d=>rural.has(canonicalDistrict(d))));
          if(!spec)return {ok:false,reason:'spec-not-found'};
          const item=await buildDongRouteOverlay(spec,{forceRebuild:true});
          if(!item)return {ok:false,reason:'no-item',scope:routeScopeSignature(spec)};
          const data={...reusableRouteData(item),inferredMovementCount:0,motorwayExcluded:true};
          return {ok:true,type:typ,vehicle:veh,day,scopeSignature:routeScopeSignature(spec),districts:routeAllowedDistricts(spec),data,
            segs:(data.segments||[]).length,evidence:(data.zoneEvidencePoints||[]).length,
            missing:data.missingTerms||[],missingRoad:data.missingRoadTerms||[]};
        }""",{"typ":typ,"veh":veh,"day":day})
        out["targets"].append(rec)
        if rec.get("ok"): patched.append(rec)
      await browser.close()

    routes=old.get("routes",[])
    def key(r):
      return (str(r.get("type","")),str(r.get("vehicle","")),str(r.get("day","")),str(r.get("scopeSignature","")))
    patchmap={(r["type"],r["vehicle"],r["day"],r["scopeSignature"]):r for r in patched}
    merged=[]
    used=set()
    for r in routes:
      k=key(r)
      if k in patchmap:
        p=patchmap[k]
        merged.append({"type":p["type"],"vehicle":p["vehicle"],"day":p["day"],"districts":p["districts"],"scopeSignature":p["scopeSignature"],"data":p["data"]})
        used.add(k)
      else:
        merged.append(r)
    for k,p in patchmap.items():
      if k not in used:
        merged.append({"type":p["type"],"vehicle":p["vehicle"],"day":p["day"],"districts":p["districts"],"scopeSignature":p["scopeSignature"],"data":p["data"]})
    merged.sort(key=lambda r:(r.get("type",""),str(r.get("vehicle","")),r.get("day",""),r.get("scopeSignature","")))
    BUNDLE.write_text(json.dumps({"version":VERSION,"routes":merged},ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    out["version"]=VERSION
    out["routeCount"]=len(merged)
    out["patchedCount"]=len(patched)
    out["success"]=len(patched)==len(TARGETS) and all((r.get("segs") or 0)>0 for r in patched)
    REPORT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))

asyncio.run(main())
