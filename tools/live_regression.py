import asyncio, json, time
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://yongseongk94.github.io/cjwaste/"
REPORT=Path("tools/live-regression-report.json")

async def idb_count(page):
    return await page.evaluate("""async () => {
      return await new Promise(resolve=>{
        try{
          const req=indexedDB.open('cjwaste-dong-route-cache',1);
          req.onsuccess=()=>{
            try{
              const db=req.result;
              if(!db.objectStoreNames.contains('routes')){resolve({count:0,keys:[]});return;}
              const tx=db.transaction('routes','readonly');
              const st=tx.objectStore('routes');
              const cr=st.count();
              const kr=st.getAllKeys();
              let count=null,keys=null;
              cr.onsuccess=()=>{count=cr.result;if(keys!==null)resolve({count,keys})};
              kr.onsuccess=()=>{keys=kr.result.map(String);if(count!==null)resolve({count,keys})};
              tx.onerror=()=>resolve({count:-1,keys:[]});
            }catch(e){resolve({count:-2,error:String(e),keys:[]})}
          };
          req.onerror=()=>resolve({count:-3,error:String(req.error),keys:[]});
        }catch(e){resolve({count:-4,error:String(e),keys:[]})}
      });
    }""")

async def snapshot(page):
    return await page.evaluate("""() => {
      const safe=(fn,fallback=null)=>{try{return fn()}catch(e){return fallback}};
      const bg=getComputedStyle(document.getElementById('landing')).backgroundImage;
      const bundleEl=document.getElementById('bundledPrecomputed');
      const perf=performance.getEntriesByType('resource').map(e=>({
        name:e.name,transferSize:e.transferSize||0,encodedBodySize:e.encodedBodySize||0,
        decodedBodySize:e.decodedBodySize||0,duration:e.duration||0
      }));
      const bundleSrc=bundleEl?.dataset?.src||'';
      const bundlePerf=perf.filter(e=>bundleSrc && e.name.includes(bundleSrc));
      return {
        href:location.href,
        title:document.title,
        bundleSrc,
        bundlePerf,
        landingBg:bg,
        kakaoLoaded:!!window.kakao,
        ready:window.__CJWASTE_PRECOMPUTE_READY===true,
        routeSpecCount:safe(()=>allDongRouteSpecs().length,-1),
        routeGeneralCount:safe(()=>dongRouteOverlays.general.length,-1),
        routeRecycleCount:safe(()=>dongRouteOverlays.recycle.length,-1),
        zoneGeneralCount:safe(()=>serviceZoneOverlays.general.filter(z=>!z.manual).length,-1),
        zoneRecycleCount:safe(()=>serviceZoneOverlays.recycle.filter(z=>!z.manual).length,-1),
        ruralZoneGeneral:safe(()=>serviceZoneOverlays.general.filter(z=>['오창읍','내수읍','북이면'].includes(canonicalDistrict(z.district||''))).length,-1),
        ruralZoneRecycle:safe(()=>serviceZoneOverlays.recycle.filter(z=>['오창읍','내수읍','북이면'].includes(canonicalDistrict(z.district||''))).length,-1),
        maxAddressRouteDistanceKm:safe(()=>MAX_ADDRESS_ROUTE_DISTANCE_KM,null),
        limits:{
          ochang:safe(()=>routeMatchLimitKm('오창읍'),null),
          naesu:safe(()=>routeMatchLimitKm('내수읍'),null),
          bugi:safe(()=>routeMatchLimitKm('북이면'),null),
          dong:safe(()=>routeMatchLimitKm('율량사천동'),null)
        },
        activeLayer:safe(()=>activeLayer,null),
        activeDay:safe(()=>activeDay,null),
        selectedGeneral:safe(()=>selectedVehicle.general,null),
        selectedRecycle:safe(()=>selectedVehicle.recycle,null),
        generalBadge:document.getElementById('generalBadge')?.textContent||'',
        recycleBadge:document.getElementById('recycleBadge')?.textContent||'',
        foodBadge:document.getElementById('foodBadge')?.textContent||'',
        selectedDistrict:document.getElementById('selectedDistrict')?.textContent||'',
        selectedAddress:document.getElementById('selectedAddress')?.textContent||''
      };
    }""")

