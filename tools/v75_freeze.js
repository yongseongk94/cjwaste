const fs=require('fs');
const puppeteer=require('puppeteer-core');
(async()=>{
  const browser=await puppeteer.launch({headless:true,protocolTimeout:1500000,executablePath:process.env.CHROME_BIN,args:['--no-sandbox','--disable-dev-shm-usage']});
  const page=await browser.newPage();
  page.setDefaultTimeout(1500000);
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('https://yongseongk94.github.io/cjwaste/?precompute=v75-'+Date.now(),{waitUntil:'domcontentloaded',timeout:180000});
  await page.waitForFunction(()=>typeof window.exportCjWastePrecomputed==='function' && typeof contractExactScheduleMatch==='function',{timeout:180000});

  const quick=await page.evaluate(()=>{
    const mk=(address)=>({district:'내덕2동',address,roadAddress:address,jibunAddress:'',legalRi:'',lat:36.67,lng:127.49});
    const exact=contractExactScheduleMatch('general',mk('충청북도 청주시 청원구 공항로84번길 30'));
    const other=contractExactScheduleMatch('general',mk('충청북도 청주시 청원구 공항로84번길 29'));
    const badRoad=(CONTRACT_ROUTES.general||[]).filter(r=>r.provider==='제일환경'&&r.plate==='95오0147'&&(r.districts||[]).includes('내덕2동'));
    const sourceApartment=(CONTRACT_SOURCE_DATA.routes?.general||[]).filter(r=>r.provider==='제일환경'&&r.plate==='95오0147'&&(r.districts||[]).includes('내덕2동'));
    const specials=(CONTRACT_SPECIAL_POINTS||[]).filter(r=>r.provider==='제일환경'&&r.vehicle==='95오0147'&&r.district==='내덕2동');
    return {
      version: DONG_ROUTE_CACHE_VERSION,
      exact,other,badRoad,sourceApartment,specials,
      directGeneral:ROUTE_DONG_SCOPE?.general?.['6157']||[],
      directRecycle:ROUTE_DONG_SCOPE?.recycle?.['0261']||[]
    };
  });
  if(!String(quick.version).includes('v75-naedeok2-apartment-only'))throw new Error('v75 cache version missing: '+quick.version);
  if(quick.badRoad.length!==0)throw new Error('contractor road route still active: '+JSON.stringify(quick.badRoad));
  if(quick.sourceApartment.length!==1 || quick.sourceApartment[0].housing!=='apartment')throw new Error('source route not reclassified as apartment: '+JSON.stringify(quick.sourceApartment));
  if(quick.specials.length!==1 || !String(quick.specials[0].address).includes('공항로84번길 30'))throw new Error('exact Haegadeun special point invalid: '+JSON.stringify(quick.specials));
  if(!quick.exact || quick.exact.provider!=='제일환경' || !['화','목','토'].every(d=>(quick.exact.days||[]).includes(d)))throw new Error('Haegadeun exact schedule failed: '+JSON.stringify(quick.exact));
  if(quick.other)throw new Error('other Gonghang-ro address incorrectly matched contractor: '+JSON.stringify(quick.other));
  if(!quick.directGeneral.includes('내덕2동'))throw new Error('direct general 6157 lost Naedeok2');
  if(!quick.directRecycle.includes('내덕2동'))throw new Error('direct recycle 0261 lost Naedeok2');

  await page.waitForFunction(()=>window.__CJWASTE_PRECOMPUTE_READY===true,{timeout:1500000,polling:1000});
  const state=await page.evaluate(()=>({
    data:window.exportCjWastePrecomputed(),
    failed:[...(window.__CJWASTE_ROUTE_PROXY_FAILED_LEGS||[])]
  }));
  if(errors.length)throw new Error('Page errors: '+errors.join(' | '));
  if(state.data?.version!=='v75-naedeok2-apartment-only')throw new Error('wrong export version '+state.data?.version);
  const routeJson=JSON.stringify(state.data?.routes||[]);
  if(routeJson.includes('95오0147|내덕2동'))throw new Error('precomputed contractor road geometry still contains Naedeok2 95오0147');
  const report={
    version:state.data?.version,
    routeCount:state.data?.routes?.length||0,
    generalZones:state.data?.zones?.general?.length||0,
    recycleZones:state.data?.zones?.recycle?.length||0,
    unresolvedLegCount:state.failed.length,
    quick,
    pageErrors:errors,
    noNaedeok2ContractRoad:!routeJson.includes('95오0147|내덕2동')
  };
  fs.writeFileSync('/tmp/v75-precomputed.json',JSON.stringify(state.data));
  fs.writeFileSync('tools/v75_naedeok2_verify_report.json',JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
