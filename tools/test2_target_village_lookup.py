import asyncio,json,time
from pathlib import Path
from playwright.async_api import async_playwright
URL="https://yongseongk94.github.io/cjwaste/cjwaste-test2/"
OUT=Path("tools/test2-target-village-lookup.json")
QUERIES=[
 "청주시 청원구 내수읍 비중리 마을회관",
 "청주시 청원구 내수읍 비중리 경로당",
 "청주시 청원구 오창읍 유리 마을회관",
 "청주시 청원구 오창읍 유리 경로당",
]
async def main():
 out={"startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"queries":{}}
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True)
  page=await browser.new_page(viewport={"width":1280,"height":900})
  await page.goto(URL+"?target_lookup="+str(int(time.time())),wait_until="domcontentloaded",timeout=90000)
  await page.wait_for_function("() => !!window.kakao && typeof places!=='undefined' && !!places && typeof ensureTestAdminBoundaryLoad==='function'",timeout=90000)
  await page.evaluate("async()=>{await ensureTestAdminBoundaryLoad();}")
  for q in QUERIES:
   rows=await page.evaluate("""q=>new Promise(resolve=>{
     places.keywordSearch(q,(rows,status)=>resolve({
       status:String(status||''),
       rows:(rows||[]).slice(0,15).map(r=>({
         name:r.place_name||'',address:r.address_name||'',road:r.road_address_name||'',
         lat:+r.y,lng:+r.x,
         district:(()=>{try{return routePointAnyDistrict({lat:+r.y,lng:+r.x,address:r.address_name||r.road_address_name||''})}catch(e){return ''}})(),
         ri:(()=>{try{const d=routePointAnyDistrict({lat:+r.y,lng:+r.x,address:r.address_name||r.road_address_name||''});return localRiAtPoint(d,+r.y,+r.x)?.riName||''}catch(e){return ''}})()
       }))
     }));
   })""",q)
   out["queries"][q]=rows
  await browser.close()
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(out,ensure_ascii=False,indent=2))
asyncio.run(main())
