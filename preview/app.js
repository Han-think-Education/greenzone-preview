'use strict';
// 기능 시연 전용: 모든 건물·시설·지도 좌표는 가상입니다.
const labels={general:'일반 생활폐기물',recycle:'재활용품',battery:'폐건전지',bulky:'대형폐기물'};
const pointCoords={A:[[107,120],[165,116],[221,124],[292,115],[353,130],[124,171],[207,174],[312,176]],B:[[525,125],[587,121],[654,130],[715,119],[774,144],[542,176],[632,172],[753,178]],C:[[161,356],[229,355],[309,358],[490,345],[553,373],[632,400],[259,407],[412,412]]};
const DEMO_BUILDINGS=Object.entries(pointCoords).flatMap(([zone,pts])=>pts.map(([x,y],i)=>({id:`${zone}-${String(i+1).padStart(2,'0')}`,name:`데모 빌라 ${zone}-${String(i+1).padStart(2,'0')}`,address:`ZONE-${zone} 시연용 가상 주소`,zone,x,y,verified:false})));
let buildings=DEMO_BUILDINGS,zone='ALL',selected='A-01',lastResult=null,requests=[],apiReady=false;
const sessionSave=(key,value)=>{try{sessionStorage.setItem(key,value)}catch{/* 보안 제한 브라우저에서는 메모리만 사용 */}};
const sessionLoad=(key)=>{try{return sessionStorage.getItem(key)}catch{return null}};
const sessionRemove=(key)=>{try{sessionStorage.removeItem(key)}catch{/* no-op */}};
const $=s=>document.querySelector(s),$$=s=>Array.from(document.querySelectorAll(s));
const el=(tag,text,cls)=>{const o=document.createElement(tag);if(text!=null)o.textContent=text;if(cls)o.className=cls;return o;};
function go(page){$$('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===page));['home','assistant','admin','architecture'].forEach(p=>$('#'+p+'Page').classList.toggle('hidden',p!==page));$('#crumb').textContent=({home:'서비스 지도',assistant:'AI 배출 도우미',admin:'관리자 대시보드',architecture:'시스템 구성'})[page];location.hash=page; if(page==='admin')renderRequests();}
$$('.nav-item').forEach(b=>b.addEventListener('click',()=>go(b.dataset.page)));$('#toAssistant').addEventListener('click',()=>go('assistant'));
function renderMap(){const group=$('#buildingLayer');group.innerHTML='';for(const b of buildings){const g=document.createElementNS('http://www.w3.org/2000/svg','g');g.setAttribute('class','building-dot'+(selected===b.id?' is-active':'')+(zone!== 'ALL'&&b.zone!==zone?' dim':''));g.setAttribute('tabindex','0');g.setAttribute('role','button');g.setAttribute('aria-label',b.name+' 선택');const r=document.createElementNS('http://www.w3.org/2000/svg','rect');r.setAttribute('x',b.x-10);r.setAttribute('y',b.y-10);r.setAttribute('width',20);r.setAttribute('height',20);r.setAttribute('rx',5);r.setAttribute('transform',`rotate(-12 ${b.x} ${b.y})`);g.append(r);const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=b.name;g.append(title);g.addEventListener('click',()=>pick(b.id));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();pick(b.id)}});group.append(g);}for(const z of ['A','B','C']){$('#area'+z).style.opacity=(zone==='ALL'||z===zone)?'1':'.2';}}
function pick(id){selected=id;const b=buildings.find(x=>x.id===id);if(!b)return;$('#buildingSelect').value=id;$('#buildingContext').textContent=`${b.name} · ${b.address} · 실제 주소 검증 전`;lastResult=null;$('#requestButton').disabled=true;$('#matchResult').innerHTML='<div class="result-empty">품목을 선택하고 배출 방법을 확인하세요.</div>';renderMap();}
function rebuildSelect(){const q=$('#buildingSearch').value.toLowerCase().trim();const items=buildings.filter(b=>(zone==='ALL'||zone===b.zone)&&(`${b.id} ${b.name} ${b.address} ZONE ${b.zone}`).toLowerCase().includes(q));const s=$('#buildingSelect');s.innerHTML='';items.forEach(b=>{const op=el('option',`${b.id} · ${b.name}`);op.value=b.id;s.append(op)});if(!items.length){let o=el('option','일치하는 건물이 없습니다');o.value='';s.append(o);lastResult=null;$('#requestButton').disabled=true;$('#buildingContext').textContent='검색 결과 없음';return}if(!items.find(b=>b.id===selected))selected=items[0].id;pick(selected)}
$('#buildingSearch').addEventListener('input',rebuildSelect);$('#buildingSelect').addEventListener('change',e=>pick(e.target.value));$('#zoneButtons').addEventListener('click',e=>{const btn=e.target.closest('button[data-zone]');if(!btn)return;zone=btn.dataset.zone;$$('#zoneButtons button').forEach(b=>b.classList.toggle('selected',b===btn));rebuildSelect()});
function computeResult(kind,b,q){const disclaimer='아래 장소·일정은 시연용입니다. 실제 배출 규칙과 위치를 공식 자료로 검증한 후 제공해야 합니다.';if(kind==='general')return {heading:'건물별 배출 기준 확인',detail:'해당 건물 앞의 허용된 배출 위치와 공식 배출 요일을 확인해야 합니다. 이 데모는 실제 배출 위치를 제공하지 않습니다.',distance:null,link:null,disclaimer};if(kind==='recycle')return {heading:'분리배출 방법 확인',detail:'품목별 분리배출 기준과 건물별 배출 위치를 확인해야 합니다. 검증된 공용 시설이 아직 등록되지 않았습니다.',distance:null,link:null,disclaimer};if(kind==='battery')return {heading:'전용 수거 시설 후보',detail:'데모 지도에 초록색으로 표시된 시설은 모두 가상입니다. 실제 운영 여부 및 수거 품목을 확인하기 전에는 추천하지 않습니다.',distance:'실제 이용 가능 시설: 검증 전',link:null,disclaimer};return {heading:'대형폐기물 신고 안내',detail:'가구류는 지역의 대형폐기물 신고 절차를 확인하세요. 자체 앱에서는 결제나 수거 신청이 이루어지지 않습니다.',distance:null,link:'https://smartclean.yangcheon.go.kr/',disclaimer};}
async function showMatch(){
  const b=buildings.find(x=>x.id===selected);if(!b)return;
  const qty=Number($('#quantity').value);
  if(!Number.isInteger(qty)||qty<1||qty>99){alert('수량은 1~99 사이 정수로 지정하세요.');return;}
  const kind=$('#categorySelect').value;
  let res=computeResult(kind,b,qty);
  if(apiReady){
    try{
      const response=await fetch('/api/match',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({building_id:b.id,category:kind,quantity:qty})});
      if(!response.ok)throw new Error('HTTP '+response.status);
      const result=await response.json();
      res={heading:'FastAPI · SQLite 조회 성공',detail:result.guidance,distance:null,link:result.official_url,disclaimer:'검증되지 않은 시연용 건물·거점 데이터입니다. 실제 배출 위치로 사용 금지.'};
    }catch(error){
      alert('FastAPI 매칭에 실패했습니다. 네트워크나 API를 확인해 주세요. ('+error.message+')');return;
    }
  }
  lastResult={building_id:b.id,building_name:b.name,zone:b.zone,category:kind,quantity:qty,verification_status:'unverified',demo:true};
  const box=$('#matchResult');box.replaceChildren();box.append(el('div','조회 결과 · '+(apiReady?'API 연결':'시뮬레이션'),'result-label'));box.append(el('div',res.heading,'result-title'));box.append(el('div',`${b.name} / ${labels[kind]} / ${qty}개`,'chip'));box.append(el('p',res.detail));if(res.distance)box.append(el('p',res.distance,'warning'));if(res.link){const x=el('p');const a=el('a','양천구 공식 서비스 열기 ↗');a.href=res.link;a.target='_blank';a.rel='noopener noreferrer';x.append(a);box.append(x)}box.append(el('p','⚠ '+res.disclaimer,'warning'));$('#requestButton').disabled=false;
}
$('#matchButton').addEventListener('click',showMatch);
$('#requestButton').addEventListener('click',async ()=>{
  if(!lastResult)return;
  if(apiReady){
    try{
      const r=await fetch('/api/requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({building_id:lastResult.building_id,category:lastResult.category,quantity:lastResult.quantity})});
      if(!r.ok)throw new Error('HTTP '+r.status);
      await refreshRequests();
    }catch(error){alert('요청 저장 실패: '+error.message);return;}
  }else{
    const record={...lastResult,id:requests.length+1,status:'시연 접수'};
    requests.push(record);sessionSave('preview_requests',JSON.stringify(requests));
    $('#countRequests').textContent=String(requests.length).padStart(2,'0');
  }
  $('#requestButton').textContent='✓ 데모 요청 등록됨';$('#requestButton').disabled=true;
  setTimeout(()=>$('#requestButton').textContent='＋ 데모 요청 등록',900);
});
async function refreshRequests(){
  if(!apiReady)return;
  const response=await fetch('/api/requests');if(!response.ok)throw new Error('requests HTTP '+response.status);
  requests=(await response.json()).map(r=>({id:r.request_id,building_name:buildings.find(b=>b.id===r.building_id)?.name||r.building_id,category:r.category,quantity:r.quantity,status:'시연 접수(DB)'}));
  $('#countRequests').textContent=String(requests.length).padStart(2,'0');
}
function renderRequests(){const tbody=$('#requestsTable');tbody.replaceChildren();$('#adminRequestCount').textContent=String(requests.length).padStart(2,'0');if(!requests.length){const tr=el('tr');const td=el('td','아직 접수된 시연 요청이 없습니다. 지도에서 데모 요청을 등록해 보세요.');td.colSpan=5;tr.append(td);tbody.append(tr);return;}for(const r of requests){const tr=el('tr');[String(r.id),r.building_name,labels[r.category],String(r.quantity),r.status].forEach(value=>tr.append(el('td',value)));tbody.append(tr)}}
$('#clearRequests').addEventListener('click',()=>{if(apiReady){alert('실행 중인 DB의 기록은 삭제하지 않습니다. SQLite 요청 목록은 유지됩니다.');return;}requests=[];sessionRemove('preview_requests');$('#countRequests').textContent='00';renderRequests()});
function replyFor(t){if(/건전지|배터리|battery/.test(t))return '의도: 폐건전지 배출 문의\n→ 검증된 수거함 데이터 조회 단계가 필요합니다. 현재 화면의 초록색 시설 2개는 모두 가상 시설이며, 실제 위치로 이용하면 안 됩니다.';if(/의자|책상|침대|소파|가구|대형/.test(t))return '의도: 대형폐기물 배출\n→ 양천구 공식 배출신고 절차를 확인해야 합니다. 시연용 앱은 실제 신고를 대신하지 않습니다.\n공식 서비스: https://smartclean.yangcheon.go.kr/';if(/재활용|플라스틱|종이|캔/.test(t))return '의도: 재활용품\n→ 거주 건물의 배출 위치 및 품목별 분리배출 기준 확인이 필요합니다. 시설·시간 정보는 검증 전이므로 임의의 위치를 추천하지 않습니다.';if(/쓰레기|종량제|배출|버리/.test(t))return '의도: 일반 생활폐기물\n→ 건물별 배출 위치와 해당 행정동의 공식 배출 요일을 조회해야 합니다. 현재는 DB와 LangGraph가 연결되지 않은 프리뷰 응답입니다.';return '입력을 명확히 분류하지 못했습니다. 일반쓰레기, 재활용품, 폐건전지, 대형폐기물 중 어떤 품목인지 알려주세요.';}
async function sendChat(s){
  const target=$('#chatMessages');target.append(el('div',s,'bubble user'));
  const bubble=el('div','응답 생성 중...','bubble bot');target.append(bubble);target.scrollTop=target.scrollHeight;
  if(apiReady){
    try{
      const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:s})});
      if(!r.ok)throw new Error('HTTP '+r.status);
      const data=await r.json();bubble.textContent=data.response+'\n\n['+data.mode+(data.ai_used?' · Ollama 사용':' · LLM 미사용')+']';
    }catch(error){bubble.textContent='AI API 오류 ('+error.message+'). 서버 상태를 확인해 주세요.';}
  }else{bubble.textContent=replyFor(s)+'\n\n[오프라인 시뮬레이션 · Ollama 미연결]';}
  target.scrollTop=target.scrollHeight;
}
$('#chatForm').addEventListener('submit',e=>{e.preventDefault();const input=$('#chatInput'),s=input.value.trim();if(s){sendChat(s);input.value='';}});$$('[data-prompt]').forEach(b=>b.addEventListener('click',()=>sendChat(b.dataset.prompt)));
async function hydrateFromAPI(){
  if(location.protocol==='file:'){$('#apiState').textContent='● 독립 프리뷰';$('#aiStatus').textContent='오프라인 시뮬레이션';return;}
  try{
    const health=await fetch('/health');if(!health.ok)throw new Error('FastAPI 없음');
    const json=await health.json();if(json.status!=='ok')throw new Error('FastAPI 미확인');
    apiReady=true;
    const result=await fetch('/api/buildings');if(!result.ok)throw new Error('건물 조회 실패');
    const rows=await result.json();
    buildings=rows.map(r=>{const dot=DEMO_BUILDINGS.find(b=>b.id===r.building_id);return {...(dot||{x:-100,y:-100}),id:r.building_id,name:r.building_name,address:r.road_address,zone:r.zone_id,verified:r.verification_status==='verified'};});
    $('#apiState').textContent='● FastAPI + SQLite 연결';
    $('#countBuildings').textContent=String(buildings.length).padStart(2,'0');
    $('#adminBuildingCount').textContent=String(buildings.length).padStart(2,'0');
    await refreshRequests();rebuildSelect();renderMap();
    const status=await fetch('/api/ai/status');if(status.ok){const info=await status.json();$('#aiStatus').textContent=info.model_installed?'● Ollama: '+info.model:info.message;}
  }catch(error){
    apiReady=false;
    $('#apiState').textContent='● 독립 프리뷰 (API 미연결)';$('#aiStatus').textContent='오프라인 시뮬레이션';
  }
}
async function init(){
  try{requests=JSON.parse(sessionLoad('preview_requests')||'[]')}catch{requests=[]}
  $('#countRequests').textContent=String(requests.length).padStart(2,'0');
  $('#countBuildings').textContent=String(buildings.length).padStart(2,'0');
  rebuildSelect();const page=location.hash.slice(1);go(['home','assistant','admin','architecture'].includes(page)?page:'home');
  await hydrateFromAPI();
}
init();
