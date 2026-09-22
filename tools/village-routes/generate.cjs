const fs=require('fs'),puppeteer=require('puppeteer-core');
(async()=>{
 const browser=await puppeteer.launch({headless:true,protocolTimeout:1800000,executablePath:process.env.CHROME_BIN,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  const page=await browser.newPage();page.setDefaultTimeout(1800000);
  page.on('console',m=>{if(m.text().startsWith('VILLAGE'))console.log(m.text());});
  await page.goto('https://yongseongk94.github.io/cjwaste/cjwaste-test/?village-build='+Date.now(),{waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForFunction(()=>typeof geocoder!=='undefined'&&!!geocoder);
  await page.evaluate(()=>ensureTestAdminBoundaryLoad());
  await page.addScriptTag({content:fs.readFileSync('tools/village-routes/match.js','utf8')});
  const matches=await page.evaluate(async()=>{
    const targets=villageRouteTargets(),out=[];
    for(const target of targets){const row=await matchVillageFacility(target);out.push(row);console.log('VILLAGE',out.length,targets.length,row.key,row.status,row.facilities.map(f=>f.name).join(','));}
    return out;
  });
  fs.writeFileSync('tools/village-routes/matches.json',JSON.stringify({generatedAt:new Date().toISOString(),source:'Kakao Maps place search; district polygon checked',matches},null,2));
  console.log('MATCH_SUMMARY',JSON.stringify(matches.reduce((a,r)=>(a[r.status]=(a[r.status]||0)+1,a),{})));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
