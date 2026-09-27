const fs=require('fs'),puppeteer=require('puppeteer-core');
(async()=>{
 const browser=await puppeteer.launch({headless:true,executablePath:process.env.CHROME_BIN,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();await page.goto('https://yongseongk94.github.io/cjwaste/cjwaste-test/',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>typeof geocoder!=='undefined'&&!!geocoder);
  const bundle=JSON.parse(fs.readFileSync('cjwaste-test/data/precomputed-hyundai-v1.json')),network=JSON.parse(fs.readFileSync('tools/hyundai-routes/road-network.json'));
  const output=await page.evaluate(async({bundle,network})=>{
   await ensureTestAdminBoundaryLoad();
   const nodes=new Map(),edges=new Map(),adj=new Map();
   for(const w of network.ways){
    const t=w.tags;
    if(!['residential','living_street','unclassified'].includes(t.highway)&&!(t.highway==='service'&&t.service==='alley'))continue;
    if(['access','vehicle','motor_vehicle','motorcar'].some(k=>['no','private','customers','permit'].includes(t[k])))continue;
    for(let i=1;i<w.nodes.length;i++){
     const a=w.nodes[i-1],b=w.nodes[i],p=w.points[i-1],q=w.points[i];
     if(![p,q,...densifyRoutePath([p,q],.015)].every(p=>pointInsideRouteDistricts(p,['내덕1동'])))continue;
     const length=routePointDistance(p,q);if(length<.001)continue;
     const key=[a,b].sort().join('|');if(edges.has(key))continue;
     nodes.set(a,p);nodes.set(b,q);edges.set(key,{a,b,length,wayId:w.id,name:t.name||'',highway:t.highway});
     for(const [from,to] of [[a,b],[b,a]]){if(!adj.has(from))adj.set(from,[]);adj.get(from).push({to,key,length});}
    }
   }
   const report=[];
   for(const r of bundle.routes){
    const selected=new Set(),coverage=[];
    for(const p of r.data.travelWaypoints){
     const seed=[...nodes].map(([id,q])=>({id,d:routePointDistance(p,q)})).sort((a,b)=>a.d-b.d)[0];
     if(!seed||seed.d>.15)throw Error('no public neighborhood access '+p.name);
     const dist=new Map([[seed.id,seed.d]]),done=new Set();
     while(true){let id=null,best=Infinity;for(const [n,d] of dist)if(!done.has(n)&&d<best){id=n;best=d;}if(id===null||best>.5)break;done.add(id);for(const e of adj.get(id)||[]){const next=best+e.length;if(next<=.5&&next<(dist.get(e.to)??Infinity))dist.set(e.to,next);}}
     let count=0;for(const [key,e] of edges)if(done.has(e.a)&&done.has(e.b)&&Math.max(dist.get(e.a),dist.get(e.b))<=.5){selected.add(key);count++;}
     if(!count)throw Error('empty neighborhood '+p.name);
     coverage.push({term:p.term,name:p.name,seedDistanceM:Math.round(seed.d*1000),edges:count});
    }
    const local=new Map();for(const k of selected){const e=edges.get(k);for(const [a,b] of [[e.a,e.b],[e.b,e.a]]){if(!local.has(a))local.set(a,[]);local.get(a).push({to:b,key:k});}}
    const used=new Set(),chains=[];
    const walk=(start,first)=>{const chain=[nodes.get(start)];let edge=first;while(edge&&!used.has(edge.key)){used.add(edge.key);chain.push(nodes.get(edge.to));const next=(local.get(edge.to)||[]).filter(x=>!used.has(x.key));edge=(local.get(edge.to)||[]).length===2?next[0]:null;}if(chain.length>1)chains.push(chain);};
    for(const [n,es] of local)if(es.length!==2)for(const e of es)if(!used.has(e.key))walk(n,e);
    for(const [n,es] of local)for(const e of es)if(!used.has(e.key))walk(n,e);
    if(used.size!==selected.size)throw Error('lost road edges');
    const length=[...selected].reduce((n,k)=>n+edges.get(k).length*1000,0);
    r.hyundaiVersion='hyundai-neighborhood-v2';
    Object.assign(r.data,{neighborhoodSegments:chains,neighborhoodDistance:Math.round(length),neighborhoodRoadNames:[...new Set([...selected].map(k=>edges.get(k).name).filter(Boolean))].sort(),neighborhoodCoverage:coverage,neighborhoodPolicy:'내덕1동 · 기준시설에서 도로거리 500m 이내 연결 생활도로 · 수거 여부 미확정',neighborhoodSource:network.source,neighborhoodAttribution:network.license});
    report.push({type:r.type,day:r.day,segments:chains.length,uniqueRoadM:Math.round(length),coverage,roads:r.data.neighborhoodRoadNames});
   }
   bundle.hyundaiVersion='hyundai-neighborhood-v2';return {bundle,report};
  },{bundle,network});
  fs.writeFileSync('cjwaste-test/data/precomputed-hyundai-v2.json',JSON.stringify(output.bundle));fs.writeFileSync('tools/hyundai-routes/neighborhood-report.json',JSON.stringify(output.report,null,2));console.log('HYUNDAI_NEIGHBORHOODS',JSON.stringify(output.report));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
