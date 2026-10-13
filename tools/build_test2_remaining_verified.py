import asyncio,copy,json,math,os,time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json'
REPORT=ROOT/'tools/test2-remaining-verified-report.json'
URL='https://yongseongk94.github.io/cjwaste/cjwaste-test2/'
IDS={'오창농협급식지원센터':'8026400','오창초':'8019281','체리부로':'17772709','팔결교':'10884349','진성레미컨':'26080540','장재교차로':'25626523','다모아패키지':'892195736','풍정교차로':'25625160','세교사거리':'7950697','비중사거리':'15139449','초정어린이집':'8912767','영하보건소':'9320509','창리사거리':'15141446','구룡에너지':'17912505','오창중':'10618649','수성초':'7971482','내수성당':'14527772'}
ADDRESSES={
 '해든전원마을':{'name':'해든전원마을 원본 코스표 주소','address':'청주시 청원구 오창읍 가곡길 181-53','sourceUrl':'repository:DIRECT_ROUTES.recycle.0262.월'},
 '가곡길181-53':{'name':'가곡길 181-53','address':'청주시 청원구 오창읍 가곡길 181-53','sourceUrl':'repository:DIRECT_ROUTES.recycle.0262.월'},
 '대길2리경로당':{'name':'대길2리경로당','address':'청주시 청원구 북이면 대길리 179-13','sourceUrl':'https://fshh.purpleo.co.kr/view/13641'},
 '정도안전산업':{'name':'정도안전산업','address':'청주시 청원구 내수읍 풍정3길 38','sourceUrl':'https://www.saramin.co.kr/zf_user/company-info/view/csn/SGFKb0E0ZVdDTGp4VEVHYTNTa2RMQT09/company_nm/%28%EC%A3%BC%29%EC%A0%95%EB%8F%84%EC%95%88%EC%A0%84%EC%82%B0%EC%97%85'}
}
async def main():
 bundle=json.loads(BUNDLE.read_text());before=copy.deepcopy(bundle)
 lookup={r['term']:r for r in json.loads((ROOT/'tools/test2-remaining-location-lookup.json').read_text())['rows']}
 matches=json.loads((ROOT/'cjwaste-test/data/precomputed-village-connected-v2.json').read_text())['matches']
 results=json.loads(REPORT.read_text())['results'] if REPORT.exists() else []
 async with async_playwright() as pw:
  proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
  browser=await pw.chromium.launch(headless=True,proxy={'server':proxy} if proxy else None)
  page=await browser.new_page(ignore_https_errors=True)
  async def asset(route):
   path=urlsplit(route.request.url).path.removeprefix('/cjwaste/');file=ROOT/(path+'index.html' if path.endswith('/') else path)
   if file.is_file():await route.fulfill(path=str(file))
   else:await route.continue_()
  await page.route('https://yongseongk94.github.io/cjwaste/**',asset)
  await page.goto(URL,wait_until='domcontentloaded',timeout=90000)
  await page.wait_for_function("typeof places!=='undefined'&&!!places",timeout=120000)
  await page.evaluate('async()=>{await ensureTestAdminBoundaryLoad();await hydrateExternalBundledPrecomputedData();}')
  await page.evaluate('(matches)=>{window.villageMatches=new Map(matches.map(m=>[m.key,m]));}',matches)
  await page.add_script_tag(content=(ROOT/'tools/village-routes/road-anchors.js').read_text())
  for term,row in lookup.items():
   point=None;mode='facility'
   if term=='영하1리버스정류장':point={'name':'영하1리 버스정류장','address':'청주시 청원구 북이면 초정약수로','lat':36.72142,'lng':127.58577,'sourceUrl':'https://busmaps.com/ko/south-korea/public_transit-stop-%EC%98%81%ED%95%981%EB%A6%AC-7614972175860400161','dataProvider':'KTDB GTFS'}
   elif term in IDS:point=next((x for x in row['results'] if x['id']==IDS[term]),None)
   elif term in ADDRESSES:
    hint=ADDRESSES[term]
    found=await page.evaluate('''async hint=>{
     const rows=await new Promise(resolve=>geocoder.addressSearch(hint.address,(r,s)=>resolve(s===kakao.maps.services.Status.OK?r:[])));
     return rows.map(r=>({...hint,lat:+r.y,lng:+r.x,jibunAddress:r.address?.address_name||r.address_name,address:r.road_address?.address_name||r.address_name,district:routePointAnyDistrict({lat:+r.y,lng:+r.x})}));
    }''',hint)
    if len(found)==1:point=found[0]
   elif term=='양지리':point=next(f for m in matches if m['village']=='양지리' for f in m['facilities'])
   elif term in ['초정구길','내수로','각리']:
    mode='road'
   else:
    results.append({'term':term,'status':'needs-source-location','uses':row['uses']});continue
   if mode=='facility' and not point:
    results.append({'term':term,'status':'location-unresolved','uses':row['uses']});continue
   for use in row['uses']:
    route=next(r for r in bundle['routes'] if all(r[k]==use[k] for k in ['type','vehicle','day','scopeSignature']))
    if term not in route['data']['missingTerms']:continue
    print('BUILD',term,use['vehicle'],use['day'],mode,flush=True)
    try:
     result=await asyncio.wait_for(page.evaluate('''async ({term,use,point,mode})=>{
      const spec=allDongRouteSpecs().find(s=>s.type===use.type&&s.vehicle===use.vehicle&&s.day===use.day&&routeScopeSignature(s)===use.scopeSignature);
      if(!spec)throw Error('source spec missing');
      let segments=[],evidence=[],complete=false,roadTerm='';
      if(mode==='road'){
       roadTerm=term==='각리'?'각리2길':term;
       const anchors=orderedRoadSamples((await searchRoadAnchorPlaces(roadTerm)).filter(p=>pointInsideRouteDistricts(p,routeAllowedDistricts(spec))),24);
       if(anchors.length<2)return {ok:false,reason:'not-enough-road-addresses',anchors};
       const road=await fetchRoadFollowingPath(anchors);
       complete=!!road&&!(road.failedLegs||[]).length;
       segments=(road?.segments||[]).flatMap(s=>clipRoutePathToDistricts(s,routeAllowedDistricts(spec)));
       evidence=anchors.map(p=>({...p,term,source:'verified-road-address',villageTerm:term==='각리'?'각리':''}));
      }else{
       point={...point,term,villageTerm:term==='양지리'?'양지리':'',source:'verified-source-location'};
       if(!pointInsideRouteDistricts(point,routeAllowedDistricts(spec)))return {ok:false,reason:'outside-source-district',point};
       const anchors=await villageRoadAnchors(point,spec);
       if(anchors.length<2)return {ok:false,reason:'not-enough-nearby-road-addresses',point};
       const road=await fetchVillageFacilityRoad(anchors,point,spec);
       segments=(road?.segments||[]).flatMap(s=>clipRoutePathToDistricts(s,routeAllowedDistricts(spec)));
       complete=!!road&&!(road.failedLegs||[]).length;
       evidence=[point];
      }
      const audit=finalRouteCoordinateAudit(spec,{segments,zoneEvidencePoints:evidence});
      const nearestM=mode==='facility'?routeItemDistanceKm({segments},point.lat,point.lng)*1000:null;
      return {ok:complete&&audit.ok&&segments.length>0&&(nearestM===null||nearestM<=80),segments,evidence,audit,nearestM,complete,roadTerm};
     }''',{'term':term,'use':use,'point':point,'mode':mode}),timeout=180)
     if result['ok']:
      data=route['data'];keys={json.dumps(s,sort_keys=True) for s in data['segments']}
      for seg in result['segments']:
       k=json.dumps(seg,sort_keys=True)
       if k not in keys:data['segments'].append(seg);keys.add(k)
      for point2 in result['evidence']:
       prior=next((p for p in data['zoneEvidencePoints'] if p.get('term')==term and abs(p['lat']-point2['lat'])<1e-6 and abs(p['lng']-point2['lng'])<1e-6),None)
       if prior:prior.update(point2)
       else:data['zoneEvidencePoints'].append(point2)
      data['missingTerms'].remove(term)
      road=result.get('roadTerm')
      if road:
       data['missingRoadTerms']=[t for t in data.get('missingRoadTerms',[]) if t!=road]
       if road not in data['coveredRoadTerms']:data['coveredRoadTerms'].append(road)
      data['distance']=round(sum(math.hypot((b['lat']-a['lat'])*111000,(b['lng']-a['lng'])*88000) for s in data['segments'] for a,b in zip(s,s[1:])))
      route['audit'].update(segments=len(data['segments']),evidence=len(data['zoneEvidencePoints']),missingTerms=data['missingTerms'],missingRoadTerms=data['missingRoadTerms'])
      BUNDLE.write_text(json.dumps(bundle,ensure_ascii=False,separators=(',',':')))
     results.append({'term':term,**use,'status':'repaired' if result['ok'] else 'road-unresolved',**result})
     print('RESULT',term,use['vehicle'],use['day'],result['ok'],result.get('nearestM'),flush=True)
    except Exception as error:
     results.append({'term':term,**use,'status':'error','error':str(error)});print('ERROR',term,str(error),flush=True)
    REPORT.write_text(json.dumps({'beforeRemaining':41,'afterRemaining':sum(len(r['data']['missingTerms']) for r in bundle['routes']),'results':results},ensure_ascii=False,indent=2))
  REPORT.write_text(json.dumps({'beforeRemaining':41,'afterRemaining':sum(len(r['data']['missingTerms']) for r in bundle['routes']),'results':results},ensure_ascii=False,indent=2))
  await browser.close()
asyncio.run(main())
