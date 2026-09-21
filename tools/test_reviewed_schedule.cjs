const fs=require('fs'),vm=require('vm'),assert=require('assert');
const path=require('path');
const root=path.resolve(__dirname,'..');

const html=fs.readFileSync(root+'/cjwaste-test/index.html','utf8');
let js=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)].map(m=>m[1]).join('\n');
js=js.slice(0,js.lastIndexOf("document.getElementById('landingForm').addEventListener"));
const ctx=vm.createContext({console,URLSearchParams,location:{search:''},window:{},document:{getElementById:()=>({getAttribute:()=>'',textContent:'',classList:{contains:()=>true}})},localStorage:{getItem:()=>null},setTimeout,clearTimeout,requestAnimationFrame:()=>{},polygonClipping:require(root+'/cjwaste-test/vendor/polygon-clipping-0.15.7.min.js')});
vm.runInContext(js,ctx);

const check=code=>vm.runInContext(code,ctx);
assert(check("exactSourceAddressMatch('주중동 304-1','청주시 청원구 주중동304-1')"));
assert(!check("exactSourceAddressMatch('주중동 304-1','주중동 304-10')"));
assert(!check("exactSourceAddressMatch('상당로 230','상당로 2300')"));
assert(!check("exactSourceAddressMatch('상리로 18','상리로18번길 3')"));
assert(!check("scheduleRouteAllowed('general','6224','수')"));
assert(check("scheduleRouteAllowed('recycle','6224','수')"));
check("currentJibunAddress='주중동 304-1';currentLookupText='주중동304-1'");
assert.equal(check("userConfirmedSchedule('general',{district:'오근장동',address:'주중동 304-10'})"),null);
assert.equal(check("userConfirmedSchedule('general',{district:'오근장동',lat:36.7,lng:127.5})"),null);
assert.equal(check("userConfirmedSchedule('general',{district:'오근장동',address:'주중동 304-1'}).vehicle"),'6224');
assert.equal(check("userConfirmedSchedule('recycle',{district:'오근장동',address:'주중동 304-1'}).days.join()"),'수');
assert.equal(check("nearestScheduleDisplayZone('general','우암동',36.66,127.48).days.length"),0);
assert(check("validReviewZone({type:'general',days:['월'],points:[{lat:36.6,lng:127.4},{lat:36.7,lng:127.4},{lat:36.6,lng:127.5}]})"));
assert(!check("validReviewZone({type:'general',days:['전체'],points:[]})"));
console.log('PASS exact parcel, side road, held route, no address leakage, unknown area, reviewed schema');
check(`
localAllowedRouteKeys=()=>new Set(['A|월','A|수','A|금','B|화']);
const testSpecs=[['A','월',0],['A','수',0],['A','금',.001],['B','화',.0013]];
const synthetic={routes:testSpecs.map(([vehicle,day,offset])=>({type:'general',vehicle,day,liveSpec:{type:'general',vehicle,day,districts:['우암동'],raw:''},data:{segments:[[{lat:36.65+offset,lng:127.48},{lat:36.65+offset,lng:127.481}]]}}))};
localScheduleIndexes.general=buildLocalScheduleIndex('general',synthetic);
`);
assert.equal(check("localScheduleAtPoint('general',{district:'우암동',lat:36.65,lng:127.4805}).days.join('·')"),'월·수');
assert.equal(check("localScheduleAtPoint('general',{district:'우암동',lat:36.65,lng:127.4805}).estimated"),true);
assert.equal(check("localScheduleAtPoint('general',{district:'우암동',lat:36.68,lng:127.49})"),null);
assert.equal(check("serviceZoneOverlayMatch('general',{district:'우암동',lat:36.65,lng:127.4805}).days.join('·')"),check("nearestScheduleDisplayZone('general','우암동',36.65,127.4805).days.join('·')"));
console.log('PASS local weekday grouping, distance cutoff, estimated line, same-point consistency');
