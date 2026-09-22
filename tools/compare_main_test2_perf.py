import asyncio, json, time
from pathlib import Path
from playwright.async_api import async_playwright

PAGES={
  "main":"https://yongseongk94.github.io/cjwaste/",
  "test2":"https://yongseongk94.github.io/cjwaste/cjwaste-test2/"
}
OUT=Path("tools/main-vs-test2-perf-report.json")

async def wait_ready(page):
    await page.wait_for_function("() => !!window.kakao && typeof setLayer==='function' && typeof routeItemPolylines==='function'",timeout=90000)

async def cdp_metrics(page):
    ses=await page.context.new_cdp_session(page)
    await ses.send("Performance.enable")
    m=await ses.send("Performance.getMetrics")
    vals={x["name"]:x["value"] for x in m.get("metrics",[])}
    await ses.detach()
    keep=["TaskDuration","ScriptDuration","LayoutDuration","RecalcStyleDuration","JSHeapUsedSize","Nodes","LayoutCount","RecalcStyleCount"]
    return {k:vals.get(k) for k in keep}

async def route_state(page):
    return await page.evaluate("""() => {
      const safe=(fn,f=null)=>{try{return fn()}catch(e){return f}};
      const out={};
      for(const type of ['general','recycle']){
        const items=safe(()=>dongRouteOverlays[type]||[],[]);
        const lines=items.flatMap(i=>safe(()=>routeItemPolylines(i),[]));
        out[type]={items:items.length,polylines:lines.length,visible:lines.filter(p=>safe(()=>p.getMap()===map,false)).length};
      }
      const routeKeys={};
      for(const type of ['general','recycle']){
        routeKeys[type]=(safe(()=>dongRouteOverlays[type]||[],[])).map(i=>({
          vehicle:i.vehicle||'', day:i.day||'', provider:i.provider||routeCompany(i.vehicle)||'',
          districts:safe(()=>routeAllowedDistricts(i),[]), fromBundle:!!i.fromBundle,
          segments:(i.segments||[]).length
        })).sort((a,b)=>(a.vehicle+'|'+a.day+'|'+a.districts.join(',')).localeCompare(b.vehicle+'|'+b.day+'|'+b.districts.join(','),'ko'));
      }
      return {
        activeLayer:safe(()=>activeLayer,''),
        district:safe(()=>currentLegalEmd||currentDistrict,''),
        ri:safe(()=>currentLegalRi,''),
        routeItems:out,
        routeKeys,
        zones:{
          general:safe(()=>serviceZoneOverlays.general.length,0),
          recycle:safe(()=>serviceZoneOverlays.recycle.length,0)
        }
      };
    }""")

async def one(browser,name,url):
    context=await browser.new_context(viewport={"width":1440,"height":1000})
    page=await context.new_page()
    req=[]
    errs=[]
    cons=[]
    page.on("request",lambda r:req.append(r.url))
    page.on("response",lambda r:errs.append({"status":r.status,"url":r.url}) if r.status>=400 else None)
    page.on("pageerror",lambda e:cons.append("pageerror:"+str(e)))
    page.on("console",lambda m:cons.append("console:"+m.text) if m.type=="error" else None)

    t0=time.perf_counter()
    resp=await page.goto(url+"?perfcompare="+str(int(time.time()*1000)),wait_until="domcontentloaded",timeout=90000)
    await wait_ready(page)
    ready_ms=round((time.perf_counter()-t0)*1000)

    # 결과지도 표시
    t=time.perf_counter()
    await page.evaluate("() => showResult()")
    await page.wait_for_timeout(1500)
    show_ms=round((time.perf_counter()-t)*1000)
    state_general=await route_state(page)

    # 재활용 전환
    t=time.perf_counter()
    await page.locator('.layer-btn[data-layer="recycle"]').click()
    await page.wait_for_timeout(800)
    recycle_ms=round((time.perf_counter()-t)*1000)
    state_recycle=await route_state(page)

    # 생활 복귀
    await page.locator('.layer-btn[data-layer="general"]').click()
    await page.wait_for_timeout(500)

    before_search=len(req)
    t=time.perf_counter()
    # 랜딩 폼을 이용해 동일 주소 검색
    await page.evaluate("""() => {
      const landing=document.getElementById('landing');
      if(landing)landing.classList.remove('hidden');
      const input=document.getElementById('landingInput');
      if(input)input.value='청주시 청원구 내수읍 저곡리';
      const form=document.getElementById('landingForm');
      if(form)form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
    }""")
    try:
      await page.wait_for_function("() => currentLegalRi==='저곡리' || document.getElementById('selectedAddress')?.textContent?.includes('저곡')",timeout=45000)
    except Exception:
      pass
    await page.wait_for_timeout(1500)
    search_ms=round((time.perf_counter()-t)*1000)
    state_search=await route_state(page)
    after_search=len(req)

    metrics=await cdp_metrics(page)

    def count(substr, arr=req):
      return sum(1 for x in arr if substr in x)
    result={
      "name":name,"url":url,"httpStatus":resp.status if resp else None,
      "timingMs":{"ready":ready_ms,"showResultPlus1500":show_ms,"recycleSwitchPlus800":recycle_ms,"addressSearchPlus1500":search_ms},
      "requests":{
        "total":len(req),
        "duringAddressSearch":after_search-before_search,
        "kakaoLocal":count("dapi.kakao.com"),
        "routeProxy":count("cjwaste-route.yseong22.workers.dev"),
        "serviceZoneJson":count("service-zones"),
        "precomputedJson":count("precomputed-routes")
      },
      "errors":{"http":errs,"console":cons},
      "states":{"general":state_general,"recycle":state_recycle,"afterSearch":state_search},
      "metrics":metrics
    }
    await context.close()
    return result

async def main():
  out={"startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
  async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    for name,url in PAGES.items():
      out[name]=await one(browser,name,url)
    await browser.close()
  OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
  print(json.dumps(out,ensure_ascii=False,indent=2))

asyncio.run(main())
