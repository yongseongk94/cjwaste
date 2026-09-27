import asyncio,json,time,re
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://yongseongk94.github.io/cjwaste/cjwaste-test2/"
BUNDLE=Path("cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json")
INDEX=Path("cjwaste-test2/index.html")
REPORT=Path("tools/test2-bijung-spatial-fix-report.json")
OLD_VERSION="v76-test2-village-hall-v9-rural-full-audit"
NEW_VERSION="v76-test2-village-hall-v10-bijung-spatial"
BASE={"name":"비중 문화마을 경로당","address":"충북 청주시 청원구 내수읍 비중길 12","lat":36.71149125948629,"lng":127.58053134952354}

async def main():
    bundle=json.loads(BUNDLE.read_text(encoding="utf-8"))
    out={"startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"url":URL,"pageErrors":[],"consoleErrors":[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page(viewport={"width":1440,"height":1000})
        page.set_default_timeout(180000)
        page.on("pageerror",lambda e:out["pageErrors"].append(str(e)))
        page.on("console",lambda m:out["consoleErrors"].append(m.text) if m.type=="error" else None)
        await page.goto(URL+"?bijung_spatial_fix="+str(int(time.time())),wait_until="domcontentloaded",timeout=90000)
        await page.wait_for_function("() => !!window.kakao && typeof map!=='undefined' && !!map && typeof localRoadAnchorsAroundPoint==='function' && typeof fetchRoadFollowingPath==='function'",timeout=90000)
        await page.evaluate("async()=>{await ensureTestAdminBoundaryLoad();}")
        patch=await page.evaluate("""async (base)=>{
          const spec=allDongRouteSpecs().find(s=>s.type==='general'&&String(s.vehicle)==='6138'&&s.day==='월'&&routeScopeSignature(s)==='내수읍');
          if(!spec)return {ok:false,reason:'spec-not-found'};
          const p={...base,term:'비중리',district:'내수읍'};
          let anchors=await localRoadAnchorsAroundPoint(p,spec,0.65);
          anchors=(anchors||[]).filter(a=>routePointAnyDistrict(a)==='내수읍');
          if(anchors.length<2)return {ok:false,reason:'insufficient-road-anchors',anchors};
          let road=await fetchRoadFollowingPath(anchors);
          let segments=[];
          for(const seg of (road?.segments||[]))segments.push(...clipRoutePathToDistricts(seg,['내수읍']));
          // 행정리 폴리곤이 비중길 일부를 잘못 분류하는 경우가 있어, 검증된 비중리 시설점과의 실제 거리로 채택합니다.
          const nearSegs=segments.filter(seg=>(seg||[]).some(q=>routePointDistance(base,q)<=0.08));
          if(!nearSegs.length)return {ok:false,reason:'no-bijung-road-segment-near-verified-facility',anchors,segmentCount:segments.length,failedLegs:road?.failedLegs||[]};
          return {
            ok:true,
            anchors:anchors.map(a=>({name:a.name||'',address:a.address||'',lat:+a.lat,lng:+a.lng})),
            segments:nearSegs.map(seg=>seg.map(q=>({lat:+q.lat,lng:+q.lng}))),
            distance:+road?.distance||0,
            failedLegs:road?.failedLegs||[]
          };
        }""",BASE)
        await browser.close()

    out["patch"]=patch
    if not patch.get("ok"):
        REPORT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
        raise RuntimeError("Bijung route patch failed: "+str(patch))

    target=None
    for r in bundle.get("routes",[]):
        if r.get("type")=="general" and str(r.get("vehicle"))=="6138" and r.get("day")=="월" and r.get("scopeSignature")=="내수읍":
            target=r;break
    if target is None: raise RuntimeError("6138 Monday Naesu route record missing")

    before=len(target.get("data",{}).get("segments",[]))
    existing=target.setdefault("data",{}).setdefault("segments",[])
    def sig(seg):
        if not seg:return ""
        a,b=seg[0],seg[-1]
        return f"{a.get('lat',0):.6f},{a.get('lng',0):.6f}|{b.get('lat',0):.6f},{b.get('lng',0):.6f}"
    seen={sig(seg) for seg in existing}
    added=0
    for seg in patch["segments"]:
        if sig(seg) not in seen:
            existing.append(seg);seen.add(sig(seg));added+=1
    target["data"]["motorwayExcluded"]=True
    target["data"]["inferredMovementCount"]=0
    target["data"]["distance"]=(float(target["data"].get("distance") or 0)+float(patch.get("distance") or 0))
    bundle["version"]=NEW_VERSION
    BUNDLE.write_text(json.dumps(bundle,ensure_ascii=False,separators=(",",":")),encoding="utf-8")

    html=INDEX.read_text(encoding="utf-8")
    html=html.replace("const DONG_ROUTE_CACHE_VERSION='"+OLD_VERSION+"';","const DONG_ROUTE_CACHE_VERSION='"+NEW_VERSION+"';")
    html=html.replace("precomputed-rural-routes-no-motorway-v1.json?v=rural-direct-v3","precomputed-rural-routes-no-motorway-v1.json?v=rural-direct-v4")
    INDEX.write_text(html,encoding="utf-8")

    out.update({"oldVersion":OLD_VERSION,"newVersion":NEW_VERSION,"segmentsBefore":before,"segmentsAdded":added,"segmentsAfter":len(existing),"success":added>0})
    REPORT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))
    if added<=0: raise RuntimeError("No Bijung segment added")

asyncio.run(main())
