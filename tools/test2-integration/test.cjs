const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..');process.chdir(root);
const html=fs.readFileSync('cjwaste-test2/index.html','utf8');let js=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const read=p=>JSON.parse(fs.readFileSync(p));const nodes={},requests=[];
const document={createElement:()=>({}),getElementById:id=>nodes[id]||(nodes[id]={dataset:{src:'cjwaste-test2/data/routes-integrated-manifest-v1.json'},getAttribute:()=>'',textContent:'',innerHTML:'',appendChild:()=>{},classList:{contains:()=>true}})};
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document,localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{},fetch:async p=>{requests.push(p);return {ok:true,json:async()=>read(p.split('?')[0])}}});
vm.runInContext(js,ctx);ctx.districts=read('tools/test2-connected/context.json').districts;
vm.runInContext('for(const [d,f] of Object.entries(districts))districtFeatureMap.set(d,f)',ctx);
(async()=>{
 await vm.runInContext("loadExternalBundledPrecomputedData('general',['우암동'])",ctx);
 assert(requests.length===2,'address should fetch manifest + one district chunk');
 assert(vm.runInContext("bundledPrecomputedExternal.routes.every(r=>r.type==='general'&&r.districts.includes('우암동'))",ctx));
 const n=requests.length;await vm.runInContext("Promise.all([loadExternalBundledPrecomputedData('general',['우암동']),loadExternalBundledPrecomputedData('general',['우암동'])])",ctx);assert.equal(requests.length,n,'duplicate network read');
 const all=await vm.runInContext("loadExternalBundledPrecomputedData('all')",ctx);assert.equal(all.routes.length,113);assert.equal(new Set(all.routes.map(r=>[r.type,r.vehicle,r.day,r.scopeSignature].join('|'))).size,113);
 for(const r of read('cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json').routes){const x=all.routes.find(x=>x.type===r.type&&x.vehicle===r.vehicle&&x.day===r.day&&x.scopeSignature===r.scopeSignature);assert(x,'missing rural');assert.equal(JSON.stringify(x.data),JSON.stringify(r.data),'rural altered');}
 for(const r of read('data/precomputed-uam-contractor-routes-v1.json').routes){const x=all.routes.find(x=>x.type===r.type&&x.vehicle===r.vehicle&&x.day===r.day);assert(x);const lines=new Set(x.data.segments.map(JSON.stringify));assert(r.data.segments.every(s=>lines.has(JSON.stringify(s))),'latest Uam segment lost');}
 ctx.records=all.routes;
 const audits=vm.runInContext("records.filter(r=>r.vehicle.startsWith('현대환경')||r.districts.includes('우암동')||r.data.connectionVersion==='road-network-v1').map(r=>({vehicle:r.vehicle,day:r.day,...finalRouteCoordinateAudit(bundleRouteRecordSpec(r,allDongRouteSpecs()),r.data)}))",ctx);
 assert(audits.every(a=>a.ok),'corrected geometry scope failure '+JSON.stringify(audits.filter(a=>!a.ok)));
 const checks=vm.runInContext(`(()=>{
 const c={district:'내수읍',legalRi:'도원리',lat:36.7,lng:127.5,address:'내수읍 도원리'};
 const m=userConfirmedSchedule('general',c);if(m.days.join()!=='월'||m.vehicle!=='6138')throw Error('Dowon override');
 const z=normalizeProductionZoneSchedule('general',{district:'내수읍',riName:'도원리',days:['화']});if(z.days.join()!=='월')throw Error('Dowon zone');
 renderReviewedSchedule('general',m,c);if(!document.getElementById('generalBadge').textContent.includes('월')||addressLayerFocus.general.days.join()!=='월')throw Error('card/focus mismatch');
 renderReviewedSchedule('recycle',null,c);if(!document.getElementById('recycleDetail').innerHTML.includes('300세대'))throw Error('apartment note missing');
 const chosen=bestCheongjuPlace([{place_name:'가게',address_name:'서울특별시',x:'1',y:'1'},{place_name:'가게',address_name:'청주시 청원구',x:'2',y:'2'}],'가게');if(chosen.x!=='2')throw Error('non-Cheongju search');
 if(!PLACE_ADDRESS_FALLBACKS['청원구청']||!PLACE_ADDRESS_FALLBACKS['헤이븐헤어'])throw Error('search regression');
 return {dowonCardAndFocus:true,cheongjuSearch:true,apartmentNotice:true};})()`,ctx);
 const report={ok:true,rows:all.routes.length,chunks:requests.length-1,firstDistrictFetches:2,ruralUnchanged:20,uamLatestPreserved:15,scopeChecks:audits.length,...checks};fs.writeFileSync('tools/test2-integration/test-report.json',JSON.stringify(report,null,2));console.log(report);
})().catch(e=>{console.error(e);process.exit(1)});
