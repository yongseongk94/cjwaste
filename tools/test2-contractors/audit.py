import asyncio,json,os,time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[2]
async def main():
 async with async_playwright() as p:
  proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
  browser=await p.chromium.launch(headless=True,proxy={'server':proxy} if proxy else None)
  page=await browser.new_page(ignore_https_errors=True,viewport={'width':1440,'height':1000});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.route('https://cjwaste-route.yseong22.workers.dev/**',lambda r:r.abort())
  if os.environ.get('TEST2_LOCAL'):
   async def asset(route):
    path=urlsplit(route.request.url).path.removeprefix('/cjwaste/');f=ROOT/(path+'index.html' if path.endswith('/') else path)
    if f.is_file():await route.fulfill(path=str(f))
    else:await route.continue_()
   await page.route('https://yongseongk94.github.io/cjwaste/**',asset)
  await page.goto('https://yongseongk94.github.io/cjwaste/cjwaste-test2/?contractor_audit='+str(int(time.time())),wait_until='domcontentloaded',timeout=90000)
  await page.wait_for_function("typeof map!=='undefined'&&!!map",timeout=90000)
  await page.evaluate('()=>showResult()')
  await page.evaluate('async()=>{await ensureTestAdminBoundaryLoad();await hydrateExternalBundledPrecomputedData()}')
  print('hydrated',flush=True)
  result=await page.evaluate('''async()=>{
    const specs=allDongRouteSpecs().filter(s=>!!s.provider),groups=new Map();
    for(const s of specs){const key=routeCacheKey(s);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(s);}
    const rows=[];for(const [key,g] of groups){const items=g.map(existingDongRouteOverlay);const owner=items[0];
      const cache=await getCachedDongRoute(g[0]);
      rows.push({vehicle:g[0].vehicle,type:g[0].type,days:g.map(s=>s.day),present:items.every(Boolean),shared:items.every(i=>i?.polylines===owner?.polylines),cacheOK:!!cache&&JSON.stringify(cache.segments)===JSON.stringify(owner?.segments),scopeOK:items.every(i=>i&&finalRouteCoordinateAudit(i,i).ok)});
    }
    const hy=Object.values(dongRouteOverlays).flat().filter(i=>i.provider==='현대환경'&&['화','목'].includes(i.day));
    const hyundai=hy.map(i=>({type:i.type,day:i.day,anchors:i.zoneEvidencePoints.length,segments:i.segments.length,estimated:i.estimatedServiceSegments?.length||0,connections:i.connectionSegments?.length||0,version:i.connectionVersion,estimatedNotCertified:(i.estimatedServiceSegments||[]).some(s=>s.some(p=>routeItemDistanceKm(i,p.lat,p.lng)>.02)),connected:i.connectionAudit?.connected}));
    const visibility=[];
    for(const type of ['general','recycle'])for(const provider of ['제일환경','현대환경'])for(const day of ['월','수','금','화','목']){
      setLayer(type);setVehicle(provider);setDay(day);await new Promise(r=>setTimeout(r,80));
      const expected=new Set((dongRouteOverlays[type]||[]).filter(i=>routeSelectedBy(provider,i.vehicle)&&i.day===day).flatMap(routeItemPolylines));
      const actual=new Set(Object.values(dongRouteOverlays).flat().flatMap(routeItemPolylines).filter(pl=>pl.getMap()===map));
      visibility.push({type,provider,day,ok:expected.size>0&&expected.size===actual.size&&[...expected].every(pl=>actual.has(pl))});
    }
    setLayer('general');setVehicle('현대환경');setDay('화');syncDongRouteVisibility('general');
    const h=dongRouteOverlays.general.find(i=>i.provider==='현대환경'&&i.day==='화');let mapCalls=0;
    const saved=h.polylines.map(pl=>pl.setMap);h.polylines.forEach(pl=>{const orig=pl.setMap;pl.setMap=function(m){mapCalls++;return orig.call(this,m)}});
    setDay('목');syncDongRouteVisibility('general');h.polylines.forEach((pl,j)=>pl.setMap=saved[j]);
    const bounds=new kakao.maps.LatLngBounds();for(const s of [...h.segments,...h.estimatedServiceSegments,...h.connectionSegments])for(const p of s)bounds.extend(new kakao.maps.LatLng(p.lat,p.lng));map.setBounds(bounds);
    return {slots:specs.length,groups:groups.size,rows,hyundai,visibility,sameGeometrySwitchMapCalls:mapCalls};
  }''')
  await page.wait_for_timeout(2000);await page.screenshot(path='/tmp/test2-hyundai-'+('local' if os.environ.get('TEST2_LOCAL') else 'live')+'.png')
  await page.reload(wait_until='domcontentloaded');await page.wait_for_function("typeof map!=='undefined'&&!!map",timeout=90000)
  await page.evaluate('async()=>{await ensureTestAdminBoundaryLoad();await hydrateExternalBundledPrecomputedData()}')
  result['reload']=await page.evaluate('''async()=>{const specs=allDongRouteSpecs().filter(s=>!!s.provider);const rows=[];for(const s of specs){const c=await getCachedDongRoute(s),i=existingDongRouteOverlay(s);rows.push(!!c&&!!i&&['segments','estimatedServiceSegments','connectionSegments'].every(k=>JSON.stringify(c[k]||[])===JSON.stringify(i[k]||[])));}return {slots:rows.length,ok:rows.every(Boolean)}}''')
  result['pageErrors']=errors;result['local']=bool(os.environ.get('TEST2_LOCAL'));result['checkedAt']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
  result['ok']=all(r['present'] and r['shared'] and r['cacheOK'] and r['scopeOK'] for r in result['rows']) and all(r['ok'] for r in result['visibility']) and len(result['hyundai'])==4 and all(r['anchors']==7 and r['estimated'] and r['connections'] and r['estimatedNotCertified'] and r['connected'] for r in result['hyundai']) and result['reload']['ok'] and result['sameGeometrySwitchMapCalls']==0 and not errors
  out=ROOT/'tools/test2-contractors'/('local-audit.json' if result['local'] else 'live-audit.json');out.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2));await browser.close();assert result['ok']
asyncio.run(main())