async def run():
    result={
      "url":URL,
      "startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
      "consoleErrors":[],
      "pageErrors":[],
      "requestFailures":[],
      "cold":{},
      "warm":{},
      "addressSearch":{},
      "checks":{}
    }
    async with async_playwright() as p:
      browser=await p.chromium.launch(headless=True)
      context=await browser.new_context(viewport={"width":1440,"height":1000})
      page=await context.new_page()

      page.on("console", lambda msg: result["consoleErrors"].append(msg.text) if msg.type=="error" else None)
      page.on("pageerror", lambda exc: result["pageErrors"].append(str(exc)))
      page.on("requestfailed", lambda req: result["requestFailures"].append({"url":req.url,"failure":req.failure}))

      cold_bundle_requests=[]
      page.on("request", lambda req: cold_bundle_requests.append(req.url) if "precomputed-routes-" in req.url else None)

      try:
        resp=await page.goto(URL+"?regression=cold",wait_until="domcontentloaded",timeout=90000)
        result["cold"]["httpStatus"]=resp.status if resp else None
      except Exception as e:
        result["cold"]["gotoError"]=repr(e)

      try:
        await page.wait_for_function("() => !!window.kakao && !!document.querySelector('#map')",timeout=90000)
      except Exception as e:
        result["cold"]["kakaoWaitError"]=repr(e)

      try:
        await page.wait_for_function("() => window.__CJWASTE_PRECOMPUTE_READY === true",timeout=150000)
      except Exception as e:
        result["cold"]["readyWaitError"]=repr(e)

      result["cold"]["snapshot"]=await snapshot(page)
      result["cold"]["idb"]=await idb_count(page)
      result["cold"]["bundleRequests"]=len(cold_bundle_requests)

      # UI layer switching
      try:
        await page.locator('.layer-btn[data-layer="recycle"]').click()
        await page.wait_for_timeout(500)
        recycle_active=await page.locator('.layer-btn[data-layer="recycle"]').evaluate("(e)=>e.classList.contains('active')")
        recycle_layer=await page.evaluate("() => activeLayer")
        await page.locator('.layer-btn[data-layer="general"]').click()
        await page.wait_for_timeout(500)
        general_active=await page.locator('.layer-btn[data-layer="general"]').evaluate("(e)=>e.classList.contains('active')")
        general_layer=await page.evaluate("() => activeLayer")
        result["checks"]["layerSwitch"]={
          "recycleButtonActive":recycle_active,"recycleActiveLayer":recycle_layer,
          "generalButtonActive":general_active,"generalActiveLayer":general_layer
        }
      except Exception as e:
        result["checks"]["layerSwitchError"]=repr(e)

      # Address search through live Kakao geocoder.
      try:
        inp=page.locator('#landingInput')
        await inp.fill("청주시 청원구 상당로 314")
        await page.locator('#landingForm button[type="submit"]').click()
        await page.wait_for_function("""() => {
          const l=document.getElementById('landing');
          const d=document.getElementById('selectedDistrict')?.textContent||'';
          return l?.classList.contains('hidden') && d && !d.includes('확인 중');
        }""",timeout=60000)
        await page.wait_for_timeout(4000)
        result["addressSearch"]=await snapshot(page)
        result["addressSearch"]["generalDetail"]=(await page.locator('#generalDetail').inner_text())[:1200]
        result["addressSearch"]["recycleDetail"]=(await page.locator('#recycleDetail').inner_text())[:1200]
      except Exception as e:
        result["addressSearch"]["error"]=repr(e)
        result["addressSearch"]["landingStatus"]=await page.locator('#landingStatus').inner_text()

      # Warm reload in SAME browser context. Existing IndexedDB should eliminate external route-bundle fetch.
      warm_bundle_requests=[]
      def warm_req(req):
        if "precomputed-routes-" in req.url:
          warm_bundle_requests.append(req.url)
      page.on("request",warm_req)
      try:
        resp2=await page.goto(URL+"?regression=warm",wait_until="domcontentloaded",timeout=90000)
        result["warm"]["httpStatus"]=resp2.status if resp2 else None
      except Exception as e:
        result["warm"]["gotoError"]=repr(e)
      try:
        await page.wait_for_function("() => !!window.kakao && !!document.querySelector('#map')",timeout=90000)
        await page.wait_for_function("() => window.__CJWASTE_PRECOMPUTE_READY === true",timeout=120000)
      except Exception as e:
        result["warm"]["readyWaitError"]=repr(e)
      result["warm"]["snapshot"]=await snapshot(page)
      result["warm"]["idb"]=await idb_count(page)
      result["warm"]["bundleRequests"]=len(warm_bundle_requests)

      await browser.close()

    c=result["cold"].get("snapshot",{})
    w=result["warm"].get("snapshot",{})
    layer=result["checks"].get("layerSwitch",{})
    addr=result.get("addressSearch",{})
    result["checks"].update({
      "liveHttp200":result["cold"].get("httpStatus")==200 and result["warm"].get("httpStatus")==200,
      "externalBundleReferenced":str(c.get("bundleSrc","")).startswith("data/precomputed-routes-"),
      "backgroundExternalized":"assets/landing-bg.jpg" in str(c.get("landingBg","")),
      "kakaoLoaded":c.get("kakaoLoaded") is True,
      "coldReady":c.get("ready") is True,
      "routeBundleColdLoaded":result["cold"].get("bundleRequests",0)>=1,
      "routeBundleWarmSkipped":result["warm"].get("bundleRequests",999)==0,
      "indexedDbPopulated":result["cold"].get("idb",{}).get("count",0)>=94,
      "warmIndexedDbRetained":result["warm"].get("idb",{}).get("count",0)>=94,
      "routesPresent":c.get("routeGeneralCount",0)>0 and c.get("routeRecycleCount",0)>0,
      "zonesPresent":c.get("zoneGeneralCount",0)>0 and c.get("zoneRecycleCount",0)>0,
      "ruralZonesPresent":c.get("ruralZoneGeneral",0)>0 and c.get("ruralZoneRecycle",0)>0,
      "distance20m":c.get("maxAddressRouteDistanceKm")==0.02 and all(v==0.02 for v in (c.get("limits") or {}).values()),
      "layerSwitchOk":layer.get("recycleButtonActive") and layer.get("recycleActiveLayer")=="recycle" and layer.get("generalButtonActive") and layer.get("generalActiveLayer")=="general",
      "addressSearchReachedCheongwon":"청원구" in str(addr.get("selectedDistrict","")) and "서비스 대상 아님" not in str(addr.get("selectedDistrict",""))
    })
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result["checks"],ensure_ascii=False,indent=2))

asyncio.run(run())
