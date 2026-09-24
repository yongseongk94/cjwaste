const fs=require('fs'),puppeteer=require('puppeteer-core');
(async()=>{
 const matches=JSON.parse(fs.readFileSync('tools/village-routes/matches.json')).matches;
 const facilities=[...JSON.parse(fs.readFileSync('tools/village-routes/public-records.json')),...JSON.parse(fs.readFileSync('tools/village-routes/public-facility-listings.json'))];
 const browser=await puppeteer.launch({headless:true,executablePath:process.env.CHROME_BIN,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();
  await page.goto('https://yongseongk94.github.io/cjwaste/cjwaste-test/?facility-verify='+Date.now(),{waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForFunction(()=>typeof geocoder!=='undefined'&&!!geocoder);
  await page.evaluate(()=>ensureTestAdminBoundaryLoad());
  page.on('console',m=>{if(m.text().startsWith('FACILITY'))console.log(m.text());});
  const result=await page.evaluate(async({matches,facilities})=>{
   const cache=new Map(),compact=s=>String(s||'').replace(/\s/g,'');
   for(const row of matches){
    if(row.status==='matched')continue;
    const stem=row.village.replace(/리$/,''),numbered=/\d/.test(stem),base=stem.replace(/\d+$/,'');
    const candidates=facilities.filter(f=>{
      const location=f.address+' '+f.jibunAddress;
      if(!row.districts.some(d=>location.includes(d))&&(!location.includes('청원구')||/(오창읍|내수읍|북이면)/.test(location)))return false;
      const n=compact(f.name);
      if(row.village==='꽃화산리')return f.address.includes('꽃화산');
      if(row.village==='빛화산리')return f.address.includes('빛화산');
      if(row.village==='원통1리'&&f.address.includes('원통길 13-2'))return true;
      return numbered?new RegExp('^'+stem+'(?:리|구|경로|노인|$)').test(n):new RegExp('^'+base+'(?:리|[0-9]+(?:리|구)|경로|노인|$|\\()').test(n);
    });
    for(const f of candidates){
      let points=[];
      for(const query of [f.address,f.jibunAddress].filter(Boolean)){
        if(!cache.has(query))cache.set(query,await addressSearchPromise(query));
        points=cache.get(query).filter(p=>pointInsideRouteDistricts({lat:+p.y,lng:+p.x},row.districts));
        if(points.length===1)break;
      }
      if(points.length!==1){console.log('FACILITY_UNRESOLVED',row.key,f.name,f.address,points.length);continue;}
      const p=points[0],pt={lat:+p.y,lng:+p.x};
      if(row.facilities.some(a=>routePointDistance(a,pt)<.02))continue;
      row.facilities.push({...f,...pt,address:p.road_address?.address_name||p.address_name||f.address,source:'public-facility-address',district:routePointAnyDistrict(pt),geocodedAt:new Date().toISOString()});
    }
    if(row.facilities.length){row.status='matched';row.facilities.sort((a,b)=>a.name.localeCompare(b.name,'ko',{numeric:true}));}
   }
   return matches;
  },{matches,facilities});
  fs.writeFileSync('tools/village-routes/matches.json',JSON.stringify({generatedAt:new Date().toISOString(),source:'Kakao facility search + Cheongju public standard facility data, geocoded and district checked',matches:result},null,2));
  console.log('AUGMENT',JSON.stringify({matched:result.filter(x=>x.status==='matched').length,unresolved:result.filter(x=>x.status!=='matched').map(x=>x.key)}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
