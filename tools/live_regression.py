import asyncio, json, time
from collections import Counter
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://yongseongk94.github.io/cjwaste/"
REPORT=Path("tools/live-regression-report-v2.json")

async def idb_summary(page):
    return await page.evaluate("""async () => await new Promise(resolve=>{
      try{
        const req=indexedDB.open('cjwaste-dong-route-cache',1);
        req.onsuccess=()=>{
          const db=req.result;
          if(!db.objectStoreNames.contains('routes')){resolve({count:0,routeKeys:0,zoneKeys:0});return}
          const tx=db.transaction('routes','readonly');
          const r=tx.objectStore('routes').getAllKeys();
          r.onsuccess=()=>{
            const keys=(r.result||[]).map(String);
            resolve({
              count:keys.length,
              routeKeys:keys.filter(k=>k.startsWith('v76-layer-visibility-refresh|')).length,
              zoneKeys:keys.filter(k=>k.startsWith('zone-v77-')).length
            });
          };
          r.onerror=()=>resolve({count:-1,routeKeys:-1,zoneKeys:-1});
        };
        req.onerror=()=>resolve({count:-2,routeKeys:-2,zoneKeys:-2});
      }catch(e){resolve({count:-3,error:String(e),routeKeys:-3,zoneKeys:-3})}
    })""")

async def snap(page):
    return await page.evaluate("""() => {
      const safe=(fn,f=null)=>{try{return fn()}catch(e){return f}};
      const specs=safe(()=>allDongRouteSpecs(),[]);
      const specRows=specs.map(s=>({
        type:s.type,vehicle:s.vehicle,day:s.day,scopeKind:s.scopeKind||'',
        scope:routeScopeSignature(s),districts:routeAllowedDistricts(s),
        exists:!!existingDongRouteOverlay(s)
      }));
      const missing=specRows.filter(x=>!x.exists);
      const routeStats={};
      for(const type of ['general','recycle']){
        const items=safe(()=>dongRouteOverlays[type]||[],[]);
        const keys=items.map(x=>[x.type,x.vehicle,x.day,routeScopeSignature(x)].join('|'));
        routeStats[type]={
          total:items.length,
          unique:new Set(keys).size,
          duplicateCount:items.length-new Set(keys).size
        };
      }
      const zoneStats={};
      for(const type of ['general','recycle']){
        const zones=safe(()=>serviceZoneOverlays[type]||[],[]).filter(z=>!z.manual);
        const byDistrict={};
        for(const z of zones){
          const d=canonicalDistrict(z.district||'')||'(none)';
          byDistrict[d]=(byDistrict[d]||0)+1;
        }
        zoneStats[type]={total:zones.length,byDistrict};
      }
      const bundleSrc=document.getElementById('bundledPrecomputed')?.dataset?.src||'';
      const bundlePerf=performance.getEntriesByType('resource')
        .filter(e=>bundleSrc&&e.name.includes(bundleSrc))
        .map(e=>({transferSize:e.transferSize||0,encodedBodySize:e.encodedBodySize||0,decodedBodySize:e.decodedBodySize||0,duration:e.duration||0}));
      const failed=safe(()=>window.__CJWASTE_ROUTE_PROXY_FAILED_LEGS||[],[]);
      return {
        href:location.href,
        title:document.title,
        kakaoLoaded:!!window.kakao,
        precomputeReady:window.__CJWASTE_PRECOMPUTE_READY===true,
        bundleSrc,bundlePerf,
        bundleHydrated:safe(()=>bundledPrecomputedHydrated,false),
        routeSpecCount:specRows.length,
        existingSpecCount:specRows.length-missing.length,
        missingSpecCount:missing.length,
        missingSpecs:missing.slice(0,60),
        routeStats,
        zoneStats,
        serviceZoneBuilt:safe(()=>({...serviceZoneBuilt}),{}),
        serviceZoneCacheHydrated:safe(()=>({...serviceZoneCacheHydrated}),{}),
        failedLegCount:failed.length,
        failedLegs:failed.slice(-25),
        limits:{
          ochang:safe(()=>routeMatchLimitKm('오창읍')),
          naesu:safe(()=>routeMatchLimitKm('내수읍')),
          bugi:safe(()=>routeMatchLimitKm('북이면')),
          dong:safe(()=>routeMatchLimitKm('율량사천동'))
        },
        activeLayer:safe(()=>activeLayer),
        selectedDistrict:document.getElementById('selectedDistrict')?.textContent||'',
        selectedAddress:document.getElementById('selectedAddress')?.textContent||'',
        generalBadge:document.getElementById('generalBadge')?.textContent||'',
        recycleBadge:document.getElementById('recycleBadge')?.textContent||''
      };
    }""")

