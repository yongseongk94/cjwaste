const fs=require('fs');
const puppeteer=require('puppeteer-core');
(async()=>{
  const browser=await puppeteer.launch({headless:true,protocolTimeout:1500000,executablePath:process.env.CHROME_BIN,args:['--no-sandbox','--disable-dev-shm-usage']});
  const page=await browser.newPage();
  page.setDefaultTimeout(1500000);
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('https://yongseongk94.github.io/cjwaste/?precompute=v74-'+Date.now(),{waitUntil:'domcontentloaded',timeout:180000});
  await page.waitForFunction(()=>typeof window.exportCjWastePrecomputed==='function',{timeout:180000});
  await page.waitForFunction(()=>window.__CJWASTE_PRECOMPUTE_READY===true,{timeout:1500000,polling:1000});
  const state=await page.evaluate(()=>({
    data:window.exportCjWastePrecomputed(),
    failed:[...(window.__CJWASTE_ROUTE_PROXY_FAILED_LEGS||[])],
    checks:{
      splitHaegadeun:routeDescriptorsForMap('공항로 84번길, 이랜드해가든아파트').map(x=>x.term),
      splitRange:routeDescriptorsForMap('사북로 145~121').map(x=>x.term),
      splitApartments:routeDescriptorsForMap('율량로 17(주공1단지), 율량로 47(주공2단지)').map(x=>x.term),
      splitPois:routeDescriptorsForMap('교서로 222번길 일대 (쉐보레부품,더좋은하우스)').map(x=>x.term)
    }
  }));
  if(errors.length)throw new Error('Page errors: '+errors.join(' | '));
  if(state.data?.version!=='v74-source-multilocation')throw new Error('wrong version '+state.data?.version);
  if(!state.checks.splitHaegadeun.some(x=>String(x).includes('공항로'))||!state.checks.splitHaegadeun.some(x=>String(x).includes('이랜드해가든')))throw new Error('Haegadeun split failed');
  if(state.checks.splitRange.length<2)throw new Error('range split failed');
  if(!state.checks.splitPois.some(x=>String(x).includes('쉐보레부품'))||!state.checks.splitPois.some(x=>String(x).includes('더좋은하우스')))throw new Error('POI split failed');
  fs.writeFileSync('/tmp/v74-precomputed.json',JSON.stringify(state.data));
  fs.writeFileSync('tools/v74_multilocation_precompute_report.json',JSON.stringify({routeCount:state.data?.routes?.length||0,generalZones:state.data?.zones?.general?.length||0,recycleZones:state.data?.zones?.recycle?.length||0,unresolvedLegCount:state.failed.length,checks:state.checks,pageErrors:errors},null,2));
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
