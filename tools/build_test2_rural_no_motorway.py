import asyncio, json, time
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://yongseongk94.github.io/cjwaste/cjwaste-test2/"
TARGET_VEHICLES={"3344","6138","6544","0262"}
OUT=Path("cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json")
REPORT=Path("tools/test2-rural-no-motorway-report.json")

async def main():
    report={"startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"url":URL,"pageErrors":[],"consoleErrors":[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page(viewport={"width":1440,"height":1000})
        page.set_default_timeout(1200000)
        page.on("pageerror",lambda e: report["pageErrors"].append(str(e)))
        page.on("console",lambda m: report["consoleErrors"].append(m.text) if m.type=="error" else None)
        await page.goto(URL+"?rural_motorway_rebuild="+str(int(time.time())),wait_until="domcontentloaded",timeout=120000)
        await page.wait_for_function("() => !!window.kakao && typeof allDongRouteSpecs==='function' && typeof buildDongRouteOverlay==='function'",timeout=120000)
        await page.evaluate("() => showResult()")
        await page.evaluate("async () => { await ensureTestAdminBoundaryLoad(); }")
        # The live Pages deployment can lag behind the repository. Pin the two verified
        # facility anchors in the build runtime so the v9 bundle is deterministic.
        await page.evaluate("""() => {
          const verified={
            '내수읍|비중리':{name:'비중 문화마을 경로당',address:'충북 청주시 청원구 내수읍 비중길 12',jibunAddress:'충북 청주시 청원구 내수읍 비중리 392',lat:36.71149125948629,lng:127.58053134952354,source:'verified-village-facility',villageTerm:'비중리'},
            '오창읍|유리':{name:'유리경로당',address:'충북 청주시 청원구 오창읍 유리길 50',jibunAddress:'충북 청주시 청원구 오창읍 유리 469-3',lat:36.7575947477498,lng:127.477909909531,source:'verified-village-facility',villageTerm:'유리'}
          };
          const original=test2VillageFacilitySearch;
          test2VillageFacilitySearch=(term)=>{
            const village=test2VillageNameFromRouteTerm(term);
            if(village){
              const districts=(typeof test2VillageDistrictCandidates==='function')
                ? test2VillageDistrictCandidates(village,term)
                : ['내수읍','오창읍','북이면'];
              for(const district of districts){
                const hit=verified[district+'|'+normalizeRi(village)];
                if(hit)return Promise.resolve([{...hit,district}]);
              }
            }
            return original(term);
          };
        }""")

        result=await page.evaluate("""async () => {
          const rural=new Set(['오창읍','내수읍','북이면']);
          const target=new Set(['3344','6138','6544','0262']);
          const specs=allDongRouteSpecs().filter(s=>
            target.has(String(s.vehicle)) &&
            routeAllowedDistricts(s).some(d=>rural.has(canonicalDistrict(d)))
          );
          const built=[];
          const fallback=[];
          const failed=[];
          let cursor=0;
          const workers=Array.from({length:8},async()=>{
            while(true){
              const i=cursor++;
              if(i>=specs.length)return;
              const spec=specs[i];
              try{
                const item=await buildDongRouteOverlay(spec,{forceRebuild:true});
                if(!item){failed.push({type:spec.type,vehicle:spec.vehicle,day:spec.day,scope:routeScopeSignature(spec),reason:'no-item'});continue}
                const rec={
                  type:spec.type,vehicle:spec.vehicle,day:spec.day,
                  districts:routeAllowedDistricts(spec),
                  scopeSignature:routeScopeSignature(spec),
                  data:{...reusableRouteData(item),inferredMovementCount:0,motorwayExcluded:true}
                };
                rec.audit={
                  segments:(rec.data.segments||[]).length,
                  evidence:(rec.data.zoneEvidencePoints||[]).length,
                  missingTerms:[...(rec.data.missingTerms||[])],
                  outsideTerms:[...(rec.data.outsideTerms||[])],
                  outOfCheongwonTerms:[...(rec.data.outOfCheongwonTerms||[])],
                  requiredRoadTerms:[...(rec.data.requiredRoadTerms||[])],
                  coveredRoadTerms:[...(rec.data.coveredRoadTerms||[])],
                  missingRoadTerms:[...(rec.data.missingRoadTerms||[])],
                  finalAuditInvalidCount:Number(rec.data.finalAuditInvalidCount)||0
                };
                built.push(rec);
                if(item.fromBundle)fallback.push({type:spec.type,vehicle:spec.vehicle,day:spec.day,scope:routeScopeSignature(spec)});
              }catch(e){
                failed.push({type:spec.type,vehicle:spec.vehicle,day:spec.day,scope:routeScopeSignature(spec),reason:String(e)});
              }
            }
          });
          await Promise.all(workers);
          built.sort((a,b)=>(a.type+'|'+a.vehicle+'|'+a.day+'|'+a.scopeSignature).localeCompare(b.type+'|'+b.vehicle+'|'+b.day+'|'+b.scopeSignature,'ko'));
          return {
            version:'v76-test2-village-hall-v9-rural-full-audit',
            routes:built,
            specCount:specs.length,
            fallback,failed,
            failedLegs:[...(window.__CJWASTE_ROUTE_PROXY_FAILED_LEGS||[])],
            cacheVersion:'v76-test2-village-hall-v9-rural-full-audit'
          };
        }""")
        await browser.close()

    report.update({
      "version":result.get("version"),
      "specCount":result.get("specCount"),
      "routeCount":len(result.get("routes") or []),
      "expectedRouteCount":20,
      "complete":len(result.get("routes") or [])==20 and len(result.get("failed") or [])==0,
      "fallbackCount":len(result.get("fallback") or []),
      "fallback":result.get("fallback") or [],
      "failedCount":len(result.get("failed") or []),
      "failed":result.get("failed") or [],
      "failedLegCount":len(result.get("failedLegs") or []),
      "pageErrors":report["pageErrors"],
      "consoleErrorCount":len(report["consoleErrors"])
    })
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"version":result["version"],"routes":result["routes"]},ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

asyncio.run(main())