async def wait_ready_or(page, seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:
            if await page.evaluate("() => window.__CJWASTE_PRECOMPUTE_READY===true"):
                return True
        except Exception:
            pass
        await page.wait_for_timeout(2000)
    return False

async def main():
    out={
      "url":URL,
      "startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
      "responses":{},
      "pageErrors":[],
      "cold":{},"warm":{},"checks":{}
    }
    status_counts=Counter()
    status_urls={}

    async with async_playwright() as p:
      browser=await p.chromium.launch(headless=True)
      ctx=await browser.new_context(viewport={"width":1440,"height":1000})
      page=await ctx.new_page()
      page.on("pageerror",lambda exc: out["pageErrors"].append(str(exc)))

      def on_response(resp):
        if resp.status>=400:
          status_counts[str(resp.status)]+=1
          status_urls.setdefault(str(resp.status),[])
          if len(status_urls[str(resp.status)])<20:
            status_urls[str(resp.status)].append(resp.url)
      page.on("response",on_response)

      # Cold browser
      resp=await page.goto(URL+"?regression=v2-cold",wait_until="domcontentloaded",timeout=90000)
      out["cold"]["httpStatus"]=resp.status if resp else None
      await page.wait_for_function("() => !!window.kakao && typeof allDongRouteSpecs==='function'",timeout=90000)

      # Search first, then exercise layer buttons (avoids landing-overlay false negative).
      try:
        await page.locator('#landingInput').fill("청주시 청원구 상당로 314")
        await page.locator('#landingForm button[type="submit"]').click()
        await page.wait_for_function("""() => document.getElementById('landing')?.classList.contains('hidden') &&
          !(document.getElementById('selectedDistrict')?.textContent||'').includes('확인 중')""",timeout=60000)
        await page.wait_for_timeout(1500)
        await page.locator('.layer-btn[data-layer="recycle"]').click()
        await page.wait_for_timeout(300)
        recycle_layer=await page.evaluate("() => activeLayer")
        await page.locator('.layer-btn[data-layer="general"]').click()
        await page.wait_for_timeout(300)
        general_layer=await page.evaluate("() => activeLayer")
        out["checks"]["layerSwitch"]={"recycle":recycle_layer,"general":general_layer}
      except Exception as e:
        out["checks"]["layerSwitchError"]=repr(e)

      out["cold"]["readyWithin180s"]=await wait_ready_or(page,180)
      out["cold"]["snapshot"]=await snap(page)
      out["cold"]["idb"]=await idb_summary(page)

      # Same browser / same IndexedDB.
      before_counts=dict(status_counts)
      resp2=await page.goto(URL+"?regression=v2-warm",wait_until="domcontentloaded",timeout=90000)
      out["warm"]["httpStatus"]=resp2.status if resp2 else None
      await page.wait_for_function("() => !!window.kakao && typeof allDongRouteSpecs==='function'",timeout=90000)
      out["warm"]["readyWithin90s"]=await wait_ready_or(page,90)
      out["warm"]["snapshot"]=await snap(page)
      out["warm"]["idb"]=await idb_summary(page)
      out["warm"]["newHttpErrors"]={k:status_counts[k]-before_counts.get(k,0) for k in status_counts if status_counts[k]-before_counts.get(k,0)}

      await browser.close()

    out["responses"]={"errorStatusCounts":dict(status_counts),"sampleErrorUrls":status_urls}
    c=out["cold"]["snapshot"]; w=out["warm"]["snapshot"]
    out["checks"].update({
      "liveHttp200":out["cold"]["httpStatus"]==200 and out["warm"]["httpStatus"]==200,
      "distance20m":all(v==0.02 for v in c.get("limits",{}).values()),
      "noColdOverlayDuplicates":all(v.get("duplicateCount")==0 for v in c.get("routeStats",{}).values()),
      "noWarmOverlayDuplicates":all(v.get("duplicateCount")==0 for v in w.get("routeStats",{}).values()),
      "scopeMappingStable":c.get("routeStats",{}).get("general",{}).get("duplicateCount")==0,
      "addressSearchReachedCheongwon":"청원구" in c.get("selectedDistrict",""),
      "layerSwitchOk":out["checks"].get("layerSwitch")=={"recycle":"recycle","general":"general"},
      "coldMissingSpecs":c.get("missingSpecCount"),
      "warmMissingSpecs":w.get("missingSpecCount"),
      "coldFailedLegs":c.get("failedLegCount"),
      "warmFailedLegs":w.get("failedLegCount"),
      "coldReady":c.get("precomputeReady"),
      "warmReady":w.get("precomputeReady")
    })
    REPORT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(out["checks"],ensure_ascii=False,indent=2))

asyncio.run(main())
