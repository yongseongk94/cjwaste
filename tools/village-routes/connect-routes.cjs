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
  const publicStops=JSON.parse(fs.readFileSync('tools/village-routes/bus-stops-public.json'));
  const result=await page.evaluate(async({bundle,publicStops})=>{
   const keyword=q=>new Promise(resolve=>places.keywordSearch(q,(r,s)=>resolve(s===kakao.maps.services.Status.OK?r:[]),{size:15}));
   for(const row of bundle.matches){
    if(row.status==='matched')continue;
    const found=[];
    for(const r of publicStops.records.filter(r=>r.village===row.village)){
      const p={lat:+r['위도'],lng:+r['경도']};
      if(!pointInsideRouteDistricts(p,row.districts))continue;
      const addressRows=await new Promise(resolve=>geocoder.coord2Address(p.lng,p.lat,(data,status)=>resolve(status===kakao.maps.services.Status.OK?data:[])));
      const address=addressRows[0]?.road_address?.address_name||addressRows[0]?.address?.address_name||('정류장 '+r['모바일단축번호']);
      found.push({...p,name:r['정류장명']+' 버스정류장',address,district:routePointAnyDistrict(p),source:'village-bus-stop',sourceUrl:publicStops.sourceUrl,stopId:r['정류장번호'],stopNumber:r['모바일단축번호'],dataDate:r['정보수집일']});
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
  },{bundle,publicStops});
  fs.writeFileSync('cjwaste-test/data/precomputed-village-connected-v2.json',JSON.stringify(result.bundle));
  fs.writeFileSync('tools/village-routes/connection-report.json',JSON.stringify(result.report,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
