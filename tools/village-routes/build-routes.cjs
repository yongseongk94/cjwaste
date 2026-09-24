const fs=require('fs'),puppeteer=require('puppeteer-core');
(async()=>{
 const browser=await puppeteer.launch({headless:true,protocolTimeout:3000000,executablePath:process.env.CHROME_BIN,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  const page=await browser.newPage();page.setDefaultTimeout(3000000);
  page.on('console',m=>{if(m.text().startsWith('VILLAGE'))console.log(m.text());});
  await page.goto('https://yongseongk94.github.io/cjwaste/cjwaste-test/?village-build='+Date.now(),{waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForFunction(()=>typeof geocoder!=='undefined'&&!!geocoder);
  await page.evaluate(()=>ensureTestAdminBoundaryLoad());
  await page.addScriptTag({content:fs.readFileSync('tools/village-routes/match.js','utf8')});
  await page.addScriptTag({content:fs.readFileSync('tools/village-routes/road-anchors.js','utf8')});
  const matches=JSON.parse(fs.readFileSync('tools/village-routes/matches.json')).matches.map(({candidates,...r})=>r);
  await page.evaluate(matches=>{
    window.villageMatches=new Map(matches.map(r=>[r.key,r]));
    window.villageCandidates=(term,spec)=>{
      const row=window.villageMatches.get(villageRouteKey(term,spec));
      return row?.status==='matched'?row.facilities.map(f=>({...f,term})):[];
    };
    const originalServiceAnchors=serviceAnchorsForEntry;
    serviceAnchorsForEntry=async(entry,spec)=>{
      if(!entry.desc?.villageFacility)return originalServiceAnchors(entry,spec);
      return villageRoadAnchors(entry.desc.villageFacility,spec);
    };
    // Build into plain data, bypassing old browser caches and visual object allocation.
    let source=buildDongRouteOverlay.toString().replace('function buildDongRouteOverlay','function generateVillageRoute');
    source=source.replace('const existing=existingDongRouteOverlay(spec);','const existing=null;');
    source=source.replace('const sharedOwner=sharedGeometryRouteOverlay(spec);','const sharedOwner=null;');
    source=source.replace('const cached=await getCachedDongRoute(spec);','const cached=null;');
    source=source.replace('const descriptors=applySourceRoadAudit(spec,routeDescriptorsForMap(spec.raw));',`const descriptors=applySourceRoadAudit(spec,routeDescriptorsForMap(spec.raw)).flatMap(d=>{
      const facilities=villageRouteTerm(d.term)?window.villageCandidates(d.term,spec):[];
      return facilities.length?facilities.map(f=>({...d,villageFacility:f})): [d];
    });`);
    source=source.replace('let generic=await searchRouteTermPlaces(term);','let generic=desc.villageFacility?[desc.villageFacility]:(villageRouteTerm(term)?[]:await searchRouteTermPlaces(term));');
    source=source.replace('generic=await expandRangeCandidates(generic,desc);','if(!villageRouteTerm(term))generic=await expandRangeCandidates(generic,desc);');
    source=source.replace('const roadResult=await fetchRoadFollowingPath(anchors);', 'const roadResult=await fetchRoadFollowingPath(anchors); if(entry.desc.villageFacility&&roadResult)roadResult.segments=clipVillageFacilitySegments(roadResult.segments,entry.desc.villageFacility);');
    source=source.replace('await putCachedDongRoute(spec,safeData);','/* generation data is saved by the runner */');
    source=source.replace('await inferredRuralMovementSegments(ruralMovementAnchors)','{segments:[],inferredMovementCount:0}');
    source=source.replace('return createDongRouteOverlay(spec,{...safeData,fromCache:false});','return safeData;');
    window.generateVillageRoute=eval('('+source+')');
  },matches);
  const specs=await page.evaluate(()=>allDongRouteSpecs().filter(s=>!s.provider&&routeDescriptorsForMap(s.raw).some(d=>villageRouteTerm(d.term)&&window.villageMatches.has(villageRouteKey(d.term,s)))));
  const routes=[],report=[];
  let cursor=0;
  await Promise.all(Array.from({length:3},async()=>{while(cursor<specs.length){
    const spec=specs[cursor++];
    const result=await page.evaluate(async spec=>{
      const start=Date.now(),data=await window.generateVillageRoute(spec);
      if(!data)throw Error('empty generated route '+spec.vehicle+' '+spec.day);
      const audit=finalRouteCoordinateAudit(spec,data);if(!audit.ok)throw Error('outside district geometry');
      const expected=routeDescriptorsForMap(spec.raw).filter(d=>villageRouteTerm(d.term)).map(d=>({term:d.term,row:window.villageMatches.get(villageRouteKey(d.term,spec))}));
      const matched=expected.filter(x=>x.row?.status==='matched');
      const missingEvidence=matched.filter(x=>x.row.facilities.some(f=>!data.zoneEvidencePoints.some(p=>routePointDistance(p,f)<.001)));
      if(missingEvidence.length)throw Error('village address not used: '+missingEvidence.map(x=>x.term).join(','));
      const facilityDistances=matched.flatMap(x=>x.row.facilities.map(f=>({term:x.term,name:f.name,address:f.address,distanceM:Math.round(routeItemDistanceKm(data,f.lat,f.lng)*1000)})));
      return {route:{type:spec.type,vehicle:spec.vehicle,day:spec.day,scopeSignature:routeScopeSignature(spec),districts:spec.districts,villageVersion:'village-facility-v1',data},report:{type:spec.type,vehicle:spec.vehicle,day:spec.day,scope:routeScopeSignature(spec),ms:Date.now()-start,segments:data.segments.length,matchedVillages:matched.length,unresolved:expected.filter(x=>x.row?.status!=='matched').map(x=>x.term),missingTerms:data.missingTerms,facilityDistances}};
    },spec);
    routes.push(result.route);report.push(result.report);console.log('VILLAGE_ROUTE',routes.length,specs.length,JSON.stringify(result.report));
    fs.mkdirSync('cjwaste-test/data',{recursive:true});
    fs.writeFileSync('cjwaste-test/data/precomputed-village-facility-routes-v1.json',JSON.stringify({version:'v76-layer-visibility-refresh',villageVersion:'village-facility-v1',generatedAt:new Date().toISOString(),matches,routes}));
    fs.writeFileSync('tools/village-routes/route-report.json',JSON.stringify(report,null,2));
  }}));
  if(routes.length!==specs.length||!routes.length)throw Error('incomplete generation');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
