function villageRouteTerm(term){
  const t=String(term||'').trim().replace(/\s*(?:일대|일부|일원)$/,'').trim();
  const m=t.match(/^(?:(?:청주시\s*)?(?:청원구\s*)?(?:내수읍|오창읍|북이면)\s+)?([가-힣]+\d*(?:리|구))$/);
  if(!m||/(?:사거리|스토리)$/.test(m[1]))return '';
  return m[1].replace(/구$/,'리');
}
function villageRouteKey(term,spec){
  return routeAllowedDistricts(spec).filter(d=>['내수읍','오창읍','북이면'].includes(d)).sort().join(',')+'|'+villageRouteTerm(term);
}
function villageRouteTargets(){
  const targets=new Map();
  for(const spec of allDongRouteSpecs()){
    if(spec.provider||!routeAllowedDistricts(spec).some(d=>['내수읍','오창읍','북이면'].includes(d)))continue;
    for(const d of routeDescriptorsForMap(spec.raw)){
      const village=villageRouteTerm(d.term);if(!village)continue;
      const key=villageRouteKey(d.term,spec);
      if(!targets.has(key))targets.set(key,{key,village,districts:routeAllowedDistricts(spec).filter(d=>['내수읍','오창읍','북이면'].includes(d)),terms:[],uses:[]});
      const target=targets.get(key);if(!target.terms.includes(d.term))target.terms.push(d.term);
      target.uses.push({type:spec.type,vehicle:spec.vehicle,day:spec.day,scopeSignature:routeScopeSignature(spec),rawTerm:d.term});
    }
  }
  return [...targets.values()];
}
async function matchVillageFacility(target){
  const compact=s=>String(s||'').replace(/\s/g,'');
  const name=target.village,stem=name.replace(/리$/,'');
  const keyword=query=>new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error('facility search timed out: '+query)),20000);
    places.keywordSearch(query,(rows,status)=>{clearTimeout(timer);if(status===kakao.maps.services.Status.ERROR)reject(Error('facility search error: '+query));else resolve(rows||[]);},{size:15});
  });
  const results=[],candidates=[];
  for(const district of target.districts){
    for(const kind of ['마을회관','경로당']){
      const query='청주 '+district+' '+name+' '+kind;
      let rows=await keyword(query);
      if(!rows.length)rows=await keyword('청주 '+district+' '+stem+' '+kind);
      candidates.push(...rows.map(r=>({name:r.place_name,address:r.address_name,roadAddress:r.road_address_name,lat:+r.y,lng:+r.x,query,id:r.id})));
      const matches=rows.filter(r=>{
        const n=compact(r.place_name),a=String(r.address_name||'');
        if(!a.includes('청원구')||!a.includes(district))return false;
        if(kind==='마을회관'?!/회관/.test(n):!/경로당|노인정/.test(n))return false;
        const numbered=/\d/.test(name);
        const stemBase=stem.replace(/\d+$/,'');
        const nameMatch=numbered?new RegExp(stem+'(?:리|구|마을|경로|노인)').test(n):(n.includes(name)||n.startsWith(stemBase));
        const legalMatch=a.includes(' '+stemBase+'리 ');
        if(!nameMatch||(!numbered&&!legalMatch))return false;
        return pointInsideRouteDistricts({lat:+r.y,lng:+r.x},[district]);
      });
      const unique=[...new Map(matches.map(r=>[r.id,r])).values()];
      if(unique.length){
        results.push(...unique.map(r=>({lat:+r.y,lng:+r.x,name:r.place_name,address:r.road_address_name||r.address_name,jibunAddress:r.address_name,district,source:kind==='마을회관'?'village-hall':'village-senior-center',placeId:r.id,sourceUrl:r.place_url||'https://place.map.kakao.com/'+r.id,query})));
        break;
      }
    }
  }
  const facilities=[];for(const f of results)if(!facilities.some(p=>routePointDistance(p,f)<.02))facilities.push(f);
  return {...target,status:facilities.length?'matched':'unresolved',facilities,candidates};
}
