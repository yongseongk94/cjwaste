import asyncio, json, os, time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json'
REPORT=ROOT/'tools/test2-remaining-facility-repair.json'
URL='https://yongseongk94.github.io/cjwaste/cjwaste-test2/'

async def main():
    bundle=json.loads(BUNDLE.read_text())
    matches=json.loads((ROOT/'cjwaste-test/data/precomputed-village-connected-v2.json').read_text())['matches']
    targets=[('general','6138','월','내수읍','비중리'),('general','3344','월','오창읍','각리'),('general','3344','수','오창읍','양지리'),('general','3344','수','오창읍','도암리'),('general','6138','화','북이면','영하리')]
    report={'startedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'results':[]}
    async with async_playwright() as pw:
        proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        browser=await pw.chromium.launch(headless=True,proxy={'server':proxy} if proxy else None)
        page=await browser.new_page(ignore_https_errors=True)
        async def asset(route):
            path=urlsplit(route.request.url).path.removeprefix('/cjwaste/')
            file=ROOT/(path+'index.html' if path.endswith('/') else path)
            if file.is_file(): await route.fulfill(path=str(file))
            else: await route.continue_()
        await page.route('https://yongseongk94.github.io/cjwaste/**',asset)
        await page.goto(URL,wait_until='domcontentloaded',timeout=90000)
        await page.wait_for_function("typeof places!=='undefined'&&!!places&&typeof allDongRouteSpecs==='function'",timeout=120000)
        await page.evaluate('async()=>{await ensureTestAdminBoundaryLoad();await hydrateExternalBundledPrecomputedData()}')
        await page.evaluate('(matches)=>{window.villageMatches=new Map(matches.map(m=>[m.key,m]));}',matches)
        await page.add_script_tag(content=(ROOT/'tools/village-routes/road-anchors.js').read_text())
        for typ,veh,day,district,village in targets:
            facilities=[dict(f,term=village,villageTerm=village) for m in matches if m['village']==village for f in m.get('facilities',[]) if f.get('district')==district]
            if not facilities:
                facilities=await page.evaluate('''async ({district,village})=>{
                  for(const kind of ['마을회관','경로당','버스정류장']){
                    const rows=await new Promise(resolve=>places.keywordSearch('청주시 청원구 '+district+' '+village+' '+kind,(r,s)=>resolve(s===kakao.maps.services.Status.OK?r:[])));
                    const hits=rows.filter(r=>(r.address_name||'').includes(district+' '+village+' ')&&r.place_name.includes(village.replace(/리$/,'')));
                    if(hits.length)return hits.map(r=>({lat:+r.y,lng:+r.x,name:r.place_name,address:r.road_address_name||r.address_name,jibunAddress:r.address_name,district,term:village,villageTerm:village,source:'verified-village-'+kind,sourceUrl:r.place_url}));
                  }
                  return [];
                }''',{'district':district,'village':village})
            print('TARGET',veh,day,village,'facilities',len(facilities),flush=True)
            if not facilities:
                report['results'].append({'vehicle':veh,'day':day,'village':village,'status':'facility-unresolved'})
                REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2));continue
            try:
                result=await asyncio.wait_for(page.evaluate('''async ({type,vehicle,day,district,facilities})=>{
                    const spec=allDongRouteSpecs().find(s=>s.type===type&&s.vehicle===vehicle&&s.day===day&&routeAllowedDistricts(s).includes(district));
                    if(!spec)throw Error('missing source spec');
                    let segments=[];
                    for(const facility of facilities){
                      const anchors=await villageRoadAnchors(facility,spec);
                      if(anchors.length<2)continue;
                      const road=await fetchVillageFacilityRoad(anchors,facility,spec);
                      segments.push(...(road?.segments||[]));
                    }
                    const data={segments,zoneEvidencePoints:facilities};
                    const audit=finalRouteCoordinateAudit(spec,data);
                    const distances=facilities.map(f=>routeItemDistanceKm(data,f.lat,f.lng)*1000);
                    return {segments,facilities,audit,distances,scope:routeScopeSignature(spec)};
                }''',{'type':typ,'vehicle':veh,'day':day,'district':district,'facilities':facilities}),timeout=180)
                good=result['audit']['ok'] and result['segments'] and max(result['distances'])<=80
                if good:
                    r=next(r for r in bundle['routes'] if (r['type'],r['vehicle'],r['day'],r['scopeSignature'])==(typ,veh,day,result['scope']))
                    r['data']['segments'].extend(result['segments'])
                    r['data']['zoneEvidencePoints'].extend(result['facilities'])
                    r['data']['missingTerms']=[t for t in r['data']['missingTerms'] if t!=village]
                    BUNDLE.write_text(json.dumps(bundle,ensure_ascii=False,separators=(',',':')))
                report['results'].append({'vehicle':veh,'day':day,'village':village,'status':'repaired' if good else 'road-unresolved',**result})
                print('RESULT',veh,day,village,good,result['distances'],flush=True)
            except Exception as error:
                report['results'].append({'vehicle':veh,'day':day,'village':village,'status':'error','error':str(error)})
                print('ERROR',veh,day,village,str(error),flush=True)
            REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        await browser.close()

asyncio.run(main())
