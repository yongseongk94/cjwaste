import asyncio, json, time, os
from urllib.parse import urlsplit
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://yongseongk94.github.io/cjwaste/cjwaste-test2/"
OUT=Path(os.environ.get("TEST2_AUDIT_OUT","tools/test2-rural-route-full-audit.json"))
TARGET={"general":["3344","6138"],"recycle":["6544","0262"]}
RURAL={"오창읍","내수읍","북이면"}

async def main():
    out={"url":URL,"localAssets":bool(os.environ.get("TEST2_LOCAL")),"startedAt":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"pageErrors":[],"consoleErrors":[],"httpErrors":[]}
    async with async_playwright() as p:
        proxy_url=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        proxy={'server':proxy_url} if proxy_url else None
        browser=await p.chromium.launch(headless=True,proxy=proxy)
        page=await browser.new_page(viewport={"width":1440,"height":1000},ignore_https_errors=True)
        if os.environ.get("TEST2_LOCAL"):
            root=Path(__file__).resolve().parents[1]
            async def local_asset(route):
                path=urlsplit(route.request.url).path.removeprefix("/cjwaste/")
                asset=root / (path+"index.html" if path.endswith("/") else path)
                if asset.is_file():
                    await route.fulfill(path=str(asset))
                else:
                    await route.continue_()
            await page.route("https://yongseongk94.github.io/cjwaste/**",local_asset)
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

        result=await page.evaluate(r"""({TARGET,RURAL})=>{
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
                  const points=items.flatMap(i=>(i.segments||[]).flat());
                  const actualRis=[...new Set(points.map(p=>pointRi(district,p)).filter(Boolean))];
                  const evidence=items.flatMap(i=>i.zoneEvidencePoints||[]);
                  const normExpected=routeNorm(expectedRi);
                  const verifiedEvidence=evidence.filter(p=>{
                    const texts=[p.term,p.villageTerm,p.jibunAddress,p.address,p.name].map(x=>routeNorm(x||'')).filter(Boolean);
                    return texts.some(t=>t.includes(normExpected)) &&
                      (/verified|village|facility|senior|hall/.test(String(p.source||'')));
                  });
                  const routeNearVerifiedEvidence=verifiedEvidence.some(p=>items.some(item=>{
                    try{return routeItemDistanceKm(item,+p.lat,+p.lng)<=0.08}catch(e){return false}
                  }));
                  const spatialCovered=actualRis.includes(expectedRi)||routeNearVerifiedEvidence;
                  const covered=spatialCovered;
                  result.expected.push({type,vehicle,day,district,ri:riRaw,officialRi:expectedRi,covered,spatialCovered,routeNearVerifiedEvidence,
                    verifiedEvidence:verifiedEvidence.map(p=>({name:p.name||'',address:p.address||'',jibunAddress:p.jibunAddress||'',term:p.term||'',villageTerm:p.villageTerm||'',source:p.source||'',lat:+p.lat,lng:+p.lng})),
                    actualRis,
                    itemCount:items.length,segmentCount:items.reduce((n,i)=>n+(i.segments||[]).length,0),
                    evidenceCount:evidence.length});
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
        out["selectionChecks"]=await page.evaluate("""async()=>{
          const checks=[];
          for(const type of ['general','recycle'])for(const vehicle of (type==='general'?['3344','6138']:['6544','0262']))for(const day of ['월','화','수','목','금']){
            setLayer(type);setVehicle(vehicle);setDay(day);
            await new Promise(resolve=>setTimeout(resolve,120));
            const items=(dongRouteOverlays[type]||[]).filter(i=>String(i.vehicle)===vehicle&&i.day===day);
            const visible=items.flatMap(routeItemPolylines).filter(p=>p.getMap()===map).length;
            checks.push({type,vehicle,day,visible,ok:visible>0});
          }
          for(let i=0;i<12;i++){setLayer(i%2?'general':'recycle');setVehicle(i%2?'3344':'0262');setDay(['월','화','수'][i%3]);}
          setLayer('recycle');setVehicle('0262');setDay('화');
          await new Promise(resolve=>setTimeout(resolve,1200));
          const visible=Object.values(dongRouteOverlays).flat().filter(i=>routeItemPolylines(i).some(p=>p.getMap()===map));
          checks.push({rapidSwitch:true,ok:visible.length>0&&visible.every(i=>i.type==='recycle'&&String(i.vehicle)==='0262'&&i.day==='화')});
          return checks;
        }""")
        out["coordinateAudits"]=await page.evaluate("""()=>allDongRouteSpecs().filter(s=>['3344','6138','6544','0262'].includes(String(s.vehicle))&&routeAllowedDistricts(s).some(d=>['오창읍','내수읍','북이면'].includes(d))).map(s=>({vehicle:s.vehicle,day:s.day,...finalRouteCoordinateAudit(s,existingDongRouteOverlay(s))}))""")
        cache_check="""async()=>{
          const specs=allDongRouteSpecs().filter(s=>['3344','6138','6544','0262'].includes(String(s.vehicle))&&routeAllowedDistricts(s).some(d=>['오창읍','내수읍','북이면'].includes(d)));
          const rows=[];
          const geometry=s=>JSON.stringify((s||[]).map(segment=>segment.map(p=>[p.lat,p.lng])));
          for(const spec of specs){const cached=await getCachedDongRoute(spec);const shown=existingDongRouteOverlay(spec);rows.push({vehicle:spec.vehicle,day:spec.day,segments:cached?.segments?.length||0,ok:!!cached&&geometry(cached.segments)===geometry(shown?.segments)});}
          return {version:DONG_ROUTE_CACHE_VERSION,rows};
        }"""
        out['cacheBeforeReload']=await page.evaluate(cache_check)
        if os.environ.get('TEST2_SCREENSHOT'):
            await page.evaluate("()=>{const b=new kakao.maps.LatLngBounds();for(const i of dongRouteOverlays.recycle.filter(i=>String(i.vehicle)==='0262'&&i.day==='화'))for(const s of i.segments)for(const p of s)b.extend(new kakao.maps.LatLng(p.lat,p.lng));map.setBounds(b)}")
            await page.wait_for_timeout(1200)
            await page.screenshot(path=os.environ['TEST2_SCREENSHOT'])
        await page.reload(wait_until='domcontentloaded',timeout=90000)
        await page.wait_for_function("typeof map!=='undefined'&&!!map&&typeof ensureTestAdminBoundaryLoad==='function'",timeout=90000)
        await page.evaluate("async()=>{await ensureTestAdminBoundaryLoad();await hydrateExternalBundledPrecomputedData();}")
        await page.wait_for_timeout(1500)
        out['cacheAfterReload']=await page.evaluate(cache_check)
        await browser.close()

    out.update(result)
    out["checks"]={
      "http200":out.get("httpStatus")==200,
      "cache20BeforeAndAfterReload":all(len(out[k]['rows'])==20 and all(r['ok'] for r in out[k]['rows']) for k in ['cacheBeforeReload','cacheAfterReload']),
      "allTargetDaysPresent":result.get("allTargetDaysPresent",False),
      "allRiCovered":result.get("allRiCovered",False),
      "noPageErrors":len(out["pageErrors"])==0,
      "allSelectionsVisible":all(r["ok"] for r in out["selectionChecks"]),
      "allCoordinatesInScope":len(out["coordinateAudits"])==20 and all(r["ok"] for r in out["coordinateAudits"])
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"checks":out["checks"],"summary":out.get("summary"),"totalExpected":out.get("totalExpected"),"totalCovered":out.get("totalCovered")},ensure_ascii=False,indent=2))

asyncio.run(main())
