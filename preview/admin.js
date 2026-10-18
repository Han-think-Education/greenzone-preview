'use strict';
const state={data:window.GREENZONE_CATALOG,apiReady:false,authenticated:false,configured:false,requests:[],requestsError:''};
function candidateFor(id){return state.data.candidates.find(c=>c.candidate_id===id);}
async function refreshRequests(){
  try{
    const rows=await api('/api/requests');
    state.requests=rows.map(r=>({id:r.request_id,building_name:state.data.buildings.find(b=>b.building_id===r.building_id)?.building_name || r.building_id,category:r.category,quantity:r.quantity,status:'내부 접수 기록'}));
    state.requestsError='';
  }catch(e){state.requestsError=e.message;}
  renderRequests();
}
function renderRequests() {
  $('#adminRequestCount').textContent=state.requestsError?'-':state.requests.length;
  const tbody=$('#requestsTable');tbody.replaceChildren();
  if(state.requestsError){const tr=el('tr'),td=el('td',state.requestsError);td.colSpan=5;tr.append(td);tbody.append(tr);return;}
  if(!state.requests.length){const tr=el('tr'),td=el('td','아직 접수 연계 기록이 없습니다.');td.colSpan=5;tr.append(td);tbody.append(tr);return;}
  state.requests.forEach(r=>{const tr=el('tr');[r.id,r.building_name,labels[r.category] || r.category,r.quantity,r.status].forEach(v=>tr.append(el('td',v)));tbody.append(tr);});
}
function renderAuth() {
  $('#loginPanel').classList.toggle('hidden',state.authenticated);
  $('#editorPanel').classList.toggle('hidden',!state.authenticated);
  $('#loginForm button').disabled=!state.apiReady||!state.configured;
  $('#loginHint').textContent=!state.apiReady?'독립 프리뷰에서는 수정할 수 없습니다. 서버를 실행해 주세요.':!state.configured?'서버에 담당자 암호 설정이 필요합니다. 실행 안내를 확인해 주세요.':'서버 실행 때 발급된 담당자 접속정보를 사용하세요.';
  if(state.authenticated)fillEditorLists();
  else $('#changeHistory').replaceChildren();
}
function fillEditorLists() {
  const oldCandidate=$('#editCandidateSelect').value,oldRule=$('#editRuleSelect').value;
  $('#editCandidateSelect').replaceChildren();state.data.candidates.forEach(c=>{const o=el('option',c.name);o.value=c.candidate_id;$('#editCandidateSelect').append(o);});
  if(candidateFor(oldCandidate))$('#editCandidateSelect').value=oldCandidate;
  $('#editRuleSelect').replaceChildren();state.data.rules.forEach(r=>{const o=el('option',labels[r.category] || r.category);o.value=r.rule_id;$('#editRuleSelect').append(o);});
  if(state.data.rules.some(r=>r.rule_id===oldRule))$('#editRuleSelect').value=oldRule;
  fillCandidateForm();fillRuleForm();
}
function fillCandidateForm() {
  const c=candidateFor($('#editCandidateSelect').value);if(!c)return;
  $('#editReview').value=c.review_status;$('#editLat').value=c.lat ?? '';$('#editLon').value=c.lon ?? '';
  $('#editCapacity').value=c.capacity ?? '';$('#capacityUnit').textContent=c.capacity_unit || '단위 미확인';
  $('#editRationale').value=c.rationale || '';$('#editSafetyNote').value=c.safety_note || '';
  const container=$('#safetyEdit');container.replaceChildren();
  Object.entries(safetyLabels).forEach(([key,label])=>{const l=el('label',label),s=el('select');s.id='edit-'+key;[['unknown','미확인'],['pass','검토 조건 충족'],['fail','부적합']].forEach(([v,t])=>{const o=el('option',t);o.value=v;s.append(o);});s.value=c[key] || 'unknown';l.append(s);container.append(l);});
}
function fillRuleForm() {
  const r=state.data.rules.find(r=>r.rule_id===$('#editRuleSelect').value);if(!r)return;
  $('#editDays').value=r.days || '';$('#editTime').value=r.time_text || '';$('#editGuidance').value=r.guidance || '';$('#editSourceUrl').value=r.source_url || '';$('#editReferenceDate').value=r.reference_date || '';
}
$('#editCandidateSelect').addEventListener('change',fillCandidateForm);$('#editRuleSelect').addEventListener('change',fillRuleForm);
$('#loginForm').addEventListener('submit',async e=>{
  e.preventDefault();$('#loginMessage').textContent='로그인 중...';
  try{await api('/api/auth/login',jsonOptions('POST',{username:$('#adminUsername').value,password:$('#adminPassword').value}));state.authenticated=true;state.data=await api('/api/catalog');$('#adminPassword').value='';$('#loginMessage').textContent='';renderAuth();await loadHistory();await refreshRequests();}
  catch(error){$('#loginMessage').textContent=error.message;}
});
$('#logoutButton').addEventListener('click',async()=>{try{await api('/api/auth/logout',jsonOptions('POST',{}));state.authenticated=false;renderAuth();}catch(e){notify(e.message);}});
function numericInput(id){return $(id).value.trim()===''?null:Number($(id).value);}
async function refreshCatalog() {
  state.data=await api('/api/catalog');if(state.authenticated)fillEditorLists();
}
async function loadHistory() {
  if(!state.authenticated)return;
  const box=$('#changeHistory');
  try{
    const rows=await api('/api/admin/history');box.replaceChildren();
    if(!rows.length)box.append(el('p','아직 수정 기록이 없습니다.'));
    rows.slice(0,8).forEach(r=>box.append(el('p',r.entity_id+' · '+new Date(r.changed_at).toLocaleString('ko-KR'))));
  }catch(error){box.replaceChildren(el('p','수정 기록 연결을 확인해 주세요.'));}
}
async function saveEditor(url,payload,messageId,form) {
  const button=form.querySelector('button[type=submit]');button.disabled=true;$(messageId).textContent='저장 중...';
  try{await api(url,jsonOptions('PATCH',payload));await refreshCatalog();await loadHistory();$(messageId).textContent='저장했습니다. 별도 분석 결과는 다시 분석·반영한 뒤 갱신됩니다.';}
  catch(e){$(messageId).textContent=e.message;if(e.status===401){state.authenticated=false;renderAuth();}if(e.status===409)await refreshCatalog();}
  finally{button.disabled=false;}
}
$('#candidateForm').addEventListener('submit',e=>{
  e.preventDefault();const c=candidateFor($('#editCandidateSelect').value);if(!c)return;
  const payload={revision:c.revision,review_status:$('#editReview').value,lat:numericInput('#editLat'),lon:numericInput('#editLon'),capacity:numericInput('#editCapacity'),rationale:$('#editRationale').value,safety_note:$('#editSafetyNote').value};
  Object.keys(safetyLabels).forEach(k=>payload[k]=$('#edit-'+k).value);
  saveEditor('/api/admin/candidates/'+encodeURIComponent(c.candidate_id),payload,'#candidateMessage',e.target);
});
$('#ruleForm').addEventListener('submit',e=>{
  e.preventDefault();const r=state.data.rules.find(r=>r.rule_id===$('#editRuleSelect').value);if(!r)return;
  saveEditor('/api/admin/rules/'+encodeURIComponent(r.rule_id),{revision:r.revision,days:$('#editDays').value,time_text:$('#editTime').value,guidance:$('#editGuidance').value,source_url:$('#editSourceUrl').value,reference_date:$('#editReferenceDate').value},'#ruleMessage',e.target);
});

$('#clearRequests').addEventListener('click',()=>notify('서버 기록은 삭제하지 않습니다. 최근 100건을 표시합니다.'));
async function initializeAdmin(){
  renderAuth();
  if(location.protocol==='file:'){$('#apiState').textContent='서버 실행 필요';return;}
  try{
    const [catalog,session]=await Promise.all([api('/api/catalog'),api('/api/auth/session')]);
    state.data=catalog;state.apiReady=true;state.authenticated=session.authenticated;state.configured=session.configured;
    $('#apiState').textContent='관리 서버 연결';renderAuth();
    if(state.authenticated){await loadHistory();await refreshRequests();}
  }catch(e){$('#apiState').textContent='서버 미연결';notify(e.message);renderAuth();}
}
initializeAdmin();
