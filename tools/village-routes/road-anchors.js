const villageRoadAnchorCache=new Map();
async function villageRoadAnchors(facility,spec){
  const key=facility.address+'|'+routeScopeSignature(spec);
  if(villageRoadAnchorCache.has(key))return villageRoadAnchorCache.get(key);
  const work=(async()=>{
    let address=facility.address,road=roadNameFromAddress(address);
    if(!road){
      const own=await addressSearchPromise(address);
      const found=own.find(p=>p.road_address&&routePointDistance(facility,{lat:+p.y,lng:+p.x})<.05);
      if(found){address=found.road_address.address_name;road=roadNameFromAddress(address);}
    }
    if(!road)return [];
    const all=(await searchRoadAnchorPlaces(road)).filter(p=>pointInsideRouteDistricts(p,routeAllowedDistricts(spec)));
    let near=all.filter(p=>routePointDistance(facility,p)<=.18&&routePointDistance(facility,p)>.015);
    const number=roadHouseNumberFromAddress(address,road);
    if(near.length<2&&Number.isFinite(number)){
      const suffix=address.match(/\s\d+-(\d+)/)?.[1];
      const numbers=[-6,-4,-2,-1,1,2,4,6].map(n=>String(number+n)).filter(n=>+n>0);
      if(suffix)numbers.push(...[-4,-2,-1,1,2,4].map(n=>number+'-'+(+suffix+n)).filter(n=>+n.split('-')[1]>0));
      const rows=(await Promise.all(numbers.map(n=>addressSearchPromise('청주시 청원구 '+road+' '+n)))).flat();
      for(const r of rows){
        const a=r.road_address?.address_name||r.address_name||'',p={lat:+r.y,lng:+r.x,address:a,sampleNo:roadSampleOrder(a,road)};
        if(roadNameFromAddress(a)!==road||!pointInsideRouteDistricts(p,routeAllowedDistricts(spec)))continue;
        const distance=routePointDistance(facility,p);
        if(distance>.015&&distance<=.18)near.push(p);
      }
    }
    // An exact facility address remains an endpoint even when only one neighboring address exists.
    near=uniqueRoutePoints(near).sort((a,b)=>routePointDistance(facility,a)-routePointDistance(facility,b)).slice(0,5);
    if(!near.length){
      // A longer road lookup is clipped to the 180 m facility neighborhood before display.
      const closest=all.filter(p=>routePointDistance(facility,p)>.015).sort((a,b)=>routePointDistance(facility,a)-routePointDistance(facility,b))[0];
      if(closest)near=[closest];
    }
    return near.length?orderedRoadSamples([...near,{...facility,address,sampleNo:roadSampleOrder(address,road)}],6):[];
  })();
  villageRoadAnchorCache.set(key,work);return work;
}
function clipVillageFacilitySegments(segments,center,radiusKm=.18){
  const origin=geoPointKm(center.lat,center.lng),out=[];
  for(const segment of segments||[]){
    let chain=[];
    const flush=()=>{if(chain.length>=2)out.push(chain);chain=[];};
    for(let i=1;i<segment.length;i++){
      const a=segment[i-1],b=segment[i],p=geoPointKm(a.lat,a.lng),q=geoPointKm(b.lat,b.lng);
      const x=p.x-origin.x,y=p.y-origin.y,dx=q.x-p.x,dy=q.y-p.y;
      const A=dx*dx+dy*dy,B=2*(x*dx+y*dy),C=x*x+y*y-radiusKm*radiusKm;
      if(A<1e-16)continue;
      const discriminant=B*B-4*A*C;
      if(discriminant<0){flush();continue;}
      const root=Math.sqrt(discriminant),lo=Math.max(0,(-B-root)/(2*A)),hi=Math.min(1,(-B+root)/(2*A));
      if(lo>hi){flush();continue;}
      const point=t=>({lat:a.lat+(b.lat-a.lat)*t,lng:a.lng+(b.lng-a.lng)*t});
      const start=point(lo),end=point(hi);
      if(chain.length&&routePointDistance(chain[chain.length-1],start)>.001)flush();
      if(!chain.length)chain.push(start);chain.push(end);
      if(hi<1)flush();
    }
    flush();
  }
  return out;
}
