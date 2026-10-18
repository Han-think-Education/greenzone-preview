 'use strict';
const state={pilot:null,apiReady:false,chatBusy:false,chatContext:null,map:null,layer:null,locationLayer:null,position:null,locationSeq:0,locating:false,page:'home',area:'compare',selectedReference:null};
state.basemap='street';state.mapConfig=null;state.basemapLayers=null;state.imageryLoaded=0;state.imageryErrors=0;
const initialBasemap=new URLSearchParams(location.search).get('basemap');
const sectorNames={residential:'주거',commercial:'상가·업무·숙박',education:'교육',medical_care:'의료·돌봄',community:'지역 시설',special:'특수·산업 시설'};
function sectorText(counts){return Object.entries(counts||{}).map(([k,v])=>(sectorNames[k]||k)+' '+fmt(v)).join(' / ');}
function buildingColor(p){if(p.has_apartment)return '#bf6262';if(p.classification==='context')return '#8159a4';if(p.sectors?.includes('commercial'))return '#287ba7';return p.classification==='target'?'#187b60':'#87929b';}
const areaNames={compare:'두 지역 함께',sinwol:'신월1동',hwagok:'화곡1동'};
const requested=new URLSearchParams(location.search).get('area');
if(Object.hasOwn(areaNames,requested))state.area=requested;
function areas(){return state.pilot?Object.entries(state.pilot.areas).filter(([id])=>state.area==='compare'||state.area===id).map(([,a])=>a):[];}
function go(page,hash=true){
  if(!['home','analysis','assistant','architecture'].includes(page))page='home';
  state.page=page;['home','analysis','assistant','architecture'].forEach(p=>$('#'+p+'Page').classList.toggle('hidden',p!==page));
  $$('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
  $('#crumb').textContent={home:'실제 자료 지도',analysis:'두 지역 분석',assistant:'해우리 배출도우미',architecture:'분석 과정'}[page];
  if(hash)location.hash=page;
  if(page==='home'&&state.map)setTimeout(()=>state.map.invalidateSize(),0);
}
$$('[data-page]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.page)));
$$('[data-go]').forEach(b=>b.addEventListener('click',e=>{e.preventDefault();go(b.dataset.go);}));
window.addEventListener('hashchange',()=>go(location.hash.slice(1),false));
function selectArea(id){
  if(!Object.hasOwn(areaNames,id))return;
  state.area=id;state.selectedReference=null;state.focusedBuilding=null;
  $('#homeMatch').replaceChildren();$('#homeMatch').classList.add('hidden');
  const url=new URL(location.href);url.searchParams.set('area',id);history.replaceState(null,'',url);
  renderOverview();renderMap();fitMap();renderBuildingSearch();
}
$('#areaButtons').addEventListener('click',e=>{const b=e.target.closest('[data-area]');if(b)selectArea(b.dataset.area);});
function renderOverview(){
  if(!state.pilot)return;
  const rows=areas().map(a=>a.summary),sum=k=>rows.reduce((n,r)=>n+r[k],0);
  $('#countBuildings').textContent=fmt(sum('target_parcels'));
  $('#countApartments').textContent=fmt(sum('excluded_apartment_parcels'));
  $('#countReferences').textContent=fmt(sum('survey_reference_count'));
  $('#countAreas').textContent=fmt(rows.length);
  $('#areaName').textContent=rows.map(r=>r.name).join(' · ')+' / 동 전체 권역·도로 이동 시나리오';
  $$('#areaButtons button').forEach(b=>{b.classList.toggle('selected',b.dataset.area===state.area);b.setAttribute('aria-pressed',String(b.dataset.area===state.area));});
  $('#candidateChoices').replaceChildren();
  areas().forEach(a=>[...a.survey_references].sort((p,q)=>p.visit_order-q.visit_order).forEach(p=>{const b=el('button',a.summary.name+' 방문 '+p.visit_order+' / '+p.sector_number+'권역','candidate-choice');b.style.borderColor=p.color;b.addEventListener('click',()=>showReference(p));$('#candidateChoices').append(b);}));
  const routes=$('#routeSummary');routes.replaceChildren();areas().forEach(a=>{
    const r=a.collection_route,s=a.summary,card=el('article');
    card.append(el('strong',s.name+' · '+s.survey_reference_count+'권역 / 내부 이동 '+fmt(Math.round(r.distance_m),'m')),
      el('p','방문 순서: '+r.order.map(id=>a.survey_references.find(p=>p.reference_id===id)?.sector_number+'권역').join(' → ')),
      el('small','동일 거점 북→남 순 '+fmt(Math.round(r.baseline_north_to_south_distance_m),'m')+' 대비 '+r.ordering_reduction_pct+'% 짧은 순서 · 차고지·처리장 제외'));
    routes.append(card);
  });
  renderReferenceEmpty();renderComparison();renderNearby();
}
function renderReferenceEmpty(){
  const box=$('#candidateDetail');box.replaceChildren();
  box.append(el('div','실제 자료 기반 · 현장 확인 전','detail-kicker'),el('h3','주황색 조사 기준점을 눌러보세요'));
  box.append(el('p','동 전체를 6개 조사 권역으로 나누고 점 사이 최소 250m를 두었습니다. 색칠한 권역이나 번호를 누르면 담당 필지와 방문 순서를 볼 수 있습니다. 갈색 점은 수거차가 거쳐 갈 조사 기준점입니다.','candidate-reason'));
  box.append(el('p','점선은 공식 도로 선형으로 계산한 이동 시나리오입니다. 양방향 평면 연결을 가정하며 실제 일방통행·차량 진입 조건은 확인 전입니다.','detail-note'));
  box.append(el('p','이 점은 현장에서 도로변 공간을 확인할 기준입니다. 도로 중앙에 쓰레기를 배출하거나 차량을 정차하라는 뜻이 아닙니다.','detail-note'));
}
function showReference(p){
  state.selectedReference=p.reference_id;state.focusedBuilding=null;
  $('#homeMatch').replaceChildren();$('#homeMatch').classList.add('hidden');
  const box=$('#candidateDetail');box.replaceChildren();box.append(el('div','현장 조사 기준점 · 배출 금지','detail-kicker'),el('h3',p.name));
  box.append(el('p','방문 '+p.visit_order+'번째 / '+p.sector_number+'권역\n권역 조사 대상: '+p.nearby_target_parcels+'필지\n기준 도로: '+p.road_name,'candidate-reason'));
  box.append(el('p','도로 접근 대용거리 평균 '+p.approach_mean_m+'m / 90백분위 '+p.approach_p90_m+'m. 실제 보행망 거리는 아닙니다.','detail-meta'));
  box.append(el('p',p.safety_note,'detail-note'));
  box.append(el('p','주변 '+p.context_radius_m+'m 용도(중복 집계): '+sectorText(p.nearby_sector_counts),'detail-meta'),el('p',p.context_review,'detail-meta'));
  const tags=el('div',null,'safety-tags');['차량 진입','정차·작업면','보행 통로','부지·관리 동의'].forEach(t=>tags.append(el('span',t+' 미확인','safety-tag unknown')));box.append(tags);
  box.append(el('p','건축물대장·SGIS 경계·VWorld 건물 및 도로 자료 / 취득 2026-10-18','detail-meta'));
  renderMap();
}
function showBuilding(p){
  const a=state.pilot.areas[p.area_id];
  const assignment=a?.survey_assignments.find(r=>r.building_id===p.building_id);
  const reference=assignment&&a.survey_references.find(r=>r.reference_id===assignment.reference_id);
  state.focusedBuilding=p.building_id;state.selectedReference=reference?.reference_id||null;
  const box=$('#candidateDetail');box.replaceChildren();box.append(el('div','공식 도형·대장 조인 / 배출 위치 아님','detail-kicker'),el('h3',p.address));
  const role=p.classification==='target'?'비아파트 주거·상가의 수요 조사 대상입니다. 실제 이용·배출량·위탁계약을 확인하기 전입니다.':p.classification==='excluded_apartment'?'아파트 주거 수요는 자체 관리 확인 대상으로 배정에서 제외합니다.':p.classification==='context'?'교육·의료·기타 시설 또는 아파트 복합용도입니다. 주변 동선·관리 맥락에 포함하며 공공 거점 참여는 별도 확인합니다.':'대장 미연결·용도 분류 보류 필지입니다.';
  box.append(el('p',p.housing_use,'candidate-reason'),el('p',(p.sectors||[]).map(k=>sectorNames[k]).join(' · ')+(p.mixed_use?' / 복합용도':''),'detail-meta'),el('p',role,'detail-note'));
  if(p.building_names?.length)box.append(el('p',p.building_names.join(' / '),'detail-meta'));
  renderHomeMatch(p,a,assignment,reference);
  if(reference){
    box.append(el('h3','이 주소의 담당 제안: '+reference.sector_number+'권역'),
      el('p',reference.name+' · 수거차 방문 순서 '+reference.visit_order+'번째','candidate-reason'),
      el('p','직선 약 '+fmt(Math.round(assignment.straight_distance_m),'m')+' / 도로 접근 대용거리 약 '+fmt(Math.round(assignment.road_proxy_distance_m),'m')+'. 실제 보행 경로·소요시간이 아닙니다.','detail-meta'),
      el('p','이미 계산한 필지별 권역 배정을 조회했습니다. 단순히 가장 가까운 점으로 새로 배정하지 않습니다. 제안 조사점은 운영 배출장소가 아니며 배출 시간·허용 품목도 아직 확정되지 않았습니다.','detail-note'));
  }
  box.append(el('p','1필지 안에 건물 도형 '+p.footprint_count+'개 / 연결 대장 '+p.title_record_count+'건. 필지 수는 가구 수나 쓰레기량이 아닙니다.','detail-meta'),el('p',p.management_status,'detail-meta'));
  renderMap();
}
function renderHomeMatch(p,a,assignment,reference){
  const box=$('#homeMatch');box.replaceChildren();box.classList.remove('hidden');
  box.append(el('strong',(p.building_names?.join(' / ')||'선택한 건물')+' · '+p.address));
  if(reference){
    box.append(el('p',(a?.summary.name||'')+' '+reference.sector_number+'권역 제안 · 방문 '+reference.visit_order+'번째 · 직선 약 '+fmt(Math.round(assignment.straight_distance_m),'m')),
      el('small','파란 집 표시 → 테두리가 강조된 조사점. 연결선은 위치 비교용 직선이며 실제 보행 경로가 아닙니다. 운영 배출장소는 아직 미확정입니다.'));
  }else{
    const reason=p.classification==='excluded_apartment'?'아파트 주거는 자체 관리 대상으로 제안 배정에서 제외했습니다.':p.classification==='context'?'학교·사업장 등 별도 참여 검토 대상입니다.':p.classification==='held'?'용도·대장 연결 확인이 필요한 필지입니다.':'도로 접근 분석의 배정 결과가 없는 필지입니다.';
    box.append(el('p','담당 제안 권역 없음 · '+reason),el('small','가까운 점을 임의로 배출장소로 지정하지 않습니다.'));
  }
  const clear=el('button','선택 해제','minor');clear.type='button';clear.addEventListener('click',()=>{state.focusedBuilding=null;state.selectedReference=null;box.replaceChildren();box.classList.add('hidden');renderReferenceEmpty();renderMap();renderBuildingSearch();});box.append(clear);
}
function focusBuilding(p){
  if(state.area!=='compare'&&state.area!==p.area_id)selectArea(p.area_id);
  showBuilding(p);
  $('#buildingSearch').value='';$('#buildingResults').replaceChildren();$('#buildingSearchStatus').textContent='선택한 주소를 지도에 표시했어요. 다른 주소도 새로 검색할 수 있습니다.';
  if(!state.map)return;
  const a=state.pilot.areas[p.area_id],r=a.survey_assignments.find(r=>r.building_id===p.building_id),ref=r&&a.survey_references.find(v=>v.reference_id===r.reference_id);
  if(ref)state.map.fitBounds([[p.lat,p.lon],[ref.lat,ref.lon]],{padding:[65,65],maxZoom:18});
  else state.map.setView([p.lat,p.lon],18);
}
function renderComparison(){
  const target=$('#comparisonCards');target.replaceChildren();
  Object.entries(state.pilot.areas).forEach(([id,a])=>{
    const s=a.summary,card=el('article',null,'plan-card');card.append(el('div','공식 자료 공간 분석','eyebrow'),el('h2',s.name));
    const dl=el('dl',null,'plan-stats');
    [['경계 면적',s.boundary_area_km2+'㎢'],['분석 지도 필지',fmt(s.mapped_parcels,'필지')],['대장 연결률',s.title_link_rate_pct+'%'],['주거·상가 수요 조사 대상',fmt(s.target_parcels,'필지')],['아파트 주거 배정 제외',fmt(s.excluded_apartment_parcels,'필지')],['주변 맥락·참여 검토',fmt(s.context_parcels,'필지')],['용도별 집계(중복)',sectorText(s.sector_counts)],['최소 점 간격(이전)',s.previous_reference_min_spacing_m+'m'],['최소 점 간격(현재)',s.reference_min_spacing_m+'m'],['조사 권역',s.survey_reference_count+'개'],['도로 모델 미배정',s.unassigned_survey_parcels+'필지'],['권역당 조사 대상',s.sector_parcel_min+'~'+s.sector_parcel_max+'필지'],['도로 접근 대용거리 평균',s.road_proxy_mean_m+'m'],['도로 접근 대용거리 90백분위',s.road_proxy_p90_m+'m'],['동일 거점 북→남 순 내부 이동',fmt(Math.round(s.baseline_route_distance_m),'m')],['최소 순서 내부 이동',fmt(Math.round(s.internal_route_distance_m),'m')],['순서 변경에 따른 거리 차이',s.ordering_reduction_pct+'%']].forEach(([k,v])=>dl.append(el('dt',k),el('dd',v)));
    const b=el('button','이 지역 지도 보기','ghost');b.addEventListener('click',()=>{selectArea(id);go('home');});card.append(dl,b);target.append(card);
  });
  $('#analysisMethod').textContent=state.pilot.method;
  const limits=$('#analysisLimits');limits.replaceChildren();state.pilot.limitations.forEach(t=>limits.append(el('li',t)));
  const list=$('#sourceList');list.replaceChildren();state.pilot.sources.forEach(s=>{const row=el('article');row.append(safeLink(s.url,s.title),el('p',s.note),el('small','원본 기준: '+(s.reference_date||'발행일 미명시')+' / 취득 2026-10-18'));list.append(row);});
}
function renderMap(){
  if(!state.map||!state.pilot||!window.L)return;
  state.layer.clearLayers();
  areas().forEach(a=>{
    L.geoJSON(a.boundary,{style:{color:a.summary.area_id==='sinwol'?'#216eaa':'#85549d',weight:2,fillOpacity:.015}}).addTo(state.layer);
    if($('#showSectors').checked)L.geoJSON(a.service_sectors,{style:f=>({color:f.properties.color,weight:f.properties.reference_id===state.selectedReference?3:1.4,fillColor:f.properties.color,fillOpacity:f.properties.reference_id===state.selectedReference ? 0.23 : state.basemap==='street'?0.12:0.07}),onEachFeature:(f,l)=>{l.bindTooltip(el('span',f.properties.name+' · 제안 권역'));const p=a.survey_references.find(p=>p.reference_id===f.properties.reference_id);if(p)l.on('click',()=>showReference(p));}}).addTo(state.layer);
    if($('#showRoads').checked)L.geoJSON(a.roads,{style:{color:'#6d8592',weight:2,opacity:.5}}).addTo(state.layer);
    L.geoJSON(a.buildings,{
      filter:f=>f.properties.building_id===state.focusedBuilding||$('#showBuildings').checked&&(['target','context'].includes(f.properties.classification)||(f.properties.classification==='excluded_apartment'?$('#showApartments').checked:$('#showOther').checked)),
      pointToLayer:(f,ll)=>L.circleMarker(ll,{radius:f.properties.classification==='context'?4:3,color:'#fff',weight:.5,fillColor:buildingColor(f.properties),fillOpacity:.8}),
      onEachFeature:(f,l)=>l.bindTooltip(el('span',f.properties.address)).on('click',()=>showBuilding(f.properties))
    }).addTo(state.layer);
    if($('#showRoute').checked){
      L.geoJSON(a.collection_route.legs,{style:{color:'#fff',weight:7,opacity:.9},interactive:false}).addTo(state.layer);
      L.geoJSON(a.collection_route.legs,{style:{color:'#495b67',weight:3.5,dashArray:'7 6',opacity:.95},onEachFeature:(f,l)=>l.bindTooltip(el('span','방문 '+f.properties.from_visit+' → '+f.properties.to_visit+' / 도로 선형 '+fmt(Math.round(f.properties.distance_m),'m')+' / 연결 가정'))}).addTo(state.layer);
      a.collection_route.legs.features.forEach(f=>{const cs=f.geometry.coordinates,i=Math.max(1,Math.floor(cs.length/2)),p=cs[i],prev=cs[i-1];const arrow=el('span','➤','route-arrow');arrow.style.transform='rotate('+Math.atan2(-(p[1]-prev[1]),(p[0]-prev[0])*Math.cos(p[1]*Math.PI/180))*180/Math.PI+'deg)';L.marker([p[1],p[0]],{interactive:false,icon:L.divIcon({html:arrow,className:'route-arrow-icon',iconSize:[18,18],iconAnchor:[9,9]})}).addTo(state.layer);});
    }
    a.survey_references.forEach(p=>{const badge=el('span',String(p.visit_order),'route-stop-badge');badge.style.borderColor=p.color;L.marker([p.lat,p.lon],{icon:L.divIcon({html:badge,className:'route-stop-icon',iconSize:[30,30],iconAnchor:[15,15]})}).addTo(state.layer).bindTooltip(el('span',p.name+' / 방문 '+p.visit_order+' / 현장 확인 전')).on('click',()=>showReference(p));});
    if($('#showAssignments').checked){
      const ps=new Map(a.survey_references.map(p=>[p.reference_id,p]));const bs=new Map(a.buildings.features.map(f=>[f.properties.building_id,f.properties]));
      a.survey_assignments.forEach(r=>{const p=ps.get(r.reference_id),b=bs.get(r.building_id);if(p&&b)L.polyline([[b.lat,b.lon],[p.lat,p.lon]],{color:p.color,weight:1,opacity:.25,dashArray:'3 5',interactive:false}).addTo(state.layer);});
    }
    if($('#showHistorical').checked)L.geoJSON(a.historical,{pointToLayer:(f,ll)=>L.circleMarker(ll,{radius:7,color:'#49596d',weight:2,fillOpacity:.12}),onEachFeature:(f,l)=>l.bindTooltip(el('span',f.properties.text+' / '+f.properties.interval+' / '+f.properties.status))}).addTo(state.layer);
    const home=a.buildings.features.find(f=>f.properties.building_id===state.focusedBuilding)?.properties;
    if(home){
      const assignment=a.survey_assignments.find(r=>r.building_id===home.building_id),ref=assignment&&a.survey_references.find(p=>p.reference_id===assignment.reference_id);
      if(ref){
        L.polyline([[home.lat,home.lon],[ref.lat,ref.lon]],{color:'#226bc2',weight:3,dashArray:'3 7',interactive:false}).addTo(state.layer);
        L.circleMarker([ref.lat,ref.lon],{radius:22,color:'#226bc2',weight:3,fill:false,interactive:false}).addTo(state.layer);
      }
      const badge=el('span','집','home-pin-badge');
      L.marker([home.lat,home.lon],{zIndexOffset:800,icon:L.divIcon({html:badge,className:'home-pin-icon',iconSize:[30,34],iconAnchor:[15,34]})}).addTo(state.layer).bindTooltip(el('span',(home.building_names?.join(' / ')||'선택한 건물')+' · '+home.address));
    }
  });
}
function fitMap(){if(state.map&&state.pilot){const bounds=L.latLngBounds([]);areas().forEach(a=>bounds.extend(L.geoJSON(a.boundary).getBounds()));if(bounds.isValid())state.map.fitBounds(bounds,{padding:[20,20]});}}
$('#fitMap').addEventListener('click',fitMap);
['showSectors','showRoute','showBuildings','showApartments','showOther','showRoads','showAssignments','showHistorical'].forEach(id=>$('#'+id).addEventListener('change',renderMap));
function renderBuildingSearch(){
  const q=$('#buildingSearch').value.trim(),list=$('#buildingResults');list.replaceChildren();if(q.length<2||!state.pilot){$('#buildingSearchStatus').textContent='도로명주소·건물명·용도로 검색하세요. 위치 권한 없이 두 동의 수집 자료에서 찾습니다.';return;}
  const normalize=s=>String(s||'').normalize('NFKC').toLowerCase().replace(/[\s(),·]/g,'');
  const parts=q.split(/\s+/).filter(Boolean).map(normalize),compact=normalize(q);
  const rows=Object.values(state.pilot.areas).flatMap(a=>a.buildings.features).map(f=>{
    const p=f.properties,fields=[p.address,p.housing_use,...(p.building_names||[]),...(p.sectors||[]).map(k=>sectorNames[k])].map(normalize);
    const joined=fields.join('|');
    return {p,match:joined.includes(compact)||parts.every(t=>joined.includes(t)),rank:fields.some(t=>t===compact)?0:fields.some(t=>t.includes(compact))?1:2};
  }).filter(r=>r.match).sort((a,b)=>a.rank-b.rank||a.p.address.localeCompare(b.p.address,'ko'));
  $('#buildingSearchStatus').textContent='두 동 전체에서 '+fmt(rows.length)+'건'+(rows.length>8?' · 우선 8건 표시. 건물번호나 이름을 더 입력하세요.':'')+' · 주소를 선택하면 담당 제안 권역을 표시합니다.';
  rows.slice(0,8).forEach(({p})=>{
    const a=state.pilot.areas[p.area_id],r=a.survey_assignments.find(r=>r.building_id===p.building_id),ref=r&&a.survey_references.find(v=>v.reference_id===r.reference_id);
    const b=el('button',null,'nearby-card address-result');b.type='button';
    b.append(el('strong',p.building_names?.join(' / ')||p.housing_use),el('span',p.address),el('small',a.summary.name+' · '+(ref?ref.sector_number+'권역 제안':'별도 검토 · 제안 배정 없음')));
    b.addEventListener('click',()=>focusBuilding(p));list.append(b);
  });
  if(!rows.length)list.append(el('p','수집된 두 동의 자료에서 찾지 못했어요. 도로명 철자·건물번호를 확인하거나 건물명만 입력해 보세요. 미수집 건물은 임의로 위치를 만들지 않습니다.'));
}
$('#buildingSearch').addEventListener('input',renderBuildingSearch);
function distance(a,b){const rad=v=>v*Math.PI/180,dlat=rad(a.lat-b.lat),dlon=rad(a.lon-b.lon),h=Math.sin(dlat/2)**2+Math.cos(rad(a.lat))*Math.cos(rad(b.lat))*Math.sin(dlon/2)**2;return 6371000*2*Math.atan2(Math.sqrt(h),Math.sqrt(Math.max(0,1-h)));}
function renderNearby(){
  const box=$('#nearbyList');box.replaceChildren();$('#clearLocation').disabled=!state.position&&!state.locating;
  if(!state.position){$('#nearbySummary').textContent='내 위치를 누르면 가까운 조사 기준점까지 직선거리를 볼 수 있습니다. 실제 배출장소 추천이 아닙니다.';return;}
  $('#nearbySummary').textContent='현재 위치 기준 · 직선거리 · 현장 조사 기준점이며 실제 배출 불가';
  areas().flatMap(a=>a.survey_references).map(p=>({p,d:distance(state.position,p)})).sort((a,b)=>a.d-b.d).slice(0,3).forEach(({p,d})=>{const b=el('button',p.name+' / '+fmt(Math.round(d),'m'),'nearby-card');b.addEventListener('click',()=>{showReference(p);if(state.map)state.map.setView([p.lat,p.lon],17);});box.append(b);});
}
function renderPosition(){
  if(!state.map||!state.locationLayer)return;state.locationLayer.clearLayers();if(!state.position)return;
  const p=state.position;L.circle([p.lat,p.lon],{radius:p.accuracy,color:'#2879c6',weight:1,fillOpacity:.05}).addTo(state.locationLayer);
  L.circleMarker([p.lat,p.lon],{radius:7,color:'#fff',weight:2,fillColor:'#2879c6',fillOpacity:1}).addTo(state.locationLayer).bindTooltip('내 위치');
}
$('#locateMe').addEventListener('click',()=>{
  if(state.locating)return;
  if(!window.isSecureContext||!navigator.geolocation){$('#locationStatus').textContent='위치 확인은 localhost 또는 HTTPS와 위치 권한이 필요합니다.';return;}
  const seq=++state.locationSeq;state.locating=true;$('#locateMe').disabled=true;$('#clearLocation').disabled=false;$('#locationStatus').textContent='위치 권한을 확인하고 있습니다.';
  navigator.geolocation.getCurrentPosition(result=>{
    if(seq!==state.locationSeq)return;state.locating=false;$('#locateMe').disabled=false;
    const {latitude:lat,longitude:lon,accuracy}=result.coords;if(![lat,lon,accuracy].every(Number.isFinite))return;
    state.position={lat,lon,accuracy};renderPosition();renderNearby();if(state.map)state.map.setView([lat,lon],16);
    $('#locationStatus').textContent='내 위치 확인 / 오차 약 '+fmt(Math.round(accuracy),'m')+' / 이 페이지에서만 사용하며 저장하지 않습니다.';
  },()=>{if(seq!==state.locationSeq)return;state.locating=false;$('#locateMe').disabled=false;$('#locationStatus').textContent='위치를 확인하지 못했습니다. 권한·연결 상태를 확인해 주세요.';renderNearby();},{enableHighAccuracy:true,timeout:12000,maximumAge:30000});
});
$('#clearLocation').addEventListener('click',()=>{state.locationSeq++;state.locating=false;state.position=null;$('#locateMe').disabled=false;renderPosition();renderNearby();fitMap();$('#locationStatus').textContent='위치 정보를 지웠습니다.';});
function selectBasemap(mode,updateURL=true){
  if(!['street','satellite','hybrid'].includes(mode))return;
  if(mode!=='street'&&!state.mapConfig?.imagery_available){$('#basemapNote').textContent=state.mapConfig?.message||'영상지도 설정을 확인하고 있습니다.';return;}
  state.basemap=mode;state.imageryLoaded=0;state.imageryErrors=0;
  $$('#basemapButtons button').forEach(b=>{const selected=b.dataset.basemap===mode;b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',String(selected));});
  if(updateURL){const url=new URL(location.href);if(mode==='street')url.searchParams.delete('basemap');else url.searchParams.set('basemap',mode);history.replaceState(null,'',url);}
  $('#basemapNote').textContent=mode==='street'?'일반지도 · 위치·권역과 도로명을 확인하세요.':'촬영일 미확인 · 실시간 영상이 아닙니다. 사진을 자세히 보려면 제안 권역 표시를 꺼보세요.';
  if(!state.map||!state.basemapLayers)return;
  Object.values(state.basemapLayers).forEach(l=>{if(state.map.hasLayer(l))state.map.removeLayer(l);});
  const layers=state.basemapLayers;
  if(mode==='street')layers.street.addTo(state.map);
  else{layers.satellite.addTo(state.map);if(mode==='hybrid')layers.labels.addTo(state.map);}
  $('#mapState').textContent=mode==='street'?'일반지도 · OSM':'영상 불러오는 중';
  renderMap();
}
$('#basemapButtons').addEventListener('click',e=>{const button=e.target.closest('[data-basemap]');if(button&&!button.disabled)selectBasemap(button.dataset.basemap);});
function loadMapLibrary() {
  const link=document.createElement('link');link.rel='stylesheet';link.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';link.integrity='sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';link.crossOrigin='';document.head.append(link);
  const script=document.createElement('script');script.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';script.integrity='sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';script.crossOrigin='';
  script.onerror=()=>{$('#mapState').textContent='좌표 도식 · 배경 미연결';$('#mapNote').textContent='실제 지도 확대·이동은 지도 연결이 필요합니다. 아래 목록은 계속 사용할 수 있습니다.';};
  script.onload=()=>{
    if(!window.L)return;
    $('#fallbackMap').classList.add('hidden');
    state.map=L.map('map',{scrollWheelZoom:true,touchZoom:true,keyboard:true,preferCanvas:true});
    state.layer=L.layerGroup().addTo(state.map);
    state.locationLayer=L.layerGroup().addTo(state.map);
    const street=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',updateWhenIdle:true}).on('tileerror',()=>{if(state.basemap==='street')$('#mapState').textContent='일반 배경 연결 확인 필요';}).on('load',()=>{if(state.basemap==='street')$('#mapState').textContent='일반지도 · OSM';});
    const attribution='&copy; <a href="https://www.vworld.kr/" target="_blank" rel="noopener noreferrer">국토교통부 · VWorld</a>';
    const satellite=L.tileLayer('/api/map/tiles/Satellite/{z}/{x}/{y}',{minZoom:1,maxZoom:19,maxNativeZoom:19,attribution,updateWhenIdle:true,keepBuffer:1,zIndex:1})
      .on('tileload',()=>{if(state.basemap!=='street'){state.imageryLoaded++;$('#mapState').textContent=state.basemap==='hybrid'?'영상+도로명 · VWorld':'위성·항공 · VWorld';}})
      .on('tileerror',()=>{if(state.basemap==='street')return;state.imageryErrors++;if(state.imageryErrors>=3&&!state.imageryLoaded){selectBasemap('street');$('#basemapNote').textContent='영상을 불러오지 못해 일반지도로 전환했어요. VWorld의 WMTS/TMS 권한·등록 URL과 연결 상태를 확인해 주세요.';}else $('#basemapNote').textContent='일부 영상이 누락됐어요. 범위·연결 상태를 확인해 주세요. 촬영일은 미확인입니다.';});
    const labels=L.tileLayer('/api/map/tiles/Hybrid/{z}/{x}/{y}',{minZoom:1,maxZoom:19,maxNativeZoom:19,attribution,updateWhenIdle:true,keepBuffer:1,zIndex:2}).on('tileerror',()=>{if(state.basemap==='hybrid')$('#basemapNote').textContent='도로명 일부를 불러오지 못했어요. 위성·항공 보기로 사진만 볼 수 있어요.';});
    state.basemapLayers={street,satellite,labels};selectBasemap(state.basemap,false);
    fitMap();renderMap();renderPosition();
    if(state.position)state.map.setView([state.position.lat,state.position.lon],16);
    if(state.page!=='home')setTimeout(()=>state.map.invalidateSize(),0);
  };
  document.head.append(script);
}
async function sendChat(message) {
  if(state.chatBusy||!message.trim()||message.length>500)return;
  state.chatBusy=true;const target=$('#chatMessages');
  target.append(el('div',message,'bubble user'));const bubble=el('div','안내를 조회하고 있습니다.','bubble bot');target.append(bubble);
  $$('#chatForm button,.quick-prompts button').forEach(b=>b.disabled=true);
  try{
    if(state.apiReady){
      const district=$('#chatDistrict').value;
      const data=await api('/api/chat',{...jsonOptions('POST',{message,district_code:district,context:state.chatContext}),timeoutMs:140000});
      if(district!==$('#chatDistrict').value){bubble.textContent='지역이 변경되어 이전 지역의 응답을 닫았어요. 새 지역으로 다시 질문해 주세요.';return;}
      state.chatContext=data.context||null;
      const method=data.retrieval?.mode==='item_database'?'공식 품목 DB 조회 · 규격/금액 자동 추정 없음':data.retrieval?.embedding_used?'임베딩 문서 검색 · 답변 생성 없음':data.citations?.length?'문서 키워드 검색 · 모델 미사용':data.ai_used?'AI 분류 + 저장된 규칙':'규칙 기반 안내 · LLM 미사용';
      bubble.textContent=data.response;
      if(data.suggestions?.length){const choices=el('div',null,'chat-choices');data.suggestions.forEach(s=>{const b=el('button',s.label,'minor');b.type='button';b.addEventListener('click',()=>sendChat(s.message));choices.append(b);});bubble.append(choices);}
      const detail=el('details',null,'retrieval-note');detail.append(el('summary','안내 방식'),el('p',method));bubble.append(detail);
      $('#aiStatus').textContent=['item_clarification','facility_clarification'].includes(data.mode)?'추가 확인 필요':data.mode==='item_database'?'품목표 조회 완료':data.citations?.length?'공식 안내 찾음':data.ai_used?'질문 분류 완료':'추가 자료 필요';
      if(data.retrieval?.message)bubble.append(el('p',data.retrieval.message,'retrieval-note'));
      renderKnowledgeReferences(bubble,data.citations || []);
    }else {bubble.textContent='서버 연결을 확인해 주세요. 연결되지 않은 상태에서 배출 방법을 추정하지 않습니다.';$('#aiStatus').textContent='서버 연결 필요';}
  }catch(e){bubble.textContent='안내를 불러오지 못했어요. 잠시 후 다시 보내주세요. '+e.message;$('#aiStatus').textContent='연결 확인 필요';}
  finally{state.chatBusy=false;$$('#chatForm button,.quick-prompts button').forEach(b=>b.disabled=false);target.scrollTop=target.scrollHeight;}
}
function renderKnowledgeReferences(parent,citations) {
  if(!citations.length)return;
  const list=el('div',null,'knowledge-references');
  list.append(el('strong','관련 공식 안내 · '+citations.length+'건'));
  citations.forEach(item=>{
    const card=el('article',null,'reference-card');
    card.append(el('h3',item.title),el('p',item.text));
    card.append(el('small',(item.district_name || '지역 미확인')+' · 원문 확인 '+item.checked_at+' · 원문 기준일 '+(item.reference_date || '미명시')));
    const period=item.effective_from || item.effective_until
      ? '시행기간 '+(item.effective_from || '시작 미명시')+' ~ '+(item.effective_until || '종료 미명시')
      : '시행기간 미명시 · 확인일은 시행일과 다릅니다.';
    card.append(el('small',period),safeLink(item.source_url,'공식 원문에서 확인하기'));
    list.append(card);
  });
  parent.append(list);
}
async function refreshKnowledgeStatus() {
  try {
    const [status,items,hub]=await Promise.all([api('/api/knowledge/status'),api('/api/waste-items/status'),api('/api/data-hub/status')]);
    $('#knowledgeStatus').textContent='양천구 공식 품목 '+items.item_count+'개 · 규격별 수수료 '+items.rule_count+'건 · 안내 요약 '+status.chunk_count+'개 · '+(status.embedding_enabled && status.index_complete
      ? '의미 검색 사용 설정 · 질문할 때 연결 확인'
      : '키워드 검색과 기본 안내 이용 가능');
    $('#hubStatus').textContent='자료 묶음: 두 지역 '+fmt(hub.building_parcels)+'필지 · 출처 기록 '+hub.source_count+'개 · 안내 요약 '+hub.guidance_documents+'개 · 추가 조사 항목 '+hub.gaps+'개. 전국 전체 품목·운영점 확보 완료를 뜻하지 않습니다.';
  } catch { $('#knowledgeStatus').textContent='문서 상태 조회 실패 · 기본 안내 사용'; }
}
$('#chatForm').addEventListener('submit',e=>{e.preventDefault();const input=$('#chatInput');const message=input.value.trim();if(message&&!state.chatBusy){input.value='';sendChat(message);}});
$('#chatDistrict').addEventListener('change',()=>{state.chatContext=null;$('#chatMessages').replaceChildren(el('div','안내 지역을 변경했어요. 이전 품목·규격 연결을 지웠습니다. 새 지역의 물건과 궁금한 점을 알려주세요.','bubble bot'));$('#aiStatus').textContent='지역 변경';});
$$('[data-prompt]').forEach(b=>b.addEventListener('click',()=>sendChat(b.dataset.prompt)));

$('#exportAnalysis').addEventListener('click',()=>{if(!state.pilot)return;const url=URL.createObjectURL(new Blob([JSON.stringify(state.pilot,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download='greenzone-official-area-analysis.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
async function initialize(){
  go(location.hash.slice(1)||'home',false);loadMapLibrary();
  try{
    const [data,config,mapConfig]=await Promise.all([api('/api/pilot-analysis',{timeoutMs:30000}),api('/api/config'),api('/api/map/config').catch(()=>null)]);
    state.mapConfig=mapConfig;$$('#basemapButtons button').forEach(b=>{b.disabled=b.dataset.basemap!=='street'&&!mapConfig?.imagery_available;});
    if(!mapConfig?.imagery_available)$('#basemapNote').textContent=mapConfig?.message||'영상지도 설정을 확인하지 못했습니다. 일반지도는 사용할 수 있어요.';
    state.pilot=data;state.apiReady=true;$('#apiState').textContent='공식 자료 연결';renderOverview();renderMap();fitMap();renderBuildingSearch();
    if(['satellite','hybrid'].includes(initialBasemap)&&mapConfig?.imagery_available)selectBasemap(initialBasemap,false);
    $('#aiStatus').textContent='질문을 입력해 주세요';await refreshKnowledgeStatus();
  }catch(e){$('#apiState').textContent='자료 연결 확인 필요';notify('공식 분석 자료를 불러오지 못했습니다. 서버 연결을 확인해 주세요. '+e.message);}
}
initialize();
