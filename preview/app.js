'use strict';
// 시연 데이터와 서버 자료를 구분하고, DOM에는 textContent로 내용을 넣습니다.
const state = {
  data: window.GREENZONE_DEMO || {candidates:[],buildings:[],rules:[],sources:[],analysis:{plans:[]}},
  apiReady:false, plan:'B', candidate:null, building:null, lastResult:null,
  requests:[], requestsError:'', matchSeq:0, matchAbort:null, requestBusy:false, chatBusy:false,
  map:null, layer:null, locationLayer:null, position:null, locationSeq:0, locating:false, page:'home'
};
function activePlan() { return (state.data.analysis.plans || []).find(p => p.plan_id === state.plan); }
function assignmentFor(id) { return (activePlan()?.assignments || []).find(a => a.building_id === id); }
function candidateFor(id) { return state.data.candidates.find(c => c.candidate_id === id); }
function fingerprint() { return [state.building,$('#categorySelect').value,$('#quantity').value,state.plan].join('|'); }
function invalidateMatch(message) {
  state.matchSeq++;
  if (state.matchAbort) state.matchAbort.abort();
  state.lastResult = null;
  $('#requestButton').disabled = true;
  $('#requestButton').textContent = '데모 요청 등록';
  $('#matchButton').disabled = !state.building;
  $('#matchResult').replaceChildren(el('div',message || '건물을 선택하고 안내를 확인하세요.','result-empty'));
}
function go(page, hash) {
  if(page==='admin'){location.href='admin.html';return;}
  if (!['home','analysis','assistant','architecture'].includes(page)) page = 'home';
  state.page = page;
  ['home','analysis','assistant','architecture'].forEach(p => $('#'+p+'Page').classList.toggle('hidden',p !== page));
  $$('.nav-item').forEach(n => n.classList.toggle('active',n.dataset.page === page));
  $('#crumb').textContent = {home:'거점 지도',analysis:'배치 비교',assistant:'배출 도우미',admin:'정보 관리',architecture:'만드는 과정'}[page];
  if (hash !== false && location.hash !== '#'+page) location.hash = page;
  if (page === 'home' && state.map) setTimeout(() => state.map.invalidateSize(),0);
}
$$('[data-page]').forEach(n => n.addEventListener('click',() => go(n.dataset.page)));
$$('[data-go]').forEach(n => n.addEventListener('click',e => {e.preventDefault();go(n.dataset.go);}));
window.addEventListener('hashchange',() => go(location.hash.slice(1),false));
function setPlan(id) {
  if (!(state.data.analysis.plans || []).some(p => p.plan_id === id)) return;
  state.plan = id; invalidateMatch('배치안이 바뀌었습니다. 배출 안내를 다시 확인해 주세요.'); renderOverview();
}
$('#planButtons').addEventListener('click',e => {const b=e.target.closest('[data-plan]');if(b)setPlan(b.dataset.plan);});
function chooseCandidate(id) {
  state.candidate = id; renderCandidate(); renderMap();
}
function renderOverview() {
  const plan = activePlan(), m = plan?.metrics;
  const allDemo=state.data.candidates.every(c=>c.is_demo) && state.data.buildings.every(b=>b.is_demo);
  $('#datasetBadge').textContent=allDemo?'가상 자료 · 실제 배출 금지':'자료 기반 제안 · 운영 승인 별도';
  $('#scopeBanner').textContent=allDemo?'후보·건물·가구 수·안전 조건은 모두 시연용 가정입니다. 지도 배경은 실제 지리정보이지만, 표시한 지점은 공식 배출장소가 아닙니다.':'자료 기반 제안과 시연 자료는 후보별 출처·상태를 확인하세요. 기관·주민·부지 확인 전 실제 배출 가능 장소로 안내하지 않습니다.';
  $('#countCandidates').textContent = state.data.candidates.length;
  const eligible = state.data.candidates.filter(c => c.eligibility?.eligible).length;
  $('#eligibleCount').textContent = (allDemo?'시연 조건 통과 ':'입력 조건 통과 ')+eligible+'곳 · 운영 확인 별도';
  $('#countBuildings').nextElementSibling.textContent=allDemo?'가상 건물 자료':'등록된 분석 대상 건물';
  $('#countBuildings').textContent = state.data.buildings.length;
  $('#averageDistance').textContent = fmt(m?.average_distance_m,'m');
  $('#unassignedCount').textContent = m ? m.unassigned_buildings : '-';
  $('#areaName').textContent = state.data.study_area?.name || '분석 권역';
  $('#analysisMethod').textContent = state.data.analysis.error || state.data.analysis.method || '분석 자료 확인 필요';
  $$('#planButtons button').forEach(b => b.classList.toggle('selected',b.dataset.plan === state.plan));
  if (!candidateFor(state.candidate)) state.candidate = state.data.candidates[0]?.candidate_id || null;
  renderCandidate(); renderComparison(); renderSources(); renderMap(); renderNearby();
}
function renderCandidate() {
  const choices = $('#candidateChoices'); choices.replaceChildren();
  state.data.candidates.forEach(c => {
    const b = el('button',c.candidate_id.replace('GZ-','')+' '+(reviewLabels[c.review_status] || '검토'), 'candidate-choice');
    b.classList.toggle('selected',state.candidate === c.candidate_id);
    b.classList.toggle('is-held',!c.eligibility?.eligible);
    b.addEventListener('click',() => chooseCandidate(c.candidate_id)); choices.append(b);
  });
  const box = $('#candidateDetail'); box.replaceChildren();
  const c = candidateFor(state.candidate); if (!c) {box.append(el('p','후보 자료가 없습니다.'));return;}
  box.append(el('div',c.is_demo ? '가상 위치 · 실제 배출 금지' : '자료 기반 제안 · 운영 승인 별도','detail-kicker'));
  box.append(el('h3',c.name));
  box.append(el('p',c.rationale || '선정 근거를 입력해 주세요.','candidate-reason'));
  const checks = el('div',null,'safety-tags');
  Object.entries(safetyLabels).forEach(([key,label]) => {
    const value = c[key] || 'unknown';
    checks.append(el('span',label+' · '+(value==='pass'?(c.is_demo?'가정 충족':'검토 적합'):value==='fail'?'부적합':'미확인'),'safety-tag '+value));
  });
  box.append(checks);
  const load = activePlan()?.loads.find(l => l.candidate_id === c.candidate_id);
  const stat = el('div',null,'candidate-stats');
  stat.append(el('div','담당 건물 '+fmt(load?.building_count || 0,'개')));
  stat.append(el('div','담당 수요 '+fmt(load?.demand || 0,' '+(c.capacity_unit || '단위 미확인'))));
  box.append(stat,el('p',c.safety_note || '현장 조건 확인 필요','detail-note'));
  if (!c.eligibility?.eligible) box.append(el('p','배정 보류: '+(c.eligibility?.reasons || []).join(', '),'hold-note'));
  const source = state.data.sources.find(s => s.source_id === c.source_id);
  box.append(el('p','자료: '+(source?.title || c.source_id || '미확인')+' / 기준일 '+(c.checked_at || '미확인'),'detail-meta'));
  if (source?.url) box.append(safeLink(source.url,'근거 원문 보기'));
}
function renderComparison() {
  const cards = $('#comparisonCards'); cards.replaceChildren();
  (state.data.analysis.plans || []).forEach(plan => {
    const card = el('article',null,'plan-card'+(plan.plan_id===state.plan?' active':''));
    card.append(el('div',plan.plan_id+' PLAN','eyebrow'),el('h2',plan.label));
    const m = plan.metrics, rows = el('dl',null,'plan-stats');
    [['활용 후보',fmt(m.candidate_count,'곳')],['배정 건물',fmt(m.assigned_buildings,'개')],['평균 직선거리',fmt(m.average_distance_m,'m')],['최장 직선거리',fmt(m.max_distance_m,'m')],['미배정',fmt(m.unassigned_buildings,'개')]].forEach(([k,v]) => {rows.append(el('dt',k),el('dd',v));});
    const b = el('button',plan.plan_id===state.plan?'현재 선택한 배치':'이 배치 보기','ghost');
    b.addEventListener('click',() => setPlan(plan.plan_id));
    card.append(rows,b); cards.append(card);
  });
  const tbody = $('#loadTable'); tbody.replaceChildren();
  (activePlan()?.loads || []).forEach(load => {
    const tr=el('tr'); [candidateFor(load.candidate_id)?.name || load.candidate_id,fmt(load.building_count,'개'),fmt(load.demand,' '+load.unit),fmt(load.capacity,' '+load.unit)].forEach(v=>tr.append(el('td',v)));tbody.append(tr);
  });
  const held=$('#heldCandidates'); held.replaceChildren();
  state.data.candidates.filter(c=>!c.eligibility?.eligible).forEach(c=>{held.append(el('b',c.name),el('p',(c.eligibility?.reasons || []).join(', ')));});
  if (!held.children.length) held.append(el('p','현재 입력된 조건에서는 보류된 후보가 없습니다. 현장 안전 확인은 별도입니다.'));
  const missing=(activePlan()?.assignments || []).filter(a=>!a.candidate_id);
  $('#unassignedNote').textContent=missing.length ? '미배정: '+missing.map(a=>a.building_id+' ('+a.reason+')').join(', ') : '현재 입력과 선택안에서는 모든 건물이 제안 배정되었습니다.';
}
function renderSources() {
  const list=$('#sourceList');list.replaceChildren();
  state.data.sources.forEach(s=>{const row=el('article');row.append(s.url?safeLink(s.url,s.title):el('b',s.title),el('p',s.note || ''),el('small','자료 기준일: '+(s.reference_date || '개별 자료 확인 필요')));list.append(row);});
}
// 외부 배경이 없어도 동일한 위경도와 배정 관계를 도식으로 표시합니다.
function svgNode(tag, attrs, text) {
  const n=document.createElementNS('http://www.w3.org/2000/svg',tag);
  Object.entries(attrs || {}).forEach(([k,v])=>n.setAttribute(k,String(v)));
  if(text!=null)n.textContent=text;return n;
}
function fallbackPosition(p) {
  const bounds=state.data.study_area?.bounds || [[37.517,126.865],[37.525,126.877]];
  return {x:30+(p.lon-bounds[0][1])/(bounds[1][1]-bounds[0][1])*820,y:460-(p.lat-bounds[0][0])/(bounds[1][0]-bounds[0][0])*430};
}
function validPosition(p) {return p && Number.isFinite(p.lat) && Number.isFinite(p.lon);}
function straightDistance(a,b) {
  const rad=v=>v*Math.PI/180;
  const dlat=rad(b.lat-a.lat),dlon=rad(b.lon-a.lon);
  const h=Math.sin(dlat/2)**2+Math.cos(rad(a.lat))*Math.cos(rad(b.lat))*Math.sin(dlon/2)**2;
  return 6371000*2*Math.atan2(Math.sqrt(h),Math.sqrt(Math.max(0,1-h)));
}
function displayDistance(m){return m>=1000?fmt(m/1000,'km'):fmt(Math.round(m),'m');}
function renderNearby() {
  const list=$('#nearbyList');list.replaceChildren();
  $('#clearLocation').disabled=!state.position&&!state.locating;
  if(!state.position){$('#nearbySummary').textContent='내 위치를 확인하거나, 선택한 시연 건물을 기준으로 살펴보세요.';return;}
  const ids=new Set((activePlan()?.loads || []).map(c=>c.candidate_id));
  const nearby=state.data.candidates.filter(c=>c.eligibility?.eligible&&validPosition(c)&&ids.has(c.candidate_id))
    .map(c=>({candidate:c,distance:straightDistance(state.position,c)})).sort((a,b)=>a.distance-b.distance);
  const bounds=state.data.study_area?.bounds;
  const outside=bounds&&(state.position.lat<bounds[0][0]||state.position.lat>bounds[1][0]||state.position.lon<bounds[0][1]||state.position.lon>bounds[1][1]);
  $('#nearbySummary').textContent=(state.position.kind==='device'?'현재 위치':'선택한 건물의 시연 위치')+' 기준 · '+state.plan+'안 후보 '+nearby.length+'곳'+(outside?' · 분석 권역 밖입니다. 현재 등록된 시연 후보까지의 거리만 표시합니다.':' · 실제 운영 장소로 확정되지 않았습니다.');
  if(!nearby.length){list.append(el('p','선택안에 안내할 수 있는 후보가 없습니다. 배치안과 검토 조건을 확인해 주세요.'));return;}
  nearby.forEach(({candidate:c,distance},index)=>{
    const card=el('button',null,'nearby-card');card.type='button';
    card.append(el('span',String(index+1).padStart(2,'0'),'nearby-rank'),el('strong',c.name),el('b',displayDistance(distance),'nearby-distance'),el('small',(c.is_demo?'가상 후보':'제안 후보')+' · 직선거리 · 지도에서 보기'));
    card.addEventListener('click',()=>{chooseCandidate(c.candidate_id);go('home');if(state.map)state.map.setView([c.lat,c.lon],17);$('#candidateHeading').scrollIntoView({behavior:'smooth',block:'nearest'});});list.append(card);
  });
}
function renderPosition() {
  if(!state.map||!state.locationLayer)return;
  state.locationLayer.clearLayers();if(!state.position)return;
  const p=state.position;
  if(p.kind==='device'&&Number.isFinite(p.accuracy))L.circle([p.lat,p.lon],{radius:p.accuracy,color:'#347bc1',weight:1,fillOpacity:.08,interactive:false}).addTo(state.locationLayer);
  L.circleMarker([p.lat,p.lon],{radius:8,color:'#fff',weight:3,fillColor:p.kind==='device'?'#2879c6':'#d37b35',fillOpacity:1}).addTo(state.locationLayer).bindTooltip(el('span',p.kind==='device'?'내 위치':'시연 건물 기준점'));
}
function usePosition(point){
  state.position=point;renderPosition();renderNearby();
  if(state.map)state.map.setView([point.lat,point.lon],16);
}
$('#locateMe').addEventListener('click',()=>{
  if(state.locating)return;
  if(!window.isSecureContext||!navigator.geolocation){$('#locationStatus').textContent='이 환경에서는 위치 확인을 사용할 수 없습니다. HTTPS 또는 localhost에서 열거나 선택 건물로 시연해 주세요.';return;}
  const seq=++state.locationSeq;state.locating=true;$('#locateMe').disabled=true;$('#clearLocation').disabled=false;
  $('#locationStatus').textContent='브라우저 위치 권한을 확인하고 있습니다…';
  navigator.geolocation.getCurrentPosition(result=>{
    if(seq!==state.locationSeq)return;
    state.locating=false;$('#locateMe').disabled=false;
    const {latitude:lat,longitude:lon,accuracy}=result.coords;
    if(!validPosition({lat,lon})){renderNearby();$('#locationStatus').textContent='위치 정보를 읽지 못했습니다. 다시 시도해 주세요.';return;}
    usePosition({lat,lon,accuracy,kind:'device'});
    $('#locationStatus').textContent='내 위치 확인 · 오차 약 '+displayDistance(accuracy)+' · 이 페이지에서만 사용하며 서버에 저장하지 않습니다.';
  },error=>{
    if(seq!==state.locationSeq)return;
    state.locating=false;$('#locateMe').disabled=false;renderNearby();
    $('#locationStatus').textContent=({1:'위치 권한이 허용되지 않았습니다. 브라우저 설정에서 허용하거나 선택 건물로 시연해 주세요.',2:'현재 위치를 확인할 수 없습니다. 선택 건물로 시연하거나 다시 시도해 주세요.',3:'위치 확인 시간이 초과되었습니다. 다시 시도해 주세요.'})[error.code]||'위치를 확인하지 못했습니다.';
  },{enableHighAccuracy:true,timeout:12000,maximumAge:30000});
});
function cancelLocationRequest(){state.locationSeq++;state.locating=false;$('#locateMe').disabled=false;}
$('#useBuildingLocation').addEventListener('click',()=>{
  const b=state.data.buildings.find(b=>b.building_id===state.building);
  if(!validPosition(b)){notify('좌표가 있는 건물을 먼저 선택해 주세요.');return;}
  cancelLocationRequest();usePosition({lat:b.lat,lon:b.lon,kind:'building'});
  $('#locationStatus').textContent=b.building_name+' 기준 시연입니다. 실제 내 위치가 아닙니다.';
});
$('#clearLocation').addEventListener('click',()=>{
  cancelLocationRequest();state.position=null;renderPosition();renderNearby();fitMap();
  $('#locationStatus').textContent='위치 정보를 지웠습니다. 필요할 때 내 위치를 다시 확인하세요.';
});
function renderFallback() {
  const svg=$('#fallbackMap');svg.replaceChildren();
  svg.append(svgNode('rect',{width:880,height:490,fill:'#f3f7f1'}));
  for(let x=40;x<880;x+=60)svg.append(svgNode('line',{x1:x,y1:0,x2:x,y2:490,stroke:'#e1e8dd'}));
  for(let y=40;y<490;y+=60)svg.append(svgNode('line',{x1:0,y1:y,x2:880,y2:y,stroke:'#e1e8dd'}));
  if($('#showAssignments').checked)(activePlan()?.assignments || []).forEach(a=>{
    const b=state.data.buildings.find(b=>b.building_id===a.building_id),c=candidateFor(a.candidate_id);
    if(!validPosition(b)||!validPosition(c))return;
    const p=fallbackPosition(b),q=fallbackPosition(c);
    svg.append(svgNode('line',{x1:p.x,y1:p.y,x2:q.x,y2:q.y,stroke:state.candidate===c.candidate_id?'#568a72':'#b5c9bd','stroke-width':1.3,'stroke-dasharray':'5 4'}));
  });
  state.data.buildings.filter(validPosition).forEach(b=>{
    const p=fallbackPosition(b),dot=svgNode('circle',{cx:p.x,cy:p.y,r:state.building===b.building_id?7:4.5,fill:state.building===b.building_id?'#e58c4a':'#7587a2',tabindex:0,role:'button','aria-label':b.building_name+' 선택'});
    dot.append(svgNode('title',{},b.building_name));dot.addEventListener('click',()=>pickBuilding(b.building_id,true));dot.addEventListener('keydown',e=>{if(e.key==='Enter')pickBuilding(b.building_id,true);});svg.append(dot);
  });
  state.data.candidates.filter(validPosition).forEach(c=>{
    const p=fallbackPosition(c),group=svgNode('g',{tabindex:0,role:'button','aria-label':c.name});
    group.append(svgNode('circle',{cx:p.x,cy:p.y,r:state.candidate===c.candidate_id?14:11,fill:c.eligibility?.eligible?'#157859':'#b58b5b',stroke:'#fff','stroke-width':3}),svgNode('text',{x:p.x+17,y:p.y+5,fill:'#274a3f','font-size':14,'font-weight':700},c.candidate_id));
    group.addEventListener('click',()=>chooseCandidate(c.candidate_id));group.addEventListener('keydown',e=>{if(e.key==='Enter')chooseCandidate(c.candidate_id);});svg.append(group);
  });
  svg.append(svgNode('text',{x:22,y:478,fill:'#61736a','font-size':12},'위경도 상대 위치 도식 · 실제 도로와 경로를 표시하지 않습니다'));
}
function renderMap() {
  if(!state.map || !window.L){renderFallback();return;}
  state.layer.clearLayers();
  if($('#showAssignments').checked)(activePlan()?.assignments || []).forEach(a=>{
    const b=state.data.buildings.find(b=>b.building_id===a.building_id),c=candidateFor(a.candidate_id);
    if(validPosition(b)&&validPosition(c))L.polyline([[b.lat,b.lon],[c.lat,c.lon]],{color:state.candidate===c.candidate_id?'#568a72':'#a8bfb2',weight:1.4,dashArray:'4 5',opacity:.7}).addTo(state.layer);
  });
  state.data.buildings.filter(validPosition).forEach(b=>{
    L.circleMarker([b.lat,b.lon],{radius:state.building===b.building_id?7:4,color:'#fff',weight:1.5,fillColor:state.building===b.building_id?'#e58c4a':'#7287a8',fillOpacity:1}).addTo(state.layer).bindTooltip(el('span',b.building_name)).on('click',()=>pickBuilding(b.building_id,true));
  });
  state.data.candidates.filter(validPosition).forEach(c=>{
    L.circleMarker([c.lat,c.lon],{radius:state.candidate===c.candidate_id?13:10,color:'#fff',weight:3,fillColor:c.eligibility?.eligible?'#157859':'#b58b5b',fillOpacity:1}).addTo(state.layer).bindTooltip(el('span',c.candidate_id+' · '+c.name)).on('click',()=>chooseCandidate(c.candidate_id));
  });
}
function fitMap() {if(state.map&&state.data.study_area?.bounds)state.map.fitBounds(state.data.study_area.bounds,{padding:[22,22]});}
$('#fitMap').addEventListener('click',fitMap);$('#showAssignments').addEventListener('change',renderMap);
function loadMapLibrary() {
  const link=document.createElement('link');link.rel='stylesheet';link.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';link.integrity='sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';link.crossOrigin='';document.head.append(link);
  const script=document.createElement('script');script.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';script.integrity='sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';script.crossOrigin='';
  script.onerror=()=>{$('#mapState').textContent='좌표 도식 · 배경 미연결';$('#mapNote').textContent='실제 지도 확대·이동은 지도 연결이 필요합니다. 아래 목록은 계속 사용할 수 있습니다.';};
  script.onload=()=>{
    if(!window.L)return;
    $('#fallbackMap').classList.add('hidden');
    state.map=L.map('map',{scrollWheelZoom:true,touchZoom:true,keyboard:true}).setView(state.data.study_area?.center || [37.521,126.871],15);
    state.layer=L.layerGroup().addTo(state.map);
    state.locationLayer=L.layerGroup().addTo(state.map);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',updateWhenIdle:true}).on('tileerror',()=>{$('#mapState').textContent='좌표 지도 · 배경 미연결';}).on('load',()=>{$('#mapState').textContent='Leaflet · OSM';}).addTo(state.map);
    fitMap();renderMap();renderPosition();
    if(state.position)state.map.setView([state.position.lat,state.position.lon],16);
    if(state.page!=='home')setTimeout(()=>state.map.invalidateSize(),0);
  };
  document.head.append(script);
}
function searchItems() {
  const q=$('#buildingSearch').value.trim().toLowerCase();
  return state.data.buildings.filter(b=>(b.building_id+' '+b.building_name+' '+b.road_address).toLowerCase().includes(q));
}
function rebuildSelect() {
  const items=searchItems(),select=$('#buildingSelect');select.replaceChildren();
  if(!items.length){
    const option=el('option','일치하는 건물이 없습니다');option.value='';select.append(option);
    state.building=null;$('#buildingContext').textContent='검색 결과 없음';invalidateMatch('검색 조건에 맞는 건물이 없습니다.');renderMap();return;
  }
  items.forEach(b=>{const op=el('option',b.building_id+' · '+b.building_name);op.value=b.building_id;select.append(op);});
  if(!items.some(b=>b.building_id===state.building))state.building=items[0].building_id;
  pickBuilding(state.building);
}
function pickBuilding(id,fromMap) {
  const building=state.data.buildings.find(b=>b.building_id===id);if(!building)return;
  if(fromMap){$('#buildingSearch').value='';state.building=id;rebuildSelect();return;}
  state.building=id;$('#buildingSelect').value=id;
  $('#buildingContext').textContent=building.road_address+' · '+(building.is_demo?'가상 자료':'자료 기반 건물');
  const a=assignmentFor(id);if(a?.candidate_id)state.candidate=a.candidate_id;
  invalidateMatch('선택한 건물의 안내를 확인하세요.');renderCandidate();renderMap();
}
$('#buildingSearch').addEventListener('input',rebuildSelect);
$('#buildingSelect').addEventListener('change',e=>pickBuilding(e.target.value));
$('#categorySelect').addEventListener('change',()=>invalidateMatch('품목이 바뀌었습니다. 안내를 다시 확인해 주세요.'));
$('#quantity').addEventListener('input',()=>invalidateMatch('수량이 바뀌었습니다. 안내를 다시 확인해 주세요.'));
async function showMatch() {
  const building=searchItems().find(b=>b.building_id===state.building);
  if(!building){invalidateMatch('조회할 건물을 먼저 선택해 주세요.');return;}
  const quantity=Number($('#quantity').value),category=$('#categorySelect').value;
  if(!Number.isInteger(quantity)||quantity<1||quantity>99){notify('수량은 1~99 사이 정수로 입력해 주세요.');return;}
  const stamp=fingerprint(),seq=++state.matchSeq;
  state.lastResult=null;$('#requestButton').disabled=true;$('#matchButton').disabled=true;
  const payload={building_id:building.building_id,category,quantity,plan_id:state.plan};
  const rule=state.data.rules.find(r=>r.category===category),a=assignmentFor(building.building_id);
  let result={guidance:rule?.guidance || '안내 자료 확인 필요',rule,proposed_candidate:candidateFor(a?.candidate_id),assignment:a};
  try {
    if(state.apiReady){
      if(state.matchAbort)state.matchAbort.abort();
      const controller=new AbortController();state.matchAbort=controller;
      const timer=setTimeout(()=>controller.abort(),10000);
      try{
        const response=await fetch('/api/match',{...jsonOptions('POST',payload),signal:controller.signal});
        if(!response.ok)throw new Error('조회 실패 ('+response.status+')');
        result=await response.json();
      }finally{clearTimeout(timer);}
    }
    if(seq!==state.matchSeq||stamp!==fingerprint())return;
    const box=$('#matchResult');box.replaceChildren();
    box.append(el('div',state.apiReady?'저장된 자료 조회':'독립 시연 자료','result-label'),el('div',building.building_name+' / '+labels[category],'result-title'));
    box.append(el('p',result.proposed_candidate?'배치 제안: '+result.proposed_candidate.name:'현재 배치안에서 미배정'));
    if(result.assignment?.distance_m!=null)box.append(el('p','직선거리 참고: '+fmt(result.assignment.distance_m,'m')));
    box.append(el('p',result.guidance));
    if(result.rule){
      box.append(el('p','요일: '+(result.rule.days || '공식 확인 필요')+' / 시간: '+(result.rule.time_text || '공식 확인 필요')));
      box.append(el('p','규칙 상태: '+(result.rule.is_demo?'시연 자료':'자료 확인 필요')+' · 기준일 '+(result.rule.reference_date || '미확인'),'warning'));
      if(result.rule.source_url)box.append(safeLink(result.rule.source_url,'안내 원문 보기'));
    }
    box.append(el('p','제안 후보는 실제 배출 가능한 장소로 확정되지 않았습니다.','warning'));
    state.lastResult={...payload,building_name:building.building_name,stamp};
    $('#requestButton').disabled=false;notify('');
  }catch(error){
    if(error.name!=='AbortError'&&seq===state.matchSeq)notify(error.message);
  }finally{if(seq===state.matchSeq)$('#matchButton').disabled=!state.building;}
}
$('#matchButton').addEventListener('click',showMatch);
function saveSessionRequests() {try{sessionStorage.setItem('preview_requests',JSON.stringify(state.requests));}catch{}}
async function refreshRequests() {
  try{
    if(state.apiReady){
      const rows=await api('/api/requests');
      state.requests=rows.map(r=>({id:r.request_id,building_name:state.data.buildings.find(b=>b.building_id===r.building_id)?.building_name || r.building_id,category:r.category,quantity:r.quantity,status:'시연 접수(DB)'}));
    }
    state.requestsError='';
  }catch(error){
    state.requestsError='요청 목록을 불러오지 못했습니다. '+error.message;renderRequests();throw error;
  }
  $('#countRequests').textContent=state.requests.length;renderRequests();
}
function renderRequests(){ $('#countRequests').textContent=state.requests.length; }
$('#requestButton').addEventListener('click',async()=>{
  if(state.requestBusy||!state.lastResult||state.lastResult.stamp!==fingerprint())return;
  const result={...state.lastResult};state.requestBusy=true;$('#requestButton').disabled=true;
  try{
    if(state.apiReady){await api('/api/requests',jsonOptions('POST',{building_id:result.building_id,category:result.category,quantity:result.quantity,plan_id:result.plan_id}));await refreshRequests();}
    else{state.requests.push({id:Date.now(),building_name:result.building_name,category:result.category,quantity:result.quantity,status:'독립 시연 접수'});saveSessionRequests();await refreshRequests();}
    if(result.stamp===fingerprint())$('#requestButton').textContent='데모 요청 등록됨';
  }catch(e){notify(e.message);if(result.stamp===fingerprint())$('#requestButton').disabled=false;}
  finally{state.requestBusy=false;}
});
function localReply(message) {
  const category=/건전지|배터리|폐전지/.test(message)?'battery':/의자|책상|소파|침대|가구|대형폐기물/.test(message)?'bulky':/재활용|분리수거|플라스틱|페트병|캔|종이/.test(message)?'recycle':/쓰레기|종량제|생활폐기물|배출|버리/.test(message)?'general':null;
  if(!category)return '품목을 판별하지 못했습니다. 일반쓰레기, 재활용품, 폐건전지, 대형폐기물 중 무엇인지 알려주세요.';
  const rule=state.data.rules.find(r=>r.category===category);
  let response=rule?.guidance || '공식 안내 확인이 필요합니다.';
  if(/언제|요일|시간|몇 시/.test(message))response+='\n요일: '+(rule?.days || '공식 확인 필요')+' / 시간: '+(rule?.time_text || '공식 확인 필요');
  if(/어디|위치|장소|수거함/.test(message))response+='\n현재 지도는 제안 후보입니다. 실제 배출 장소로 확정하지 않습니다.';
  return response+'\n[독립 시연 · LLM 미사용]';
}
async function sendChat(message) {
  if(state.chatBusy||!message.trim()||message.length>500)return;
  state.chatBusy=true;const target=$('#chatMessages');
  target.append(el('div',message,'bubble user'));const bubble=el('div','안내를 조회하고 있습니다.','bubble bot');target.append(bubble);
  $$('#chatForm button,.quick-prompts button').forEach(b=>b.disabled=true);
  try{
    if(state.apiReady){
      const data=await api('/api/chat',{...jsonOptions('POST',{message,building_id:state.building}),timeoutMs:140000});
      bubble.textContent=data.response+'\n\n['+(data.ai_used?'AI 분류 + 저장된 규칙':'규칙 기반 안내 · LLM 미사용')+']';
    }else bubble.textContent=localReply(message);
  }catch(e){bubble.textContent='안내 연결 오류: '+e.message;}
  finally{state.chatBusy=false;$$('#chatForm button,.quick-prompts button').forEach(b=>b.disabled=false);target.scrollTop=target.scrollHeight;}
}
$('#chatForm').addEventListener('submit',e=>{e.preventDefault();const input=$('#chatInput');const message=input.value.trim();if(message&&!state.chatBusy){input.value='';sendChat(message);}});
$$('[data-prompt]').forEach(b=>b.addEventListener('click',()=>sendChat(b.dataset.prompt)));
$('#exportAnalysis').addEventListener('click',()=>{
  const blob=new Blob([JSON.stringify(state.data.analysis,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='greenzone-analysis.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
async function initialize() {
  try{const data=JSON.parse(sessionStorage.getItem('preview_requests') || '[]');if(Array.isArray(data))state.requests=data;}catch{}
  renderOverview();rebuildSelect();renderRequests();$('#countRequests').textContent=state.requests.length;
  go(location.hash.slice(1) || 'home',false);loadMapLibrary();
  if(location.protocol==='file:'){$('#apiState').textContent='독립 시연 · 서버 미연결';return;}
  try{
    const [catalog,config]=await Promise.all([api('/api/catalog'),api('/api/config')]);
    state.data=catalog;state.apiReady=true;
    $('#apiState').textContent='FastAPI + SQLite 연결';$('#aiStatus').textContent=config.ai_enabled?'AI 분류 선택 기능 사용':'규칙 기반 안내 · AI 꺼짐';
    state.requests=[];renderOverview();rebuildSelect();
    await refreshRequests().catch(error=>notify(error.message));
    if(state.position&&state.map)state.map.setView([state.position.lat,state.position.lon],16);else fitMap();
  }catch(error){state.apiReady=false;$('#apiState').textContent='독립 시연 · 서버 미연결';notify('서버 연결이 없어 저장된 시연 자료를 보여 줍니다. 수정·서버 저장은 사용할 수 없습니다.');}
}
initialize();
