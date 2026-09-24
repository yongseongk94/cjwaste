const fs=require('fs'),assert=require('assert'),puppeteer=require('puppeteer-core');
(async()=>{
 const browser=await puppeteer.launch({headless:true,executablePath:process.env.CHROME_BIN,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('https://yongseongk94.github.io/cjwaste/cjwaste-test/?village-verify='+Date.now(),{waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForFunction(()=>typeof geocoder!=='undefined'&&!!geocoder);
  const result=await page.evaluate(async()=>{
   await ensureTestAdminBoundaryLoad();
   const bundle=await loadExternalBundledPrecomputedData();
   const specs=allDongRouteSpecs().filter(villageSpecAffected);
   if(!villageRouteBundle||villageRouteBundle.routes.length!==specs.length)throw Error('incomplete live village bundle');
   const bad=specs.filter(s=>bundle.routes.filter(r=>r.type===s.type&&r.vehicle===s.vehicle&&r.day===s.day&&r.scopeSignature===routeScopeSignature(s)).length!==1);
   if(bad.length)throw Error('duplicate or missing merged route');
   let roadRequests=0;const oldFetch=window.fetch;
   window.fetch=(url,...args)=>{if(String(url)===ROUTE_PROXY_URL)roadRequests++;return oldFetch(url,...args);};
   const started=performance.now();
   for(const spec of specs){
    const item=await buildDongRouteOverlay(spec);
    if(!item)throw Error('no live route data');
    if(!item.segments.length&&routeDescriptorsForMap(spec.raw).some(d=>villageFacilityCandidates(d.term,spec).length))throw Error('no live road segments for matched facility');
    if(!finalRouteCoordinateAudit(spec,item).ok)throw Error('live geometry outside assigned districts');
   }
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
