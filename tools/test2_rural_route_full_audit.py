import asyncio, json, time
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://yongseongk94.github.io/cjwaste/cjwaste-test2/"
OUT=Path("tools/test2-rural-route-full-audit.json")
TARGET={"general":["3344","6138"],"recycle":["6544","0262"]}
RURAL={"오창읍","내수읍","북이면"}

async def main():
    out={"url":URL,"startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"pageErrors":[],"consoleErrors":[],"httpErrors":[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page(viewport={"width":1440,"height":1000})
        page.set_default_timeout(120000)
        page.on("pageerror",lambda e: out["pageErrors"].append(str(e)))
        page.on("console",lambda m: out["consoleErrors"].append(m.text) if m.type=="error" else None)
        page.on("response",lambda r: out["httpErrors"].append({"status":r.status,"url":r.url}) if r.status>=400 else None)
        resp=await page.goto(URL+"?full_rural_audit="+str(int(time.time())),wait_until="domcontentloaded",timeout=90000)
        out["httpStatus"]=resp.status if resp else None
        await page.wait_for_function("() => !!window.kakao && typeof map!=='undefined' && !!map && typeof ensureTestAdminBoundaryLoad==='function'",timeout=90000)
        await page.evaluate("() => showResult()")
        await page.evaluate("async()=>{await ensureTestAdminBoundaryLoad(); await hydrateExternalBundledPrecomputedData();}")
        await page.wait_for_timeout(1500)

        result=await page.evaluate("""({TARGET,RURAL})=>{
          const rural=new Set(RURAL);
          const officialName=(ri)=>{
            const v=normalizeRi(ri||'');
            if(v==='빛화산리'||v==='꽃화산리')return '화산리';
            if(/^장양[123]리$/.test(v))return '장양리';
            if(/^영하\d+리$/.test(v))return '영하리';
            return v;
          };
          const pointRi=(district,p)=>{
            try{return normalizeRi(localRiAtPoint(district,+p.lat,+p.lng)?.riName||'')}catch(e){return ''}
          };
          const itemPoints=(item)=>{
            const pts=[];
            for(const seg of (item?.segments||[]))for(const p of (seg||[]))pts.push(p);
            for(const p of (item?.zoneEvidencePoints||[]))pts.push(p);
            return pts;
          };
          const result={targets:{},expected:[],summary:{}};

          for(const [type,vehicles] of Object.entries(TARGET)){
            result.targets[type]={};
            for(const vehicle of vehicles){
              const rows=[];
              for(const day of ['월','화','수','목','금']){
                const items=(dongRouteOverlays[type]||[]).filter(i=>String(i.vehicle)===vehicle&&i.day===day);
                rows.push({
                  day,
                  itemCount:items.length,
                  scopes:items.map(i=>routeAllowedDistricts(i)),
                  segmentCount:items.reduce((n,i)=>n+(i.segments||[]).length,0),
                  polylineCount:items.reduce((n,i)=>n+routeItemPolylines(i).length,0),
                  evidenceCount:items.reduce((n,i)=>n+(i.zoneEvidencePoints||[]).length,0),
                  missingTerms:[...new Set(items.flatMap(i=>i.missingTerms||[]))],
                  missingRoadTerms:[...new Set(items.flatMap(i=>i.missingRoadTerms||[]))],
                  outOfCheongwonTerms:[...new Set(items.flatMap(i=>i.outOfCheongwonTerms||[]))]
                });
              }
              result.targets[type][vehicle]=rows;
            }
          }

          for(const [type,vehicles] of Object.entries(TARGET)){
            for(const day of ['월','화','수','목','금']){
              for(const rec of (DIRECT_RI_DAYS?.[type]?.[day]||[])){
                const [district,riRaw]=String(rec.key||'').split('|');
                if(!rural.has(district))continue;
                for(const vehicle of vehicles){
                  if(!(rec.vehicles||[]).map(String).includes(vehicle))continue;
                  const expectedRi=officialName(riRaw);
                  const items=(dongRouteOverlays[type]||[]).filter(i=>
                    String(i.vehicle)===vehicle&&i.day===day&&routeAllowedDistricts(i).includes(district)
                  );
                  const points=items.flatMap(itemPoints);
                  const actualRis=[...new Set(points.map(p=>pointRi(district,p)).filter(Boolean))];
                  const covered=actualRis.includes(expectedRi);
                  result.expected.push({type,vehicle,day,district,ri:riRaw,officialRi:expectedRi,covered,actualRis,
                    itemCount:items.length,segmentCount:items.reduce((n,i)=>n+(i.segments||[]).length,0),
                    evidenceCount:items.reduce((n,i)=>n+(i.zoneEvidencePoints||[]).length,0)});
                }
              }
            }
          }

          for(const district of RURAL){
            const rows=result.expected.filter(x=>x.district===district);
            result.summary[district]={
              expected:rows.length,
              covered:rows.filter(x=>x.covered).length,
              missing:rows.filter(x=>!x.covered),
              byType:{
                general:{expected:rows.filter(x=>x.type==='general').length,covered:rows.filter(x=>x.type==='general'&&x.covered).length},
                recycle:{expected:rows.filter(x=>x.type==='recycle').length,covered:rows.filter(x=>x.type==='recycle'&&x.covered).length}
              }
            };
          }
          result.allTargetDaysPresent=Object.values(result.targets).every(byVehicle=>Object.values(byVehicle).every(rows=>rows.every(r=>r.itemCount>0&&r.segmentCount>0&&r.polylineCount>0)));
          result.allRiCovered=Object.values(result.summary).every(s=>s.expected===s.covered);
          result.totalExpected=result.expected.length;
          result.totalCovered=result.expected.filter(x=>x.covered).length;
          return result;
        }""",{"TARGET":TARGET,"RURAL":list(RURAL)})
        await browser.close()

    out.update(result)
    out["checks"]={
      "http200":out.get("httpStatus")==200,
      "allTargetDaysPresent":result.get("allTargetDaysPresent",False),
      "allRiCovered":result.get("allRiCovered",False),
      "noPageErrors":len(out["pageErrors"])==0
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"checks":out["checks"],"summary":out.get("summary"),"totalExpected":out.get("totalExpected"),"totalCovered":out.get("totalCovered")},ensure_ascii=False,indent=2))

asyncio.run(main())
