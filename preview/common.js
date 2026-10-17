'use strict';
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
const labels = {general:'일반 생활폐기물', recycle:'재활용품', battery:'폐건전지', bulky:'대형폐기물'};
const safetyLabels = {truck_access:'차량 진입', stopping_space:'정차 공간', work_space:'작업 공간', pedestrian_clear:'보행 통로'};
const reviewLabels = {review:'검토 중', selected:'배치안 채택', hold:'추가 확인·보류', excluded:'제외'};
function el(tag, text, cls) {
  const n = document.createElement(tag);
  if (text != null) n.textContent = String(text);
  if (cls) n.className = cls;
  return n;
}
function notify(text) {
  $('#globalNotice').textContent = text;
  $('#globalNotice').classList.toggle('hidden', !text);
}
function safeLink(url, label) {
  try {
    const u = new URL(url);
    if (!['http:', 'https:'].includes(u.protocol)) return el('span', label || '출처 미확인');
    const a = el('a', label || u.href); a.href = u.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a;
  } catch { return el('span', label || '출처 미확인'); }
}
function fmt(value, unit) { return value == null ? '미확인' : Number(value).toLocaleString('ko-KR',{maximumFractionDigits:1}) + (unit || ''); }
async function api(url, options) {
  const {timeoutMs=10000,...requestOptions}=options || {};
  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort(), timeoutMs);
  try {
    const r = await fetch(url, {credentials:'same-origin', signal:timeout.signal, ...requestOptions});
    const data = await r.json();
    if (!r.ok) {
      const detail = typeof data.detail === 'string' ? data.detail : '입력한 항목과 서버 상태를 확인해 주세요.';
      const error = new Error(detail); error.status = r.status; throw error;
    }
    return data;
  } finally { clearTimeout(timer); }
}
function jsonOptions(method, data) { return {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}; }
