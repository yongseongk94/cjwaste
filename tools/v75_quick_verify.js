const fs=require('fs');
const puppeteer=require('puppeteer-core');
(async()=>{
  const browser=await puppeteer.launch({headless:true,executablePath:process.env.CHROME_BIN,args:['--no-sandbox','--disable-dev-shm-usage']});
  const page=await browser.newPage();
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.goto('https://yongseongk94.github.io/cjwaste/?v75quick='+Date.now(),{waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForFunction(()=>typeof contractExactScheduleMatch==='function'&&typeof CONTRACT_ROUTES!=='undefined',{timeout:120000});
  const r=await page.evaluate(()=>{
    const mk=(a)=>({district:'내덕2동',legalEmd:'내덕2동',address:a,roadAddress:a,jibunAddress:'',legalRi:''});
    let bundledVersion='';
    try{bundledVersion=JSON.parse(document.getElementById('bundledPrecomputed')?.textContent||'{}').version||''}catch(e){}
    return {
      cacheVersion:typeof DONG_ROUTE_CACHE_VERSION!=='undefined'?DONG_ROUTE_CACHE_VERSION:'',
      bundledVersion,
      precomputeReady:window.__CJWASTE_PRECOMPUTE_READY===true,
      exact30:contractExactScheduleMatch('general',mk('충청북도 청주시 청원구 공항로84번길 30')),
      sameRoad29:contractExactScheduleMatch('general',mk('충청북도 청주시 청원구 공항로84번길 29')),
      byName:contractExactScheduleMatch('general',mk('이랜드해가든')),
      activeContractRoads:(CONTRACT_ROUTES.general||[]).filter(x=>x.provider==='제일환경'&&x.plate==='95오0147'&&(x.districts||[]).includes('내덕2동')),
      sourceRows:(CONTRACT_SOURCE_DATA.routes?.general||[]).filter(x=>x.provider==='제일환경'&&x.plate==='95오0147'&&(x.districts||[]).includes('내덕2동')),
      specialRows:(CONTRACT_SPECIAL_POINTS||[]).filter(x=>x.provider==='제일환경'&&x.vehicle==='95오0147'&&x.district==='내덕2동'),
      directGeneral6157:ROUTE_DONG_SCOPE?.general?.['6157']||[],
      directRecycle0261:ROUTE_DONG_SCOPE?.recycle?.['0261']||[]
    };
  });
  r.pageErrors=errors;
  const failures=[];
  if(!String(r.cacheVersion).includes('v75-naedeok2-apartment-only'))failures.push('cache version');
  if(!r.exact30||r.exact30.provider!=='제일환경'||r.exact30.vehicle!=='95오0147')failures.push('exact 30 match');
  if(!['화','목','토'].every(d=>(r.exact30?.days||[]).includes(d)))failures.push('exact 30 days');
  if(r.sameRoad29!==null)failures.push('same-road 29 false positive');
  if(!r.byName||r.byName.provider!=='제일환경')failures.push('name match');
  if(r.activeContractRoads.length!==0)failures.push('contract road still active');
  if(r.sourceRows.length!==1||r.sourceRows[0].housing!=='apartment')failures.push('source apartment classification');
  if(r.specialRows.length!==1||!String(r.specialRows[0].address).includes('공항로84번길 30'))failures.push('special exact point');
  if(!r.directGeneral6157.includes('내덕2동'))failures.push('6157 direct scope');
  if(!r.directRecycle0261.includes('내덕2동'))failures.push('0261 direct scope');
  if(errors.length)failures.push('page errors');
  r.failures=failures; r.success=failures.length===0;
  fs.writeFileSync('tools/v75_live_quick_verify.json',JSON.stringify(r,null,2));
  console.log(JSON.stringify(r,null,2));
  await browser.close();
  if(failures.length)process.exit(1);
})().catch(e=>{console.error(e);process.exit(1)});
