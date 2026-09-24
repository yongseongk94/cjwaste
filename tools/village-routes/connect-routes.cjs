const fs=require('fs'),puppeteer=require('puppeteer-core');
(async()=>{
 const file='cjwaste-test/data/precomputed-village-facility-routes-v1.json';
 const bundle=JSON.parse(fs.readFileSync(file));
 const browser=await puppeteer.launch({headless:true,protocolTimeout:1800000,executablePath:process.env.CHROME_BIN,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  const page=await browser.newPage();
  page.on('console',m=>{if(m.text().startsWith('CONNECT'))console.log(m.text());});
  await page.goto('https://yongseongk94.github.io/cjwaste/cjwaste-test/?connect='+Date.now(),{waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForFunction(()=>typeof geocoder!=='undefined'&&!!geocoder);
  await page.evaluate(()=>ensureTestAdminBoundaryLoad());
  const result=await page.evaluate(async bundle=>{
   const keyword=q=>new Promise(resolve=>places.keywordSearch(q,(r,s)=>resolve(s===kakao.maps.services.Status.OK?r:[]),{size:15}));
   for(const row of bundle.matches){
    if(row.status==='matched')continue;
    const found=[];
    for(const district of row.districts){
     for(const q of ['청주 '+district+' '+row.village+' 버스정류장','청주 '+row.village+' 버스정류장','청주 '+row.village+' 정류장']){
      for(const r of await keyword(q)){
       const p={lat:+r.y,lng:+r.x},stem=row.village.replace(/리$/,'');
       if(!/버스|정류장/.test(r.category_name+' '+r.place_name)||!r.place_name.includes(stem)||!pointInsideRouteDistricts(p,[district]))continue;
       if(found.some(f=>f.placeId===r.id))continue;
       found.push({...p,name:r.place_name,address:r.road_address_name||r.address_name,jibunAddress:r.address_name,district,source:'village-bus-stop',sourceUrl:r.place_url||'https://place.map.kakao.com/'+r.id,placeId:r.id,query:q});
      }
     }
    }
    row.busCandidates=found;row.facilities=found.length?[found[0]]:[];
    if(found.length){row.status='matched';row.matchKind='bus-stop';}
    console.log('CONNECT_BUS',row.key,JSON.stringify(found));
   }
   const specs=allDongRouteSpecs(),rows=new Map(bundle.matches.map(r=>[r.key,r]));
   const report=[];
   for(const record of bundle.routes){
    const spec=bundleRouteRecordSpec(record,specs),waypoints=[],missing=[];
    for(const d of applySourceRoadAudit(spec,routeDescriptorsForMap(spec.raw))){
     const row=rows.get(villageRouteKey(d.term,spec));
     let candidates=row?.status==='matched'?row.facilities:[];
     if(row&&row.status!=='matched'){missing.push(d.term);continue;}
     if(!row){
      candidates=record.data.zoneEvidencePoints.filter(p=>p.term===d.term);
      if(!candidates.length)candidates=(await searchRouteTermPlaces(d.term)).filter(p=>pointInsideRouteDistricts(p,routeAllowedDistricts(spec))).slice(0,1);
     }
     if(!candidates.length){missing.push(d.term);continue;}
     for(const p of candidates){
      const point={...p,term:d.term};
      if(!waypoints.length||routePointDistance(waypoints[waypoints.length-1],point)>.005)waypoints.push(point);
      if(row?.matchKind==='bus-stop'&&!record.data.zoneEvidencePoints.some(e=>routePointDistance(e,point)<.001))record.data.zoneEvidencePoints.push(point);
     }
    }
    const road=await fetchRoadFollowingPath(waypoints);
    if(waypoints.length>=2&&(!road?.segments?.length||road.failedLegs.length))throw Error('unresolved connecting road '+spec.vehicle+' '+spec.day);
    const joined=[];
    for(const seg of road?.segments||[]){
     if(joined.length&&routePointDistance(joined[joined.length-1].at(-1),seg[0])<.005)joined[joined.length-1].push(...seg.slice(1));
     else joined.push([...seg]);
    }
    record.data.travelSegments=joined;record.data.travelWaypoints=waypoints;
    record.data.travelMissingTerms=[...new Set(missing)];
    record.data.travelDistance=routeSegmentsDistanceMeters(joined);
    record.data.travelVersion='village-connected-v2';
    record.data.missingTerms=record.data.missingTerms.filter(t=>!rows.get(villageRouteKey(t,spec))?.matchKind);
    const distances=waypoints.map(p=>({name:p.name,term:p.term,distanceM:Math.round(routeItemDistanceKm({segments:joined},p.lat,p.lng)*1000)}));
    report.push({vehicle:spec.vehicle,day:spec.day,type:spec.type,waypoints:waypoints.length,parts:joined.length,missing,distances});
    console.log('CONNECT_ROUTE',JSON.stringify(report.at(-1)));
   }
   bundle.travelVersion='village-connected-v2';bundle.connectedAt=new Date().toISOString();
   return {bundle,report};
  },bundle);
  fs.writeFileSync('cjwaste-test/data/precomputed-village-connected-v2.json',JSON.stringify(result.bundle));
  fs.writeFileSync('tools/village-routes/connection-report.json',JSON.stringify(result.report,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
