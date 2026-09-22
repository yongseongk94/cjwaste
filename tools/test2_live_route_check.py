import asyncio, json, time
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://yongseongk94.github.io/cjwaste/cjwaste-test2/"
REPORT=Path("tools/test2-live-route-report.json")

async def snap(page,label):
    return await page.evaluate("""(label) => {
      const safe=(fn,f=null)=>{try{return fn()}catch(e){return f}};
      const routeItems={};
      for(const type of ['general','recycle']){
        const items=safe(()=>dongRouteOverlays[type]||[],[]);
        const polylines=items.flatMap(i=>safe(()=>routeItemPolylines(i),[]));
        routeItems[type]={
          items:items.length,
          polylines:polylines.length,
          visible:polylines.filter(p=>safe(()=>p.getMap()===map,false)).length,
          fromBundle:items.filter(i=>!!i.fromBundle).length,
          withSegments:items.filter(i=>(i.segments||[]).length>0).length
        };
      }
      return {
        label,
        href:location.href,
        activeLayer:safe(()=>activeLayer,''),
        serviceLayerState:safe(()=>({...serviceLayerState}),{}),
        currentDistrict:safe(()=>currentDistrict,''),
        currentLegalEmd:safe(()=>currentLegalEmd,''),
        currentLegalRi:safe(()=>currentLegalRi,''),
        selectedAddress:document.getElementById('selectedAddress')?.textContent||'',
        badge:document.getElementById('mapBadge')?.innerText||'',
        bundleHydrated:safe(()=>bundledPrecomputedHydrated,false),
        boundaryStarted:safe(()=>testAdminBoundaryLoadStarted,false),
        districtFeatureCount:safe(()=>districtFeatureMap.size,0),
        routeItems
      };
    }""",label)

async def main():
    out={"url":URL,"startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"pageErrors":[],"consoleErrors":[],"httpErrors":[],"snapshots":[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page(viewport={"width":1440,"height":1000})
        page.on("pageerror",lambda e: out["pageErrors"].append(str(e)))
        page.on("console",lambda m: out["consoleErrors"].append(m.text) if m.type=="error" else None)
        page.on("response",lambda r: out["httpErrors"].append({"status":r.status,"url":r.url}) if r.status>=400 else None)
        resp=await page.goto(URL+"?routecheck="+str(int(time.time())),wait_until="domcontentloaded",timeout=90000)
        out["httpStatus"]=resp.status if resp else None
        await page.wait_for_function("() => !!window.kakao && typeof setLayer==='function' && typeof routeItemPolylines==='function'",timeout=90000)

        await page.evaluate("() => showResult()")
        await page.wait_for_timeout(6000)
        out["snapshots"].append(await snap(page,"general-no-address"))

        await page.locator('.layer-btn[data-layer="recycle"]').click()
        await page.wait_for_timeout(3000)
        out["snapshots"].append(await snap(page,"recycle-no-address"))

        await page.locator('.layer-btn[data-layer="general"]').click()
        await page.evaluate("""() => {
          document.getElementById('landing').classList.remove('hidden');
          document.getElementById('landingInput').value='청주시 청원구 내수읍 저곡리';
          document.getElementById('landingForm').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
        }""")
        try:
            await page.wait_for_function("() => currentLegalRi==='저곡리' || document.getElementById('selectedAddress')?.textContent?.includes('저곡')",timeout=60000)
        except Exception:
            pass
        await page.wait_for_timeout(12000)
        out["snapshots"].append(await snap(page,"general-jeogok-after-search"))

        await page.locator('.layer-btn[data-layer="recycle"]').click()
        await page.wait_for_timeout(5000)
        out["snapshots"].append(await snap(page,"recycle-jeogok-after-search"))

        await browser.close()

    out["checks"]={
      "http200":out.get("httpStatus")==200,
      "generalVisibleBefore":out["snapshots"][0]["routeItems"]["general"]["visible"]>0,
      "recycleVisibleBefore":out["snapshots"][1]["routeItems"]["recycle"]["visible"]>0,
      "generalVisibleAfterAddress":out["snapshots"][2]["routeItems"]["general"]["visible"]>0,
      "recycleVisibleAfterAddress":out["snapshots"][3]["routeItems"]["recycle"]["visible"]>0,
    }
    REPORT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out["checks"],ensure_ascii=False,indent=2))

asyncio.run(main())
