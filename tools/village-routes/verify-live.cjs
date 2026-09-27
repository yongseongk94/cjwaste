const fs=require('fs'),assert=require('assert'),puppeteer=require('puppeteer-core');
(async()=>{
 const browser=await puppeteer.launch({headless:true,executablePath:process.env.CHROME_BIN,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  const page=await browser.newPage(),errors=[];page.on('console',m=>{if(m.text().startsWith('HYUNDAI_'))console.log(m.text())});page.on('pageerror',e=>errors.push(e.message));
  await page.goto('https://yongseongk94.github.io/cjwaste/cjwaste-test/?village-verify='+Date.now(),{waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForFunction(()=>typeof geocoder!=='undefined'&&!!geocoder);
  const result=await page.evaluate(async()=>{
   await ensureTestAdminBoundaryLoad();
   const bundle=await loadExternalBundledPrecomputedData();
   const specs=allDongRouteSpecs().filter(villageSpecAffected);
   if(!villageRouteBundle||villageRouteBundle.travelVersion!=='village-connected-v2'||villageRouteBundle.routes.length!==specs.length)throw Error('incomplete live village bundle');
   const bad=specs.filter(s=>bundle.routes.filter(r=>r.type===s.type&&r.vehicle===s.vehicle&&r.day===s.day&&r.scopeSignature===routeScopeSignature(s)).length!==1);
   if(bad.length)throw Error('duplicate or missing merged route');
   let roadRequests=0;const oldFetch=window.fetch;
   window.fetch=(url,...args)=>{if(String(url)===ROUTE_PROXY_URL)roadRequests++;return oldFetch(url,...args);};
   const started=performance.now();
   for(const spec of specs){
    const item=await buildDongRouteOverlay(spec);
    if(!item)throw Error('no live route data');
    if(item.travelSegments?.length!==1)throw Error('live route disconnected');
    if(routeItemPolylines(item).length!==1)throw Error('fragmented display');
    if(!finalRouteCoordinateAudit(spec,item).ok)throw Error('live geometry outside assigned districts');
   }
   const hyundaiSpecs=allDongRouteSpecs().filter(hyundaiRouteAffected);
   if(hyundaiSpecs.length!==4)throw Error('Hyundai slot count');
   for(const spec of hyundaiSpecs){
    const item=await buildDongRouteOverlay(spec);
    const record=hyundaiRouteBundle.routes.find(r=>r.type===spec.type&&r.day===spec.day);
    if(!item||item.travelSegments?.length!==1||routeItemPolylines(item).length!==1)throw Error('Hyundai display missing');
    if(!finalRouteCoordinateAudit(spec,item).ok)throw Error('Hyundai service geometry outside scope');
    if(item.zoneEvidencePoints.length!==(spec.day==='화'?4:6))throw Error('Hyundai landmark missing');
    if(item.zoneEvidencePoints.some(p=>['형제빌라','풀하우스','오성빌리지','위너스빌'].includes(p.name)))throw Error('unrelated housing retained');
    if(record.data.travelMissingTerms.length)throw Error('Hyundai missing local road');
    for(const p of record.data.travelWaypoints)if(routeItemDistanceKm({segments:item.travelSegments},p.lat,p.lng)>.15)throw Error('Hyundai route misses landmark');
   }
   console.log('HYUNDAI_LIVE_PASS',JSON.stringify({routes:hyundaiSpecs.length,landmarks:[4,6],roadRequests}));
   window.fetch=oldFetch;
   if(roadRequests)throw Error('live route recalculation '+roadRequests);
   const first=villageRouteBundle.matches.find(r=>r.key==='오창읍|창리').facilities[0];
   return {routes:specs.length,matched:villageRouteBundle.matches.filter(r=>r.status==='matched').length,roadRequests,loadMs:Math.round(performance.now()-started),sample:first};
  });
  await page.evaluate(f=>moveTo(f.lat,f.lng,f.address,f.address,f.jibunAddress||''),result.sample);
  await page.waitForFunction(()=>document.getElementById('landing').classList.contains('hidden'),{timeout:60000});
  await page.waitForFunction(()=>!!map&&map.getCenter().getLat()>36.7,{timeout:60000});
  const responseStart=Date.now();
  assert(await page.evaluate(()=>typeof map.getLevel()==='number'));
  result.mapResponseMs=Date.now()-responseStart;
  assert(result.mapResponseMs<5000,'Ochang map is unresponsive');
  assert.deepEqual(errors,[]);
  delete result.sample;console.log('VILLAGE_LIVE_PASS',JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
