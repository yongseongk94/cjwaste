import asyncio,json,time
from pathlib import Path
from playwright.async_api import async_playwright

PAGES={"main":"https://yongseongk94.github.io/cjwaste/","test2":"https://yongseongk94.github.io/cjwaste/cjwaste-test2/"}
POINTS={
 "오창1산단중앙":[36.7120,127.4300],
 "오창2산단_81":[36.730034575028,127.44700275],
 "오창2산단_167":[36.735893087274,127.45332092277],
 "내수_저곡리":[36.7480,127.5350],
 "북이_장양리":[36.7580,127.5450],
 "우암동_중앙":[36.6497,127.4870],
 "율량사천동_중앙":[36.6655,127.4935],
}
OUT=Path("tools/main-vs-test2-zone-point-report.json")

async def inspect(browser,name,url):
    page=await browser.new_page(viewport={"width":1440,"height":1000})
    errors=[]
    page.on("pageerror",lambda e: errors.append(str(e)))
    await page.goto(url+"?zonecompare="+str(int(time.time()*1000)),wait_until="domcontentloaded",timeout=90000)
    await page.wait_for_function("() => !!window.kakao && typeof map!=='undefined' && !!map && typeof setLayer==='function'",timeout=90000)
    await page.evaluate("() => showResult()")
    result={"errors":errors,"layers":{}}
    for typ in ["general","recycle"]:
      await page.evaluate("(t)=>{setLayer(t);}",typ)
      await page.wait_for_timeout(2200)
      vals=await page.evaluate("""({typ,points})=>{
        const out={};
        for(const [name,[lat,lng]] of Object.entries(points)){
          const raw=typeof rawServiceZonesForDistrict==='function'
            ? [...(rawServiceZones?.[typ]?.entries?.()||[])].flatMap(([d,zs])=>(zs||[]).filter(z=>{try{return pointInZonePolygon(lat,lng,z)}catch(e){return false}}).map(z=>({district:d,provider:z.provider||routeCompany(z.vehicle),vehicle:z.vehicle||'',days:z.days||[],contract:!!z.contractLayer})))
            : [];
          const disp=(serviceZoneOverlays?.[typ]||[]).filter(z=>{try{return pointInZonePolygon(lat,lng,z)}catch(e){return false}}).map(z=>({district:z.district||'',provider:z.provider||routeCompany(z.vehicle),vehicle:z.vehicle||'',days:z.days||[],contract:!!z.contractLayer,displayOnly:!!z.displayOnly,legacy:!!z.legacyDisplay}));
          out[name]={raw,display:disp};
          if(typeof insideOchang2023==='function')out[name].insideOchangIndustrial=insideOchang2023(lat,lng);
        }
        return out;
      }""",{"typ":typ,"points":POINTS})
      result["layers"][typ]=vals
    await page.close()
    return result

async def main():
  out={"startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"points":POINTS}
  async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    for n,u in PAGES.items():out[n]=await inspect(browser,n,u)
    await browser.close()
  OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
  print(json.dumps({"mainErrors":out["main"]["errors"],"test2Errors":out["test2"]["errors"]},ensure_ascii=False))
asyncio.run(main())
