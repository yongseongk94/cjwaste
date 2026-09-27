import asyncio,json,time
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://yongseongk94.github.io/cjwaste/cjwaste-test2/"
OUT=Path("tools/test2-rural-route-audit-report.json")
TARGET=["3344","6138","6544","0262"]

async def main():
  out={"startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"url":URL,"errors":[]}
  async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    page=await browser.new_page(viewport={"width":1440,"height":1000})
    page.on("pageerror",lambda e: out["errors"].append("page:"+str(e)))
    page.on("console",lambda m: out["errors"].append("console:"+m.text) if m.type=="error" else None)
    await page.goto(URL+"?ruralaudit="+str(int(time.time())),wait_until="domcontentloaded",timeout=90000)
    await page.wait_for_function("() => !!window.kakao && typeof allDongRouteSpecs==='function' && typeof bundleRouteRecordSpec==='function' && typeof stripInferredTransitSegments==='function'",timeout=90000)
    data=await page.evaluate("""async (target)=>{
      const bundle=await loadExternalBundledPrecomputedData();
      const specs=allDongRouteSpecs();
      const rows=[];
      const liveBefore={};
      for(const vehicle of target){
        liveBefore[vehicle]=(dongRouteOverlays.general||[]).concat(dongRouteOverlays.recycle||[])
          .filter(x=>String(x.vehicle)===vehicle)
          .map(x=>({type:x.type,day:x.day,scope:routeScopeSignature(x),districts:routeAllowedDistricts(x),segments:(x.segments||[]).length,fromBundle:!!x.fromBundle}));
      }
      for(const vehicle of target){
        const routeRecords=(bundle.routes||[]).filter(r=>String(r.vehicle)===vehicle);
        const specRows=specs.filter(s=>String(s.vehicle)===vehicle).map(s=>({
          type:s.type,vehicle:s.vehicle,day:s.day,scopeKind:s.scopeKind,
          districts:routeAllowedDistricts(s),scopeSignature:routeScopeSignature(s),
          raw:String(s.raw||'').slice(0,500)
        }));
        for(const r of routeRecords){
          const spec=bundleRouteRecordSpec(r,specs);
          const stripped=stripInferredTransitSegments(r.data||{});
          const audit=spec?finalRouteCoordinateAudit(spec,stripped):null;
          const existing=spec?existingDongRouteOverlay(spec):null;
          rows.push({
            record:{type:r.type,vehicle:r.vehicle,day:r.day,districts:r.districts||[],scopeSignature:r.scopeSignature||'',districtLabel:r.data?.districtLabel||'',segments:(r.data?.segments||[]).length,inferred:Number(r.data?.inferredMovementCount)||0,strippedSegments:(stripped.segments||[]).length,evidence:(r.data?.zoneEvidencePoints||[]).length,motorwayExcluded:!!r.data?.motorwayExcluded},
            mappedSpec:spec?{type:spec.type,vehicle:spec.vehicle,day:spec.day,scopeKind:spec.scopeKind,districts:routeAllowedDistricts(spec),scopeSignature:routeScopeSignature(spec)}:null,
            patch:spec?routeNeedsPatchedGeometry(spec):null,
            audit,
            existing:existing?{scope:routeScopeSignature(existing),segments:(existing.segments||[]).length,fromBundle:!!existing.fromBundle}:null
          });
        }
        rows.push({vehicle,specRows,recordCount:routeRecords.length});
      }
      await hydrateExternalBundledPrecomputedData();
      await new Promise(r=>setTimeout(r,1000));
      const liveAfter={};
      for(const vehicle of target){
        liveAfter[vehicle]=(dongRouteOverlays.general||[]).concat(dongRouteOverlays.recycle||[])
          .filter(x=>String(x.vehicle)===vehicle)
          .map(x=>({type:x.type,day:x.day,scope:routeScopeSignature(x),districts:routeAllowedDistricts(x),segments:(x.segments||[]).length,fromBundle:!!x.fromBundle}));
      }
      return {bundleVersion:bundle.version||'',routeCount:(bundle.routes||[]).length,rows,liveBefore,liveAfter};
    }""",TARGET))
    out.update(data)
    await browser.close()
  OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
  print(json.dumps({"bundleVersion":out.get("bundleVersion"),"errors":out["errors"],"rows":len(out.get("rows",[]))},ensure_ascii=False))

asyncio.run(main())
