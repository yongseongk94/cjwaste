import asyncio,json,os,time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tools/test2-remaining-location-lookup.json'
URL='https://yongseongk94.github.io/cjwaste/cjwaste-test2/'
async def main():
 bundle=json.loads((ROOT/'cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json').read_text())
 terms={}
 for r in bundle['routes']:
  for t in r['data']['missingTerms']:
   row=terms.setdefault(t,{'term':t,'uses':[],'evidence':[]})
   row['uses'].append({k:r[k] for k in ['type','vehicle','day','districts','scopeSignature']})
   for e in r['data']['zoneEvidencePoints']:
    if e.get('term')==t and e not in row['evidence']:row['evidence'].append(e)
 async with async_playwright() as pw:
  proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
  browser=await pw.chromium.launch(headless=True,proxy={'server':proxy} if proxy else None)
  page=await browser.new_page(ignore_https_errors=True)
  await page.goto(URL,wait_until='domcontentloaded',timeout=90000)
  await page.wait_for_function("typeof places!=='undefined'&&!!places",timeout=120000)
  await page.evaluate('async()=>await ensureTestAdminBoundaryLoad()')
  rows=[]
  for term,row in terms.items():
   result=await page.evaluate('''async ({term,uses,evidence})=>{
    const aliases={'오창농협급식지원센터':['오창농협 학교급식지원센터','오창농협 친환경농산물유통센터'],'체리부로':['체리부로 오창','처갓집양념치킨 오창 공장'],'대길2리경로당':['대길2리 경로당','대길리 경로당'],'정도안전산업':['정도안전산업','정도산업 내수'],'영하1리버스정류장':['영하1리 버스정류장','영하1리'],'해든전원마을':['해든전원마을','해든 전원마을'],'장재문화마을':['장재문화마을','장재리 문화마을'],'도암리':['도암리 마을회관','도암리 경로당','도암리 버스정류장','도암리 노인정'],'초정구길':['초정구길'],'내수로':['내수로']};
    const allowed=[...new Set(uses.flatMap(u=>u.districts))];
    const queries=[...new Set([term,...(aliases[term]||[]),...evidence.map(e=>e.name).filter(Boolean)])].map(q=>'청주시 청원구 '+q);
    const results=[];
    for(const query of queries){
     const found=await new Promise(resolve=>places.keywordSearch(query,(r,s)=>resolve(s===kakao.maps.services.Status.OK?r:[])));
     results.push(...found.map(r=>({name:r.place_name,address:r.road_address_name||r.address_name,jibunAddress:r.address_name,lat:+r.y,lng:+r.x,sourceUrl:r.place_url,query,id:r.id,district:routePointAnyDistrict({lat:+r.y,lng:+r.x}),category:r.category_name})));
    }
    const unique=[...new Map(results.map(r=>[r.id,r])).values()];
    return {allowed,results:unique};
   }''',row)
   row.update(result);rows.append(row);OUT.write_text(json.dumps({'queriedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'rows':rows},ensure_ascii=False,indent=2))
   print(term,json.dumps(result['results'],ensure_ascii=False),flush=True)
  await browser.close()
asyncio.run(main())
