import asyncio, json, time
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://yongseongk94.github.io/cjwaste/cjwaste-test2/"
OUT=Path("tools/test2-ochang2-layer-report.json")
POINTS={
  "2산단로81":[36.730034575028,127.44700275],
  "2산단로82":[36.7280632,127.4470999],
  "2산단2로32":[36.736212241894,127.44896151307],
  "2산단로167":[36.735893087274,127.45332092277],
  "2산단4로60":[36.737700456439,127.45040775662],
}

async def main():
    out={"url":URL,"startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"pageErrors":[],"consoleErrors":[],"httpErrors":[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page(viewport={"width":1440,"height":1000})
        page.on("pageerror",lambda e: out["pageErrors"].append(str(e)))
        page.on("console",lambda m: out["consoleErrors"].append(m.text) if m.type=="error" else None)
        page.on("response",lambda r: out["httpErrors"].append({"status":r.status,"url":r.url}) if r.status>=400 else None)
        resp=await page.goto(URL+"?ochang2check="+str(int(time.time())),wait_until="domcontentloaded",timeout=90000)
        out["httpStatus"]=resp.status if resp else None
        await page.wait_for_function("() => !!window.kakao && typeof insideOchang2023==='function' && !!window.CJWASTE_OCHANG2_2023 && typeof map!=='undefined' && !!map",timeout=90000)
        await page.evaluate("() => showResult()")
        await page.evaluate("""() => {
          map.setCenter(new kakao.maps.LatLng(36.7338,127.4498));
          map.setLevel(5);
          setLayer('general');
          scheduleVisibleServiceZoneMaterialization('general');
        }""")
        await page.wait_for_timeout(4000)

        out["general"]=await page.evaluate("""(points) => {
          const result={points:{},zoneCount:(serviceZoneOverlays.general||[]).length};
          for(const [name,coord] of Object.entries(points)){
            const [lat,lng]=coord;
            const hits=(serviceZoneOverlays.general||[]).filter(z=>{
              try{return pointInZonePolygon(lat,lng,z)}catch(e){return false}
            });
            result.points[name]={
              insideIndustrial:insideOchang2023(lat,lng),
              insideOchang2:pointInGeoFeature([lng,lat],OCHANG2_2023_FEATURE),
              hits:hits.map(z=>({provider:z.provider||routeCompany(z.vehicle),vehicle:z.vehicle||'',days:z.days||[],contract:!!z.contractLayer,display:!!z.displaySchedule}))
            };
          }
          return result;
        }""",POINTS)

        await page.evaluate("""() => { setLayer('recycle'); scheduleVisibleServiceZoneMaterialization('recycle'); }""")
        await page.wait_for_timeout(3500)
        out["recycle"]=await page.evaluate("""(points) => {
          const result={points:{},zoneCount:(serviceZoneOverlays.recycle||[]).length};
          for(const [name,coord] of Object.entries(points)){
            const [lat,lng]=coord;
            const hits=(serviceZoneOverlays.recycle||[]).filter(z=>{
              try{return pointInZonePolygon(lat,lng,z)}catch(e){return false}
            });
            result.points[name]={
              insideIndustrial:insideOchang2023(lat,lng),
              insideOchang2:pointInGeoFeature([lng,lat],OCHANG2_2023_FEATURE),
              hits:hits.map(z=>({provider:z.provider||routeCompany(z.vehicle),vehicle:z.vehicle||'',days:z.days||[],contract:!!z.contractLayer,display:!!z.displaySchedule}))
            };
          }
          return result;
        }""",POINTS)
        await browser.close()

    out["checks"]={
      "http200":out.get("httpStatus")==200,
      "featureLoaded":all(x["insideOchang2"] for x in out["general"]["points"].values()),
      "combinedBoundary":all(x["insideIndustrial"] for x in out["general"]["points"].values()),
      "generalLayerCovers":all(len(x["hits"])>0 for x in out["general"]["points"].values()),
      "recycleLayerCovers":all(len(x["hits"])>0 for x in out["recycle"]["points"].values()),
      "noPageErrors":len(out["pageErrors"])==0
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out["checks"],ensure_ascii=False,indent=2))

asyncio.run(main())
