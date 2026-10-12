const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('cjwaste-test2/index.html','utf8');
function extract(name){
  const start=html.indexOf('function '+name+'('); assert(start>=0);
  const end=html.indexOf('\n}',start)+2; return html.slice(start,end);
}
const context=vm.createContext({});
vm.runInContext(['geoPointKm','pointSegmentDistanceKm','routeItemDistanceKm','test2RouteReplacementPreservesCoverage'].map(extract).join('\n'),context);
const allow=context.test2RouteReplacementPreservesCoverage;
const a={lat:36.7,lng:127.5},b={lat:36.7,lng:127.51},c={lat:36.7,lng:127.52};
const old={segments:[[a,b,c]],missingTerms:['미복원'],missingRoadTerms:[]};
assert.equal(allow(old,{...old,segments:[[a,b]]}),false,'partial rebuild must not remove the last road');
assert.equal(allow(old,{...old,segments:[]}),false,'empty rebuild must preserve the old route');
assert.equal(allow(old,{...old,missingTerms:['미복원','새누락']}),false,'new missing source terms must reject replacement');
assert.equal(allow(old,{...old,missingRoadTerms:['새누락도로']}),false,'new missing roads must reject replacement');
assert.equal(allow(old,{...old,missingTerms:[]}),true,'same geometry with resolved terms is accepted');
const build=html.slice(html.indexOf('async function buildDongRouteOverlay('),html.indexOf('function routeLayerMatchedColor('));
assert(build.indexOf('!test2RouteReplacementPreservesCoverage')<build.indexOf('await putCachedDongRoute'),'guard must run before cache writes');
const bundle=JSON.parse(fs.readFileSync('cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json'));
assert.equal(bundle.routes.length,20);
assert(html.includes("DONG_ROUTE_CACHE_VERSION='"+bundle.version+"'"));
console.log('PASS: partial/empty/missing-term regressions, cache write order, 20-route version match');
