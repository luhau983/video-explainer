'use strict';
const $ = id => document.getElementById(id);
const fields = ['id','characters','scene','camera','motion'];
let state, selected = 0, dirty = false;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function notice(message, error=false) { $('notice').textContent = message; $('notice').hidden = false; $('notice').className = error ? 'error' : ''; }
async function api(url, body) {
  const options = body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)};
  const response = await fetch(url, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Không thể hoàn tất thao tác');
  return result;
}
function mediaFor(id, type) { return state.assets.find(a => a.path.startsWith(`out/${type}/${id}.`)); }
function renderTable() {
  $('scene-rows').innerHTML = state.scenes.map((s,i) => `<tr data-index="${i}" tabindex="0" aria-label="Chọn cảnh ${esc(s.id)}" aria-selected="${i===selected}" class="${i===selected?'selected':''}"><td>${esc(s.id)}</td><td><div class="scene-text">${esc(s.scene)}</div><div class="character-tags">${esc(s.characters.replaceAll(';',' · ') || 'Không có nhân vật cố định')}</div></td><td>${esc(s.camera)}</td><td><span class="asset-status ${mediaFor(s.id,'images')?'ready':''}">${mediaFor(s.id,'images')?'Có ảnh':'Chưa có ảnh'}</span><span class="asset-status ${mediaFor(s.id,'audio')?'ready':''}">${mediaFor(s.id,'audio')?'Có audio':'Chưa có audio'}</span></td></tr>`).join('');
  document.querySelectorAll('[data-index]').forEach(row => {
    const choose = () => { selected = Number(row.dataset.index); renderTable(); renderDetail(); };
    row.addEventListener('click', choose); row.addEventListener('keydown', e => {if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}});
  });
}
function renderDetail() {
  const s = state.scenes[selected]; if (!s) return;
  $('selected-id').textContent = s.id;
  fields.forEach(f => $('field-'+f).value = s[f]);
  const video = mediaFor(s.id,'videos'), image = mediaFor(s.id,'images');
  $('scene-preview').innerHTML = video ? `<video controls preload="metadata" src="${esc(video.url)}"></video>` : image ? `<img src="${esc(image.url)}" alt="Ảnh thật cảnh ${esc(s.id)}">` : `<div class="empty-frame" aria-hidden="true"></div><strong>Chưa có ảnh cảnh ${esc(s.id)}</strong><small>out/images/${esc(s.id)}.png</small>`;
}
function render() {
  const images = state.scenes.filter(s=>mediaFor(s.id,'images')).length;
  const audio = state.scenes.filter(s=>mediaFor(s.id,'audio')).length;
  const sheets = state.characters.filter(c=>c.images.length).length;
  $('summary').innerHTML = [[state.scenes.length,'phân cảnh','scenes.csv'],[`${images}/${state.scenes.length}`,'ảnh cảnh','Đọc từ đĩa'],[`${audio}/${state.scenes.length}`,'đoạn thoại','Đọc từ đĩa'],[state.prompts.length,'motion prompts','Tệp CSV hiện có']].map(([n,t,b])=>`<div class="summary-item"><strong>${n}</strong><span>${t}</span><em>${b}</em></div>`).join('');
  $('script-editor').value = state.script; $('style-editor').value = state.style;
  selected = Math.min(selected, state.scenes.length-1); renderTable(); renderDetail();
  $('motion-note').textContent = state.timing_available ? 'Có timing.csv; thời lượng sẽ dựa vào audio đã đo. Lưu chỉnh sửa trước khi tạo.' : 'Chưa có timing.csv: script dùng 4,5 giây thoại mặc định / cảnh, không phải thời lượng đã đo. Lưu chỉnh sửa trước khi tạo.';
  $('prompt-list').innerHTML = state.prompts.length ? state.prompts.map(p=>`<div class="prompt-row"><b>${esc(p.id)}<br>${esc(p.duration)}s</b><div>${esc(p.prompt)}<p>Thoại: ${esc(p.speech)}s · override=${esc(p.override)}</p></div></div>`).join('') : '<p>Chưa có motion_prompts.csv.</p>';
  $('character-list').innerHTML = state.characters.map(c=>`<article class="character"><div>${c.images.length ? c.images.map(url=>`<img src="${esc(url)}" alt="Sheet nhân vật ${esc(c.name)}">`).join('') : '<div class="character-empty">Chưa có character sheet<br><small>Không có ảnh tham chiếu</small></div>'}</div><div><span class="eyebrow">CHARACTER / ${esc(c.name)}</span><h3>${esc(c.name)}</h3><p>${esc(c.description)}</p><p class="sheet-hint">characters/${esc(c.name)}/ · ${c.images.length} ảnh trên đĩa</p></div></article>`).join('');
  const pipeline = [
    ['Kịch bản & phân cảnh','Có dữ liệu',`${state.scenes.length} cảnh. Kiểm tra ID, nhân vật và trường bắt buộc mỗi lần lưu.`],
    ['Character sheets',`${sheets}/${state.characters.length} nhân vật có ảnh`,'Chỉ hiển thị ảnh đã có. Tạo character sheet chưa tích hợp.'],
    ['Ảnh cảnh',`${images}/${state.scenes.length} ảnh`,'Chưa tích hợp tạo ảnh; không gọi Codex hay dịch vụ hình ảnh.'],
    ['Giọng đọc',`${audio}/${state.scenes.length} đoạn thoại`,'TTS chưa tích hợp vào UI. Không gọi edge-tts qua mạng.'],
    ['Motion prompts',`${state.prompts.length} dòng CSV`,'Có thể tạo cục bộ bằng build_motion_prompts.py. Giữ các dòng override=1.'],
    ['Video & dựng cuối','Chưa tích hợp','submit_job / poll_job còn NotImplemented. Chưa có pipeline dựng cuối.']
  ];
  $('pipeline-list').innerHTML = pipeline.map(([title,status,desc],i)=>`<div class="pipeline-row"><span>0${i+1}</span><div><strong>${title}</strong><small>${status}</small></div><p>${desc}</p></div>`).join('');
  $('asset-list').innerHTML = state.assets.length ? state.assets.map(a=>`<article class="asset-entry"><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.path)}</a>${/\.(png|jpg|jpeg|webp)$/.test(a.path)?`<img src="${esc(a.url)}" alt="${esc(a.path)}">`:/\.mp4$/.test(a.path)?`<video controls preload="metadata" src="${esc(a.url)}"></video>`:/\.mp3$/.test(a.path)?`<audio controls preload="metadata" src="${esc(a.url)}"></audio>`:''}</article>`).join('') : '<div class="empty-assets">Chưa có ảnh, audio hoặc video trong dự án.<br>Tệp sẽ xuất hiện ở đây khi có trên đĩa.</div>';
  $('scene-save-state').textContent = 'Đã đọc từ đĩa'; dirty = false;
}
async function load() { state = await api('/api/state'); render(); }
async function action(button, job) {
  if (button.disabled) return; button.disabled = true;
  try { await job(); } catch(error) { notice(error.message,true); }
  finally { button.disabled = false; }
}
async function save(file, content, button) {
  await action(button, async()=>{
    const result = await api('/api/save', {file,content});
    // Read the exact target back before showing success.
    const fresh = await api('/api/state');
    const actual = file==='script.md'?fresh.script:file==='style.md'?fresh.style:null;
    if (actual!==null && actual!==content) throw new Error('Đọc lại không khớp nội dung đã lưu');
    state = fresh; render(); notice(result.message);
  });
}
function csvText() { return fields.join(',')+'\n'+state.scenes.map(s=>fields.map(f=>'"'+s[f].replaceAll('"','""')+'"').join(',')).join('\n')+'\n'; }
fields.forEach(f=>$('field-'+f).addEventListener('input',()=>{
  state.scenes[selected][f] = $('field-'+f).value; dirty=true; $('scene-save-state').textContent='Có thay đổi chưa lưu'; renderTable();
}));
['script-editor','style-editor'].forEach(id=>$(id).addEventListener('input',()=>{dirty=true;}));
$('save-scenes').addEventListener('click',()=>save('scenes.csv',csvText(),$('save-scenes')));
$('save-script').addEventListener('click',()=>save('script.md',$('script-editor').value,$('save-script')));
$('save-style').addEventListener('click',()=>save('style.md',$('style-editor').value,$('save-style')));
$('generate-motion').addEventListener('click',()=>action($('generate-motion'),async()=>{
  if(dirty) throw new Error('Hãy lưu chỉnh sửa trước khi tạo motion prompts.');
  const result=await api('/api/motion',{}); await load(); notice(result.message);
}));
$('reload').addEventListener('click',()=>action($('reload'),async()=>{if(dirty&&!confirm('Bỏ chỉnh sửa chưa lưu và đọc lại từ đĩa?'))return;await load();notice('Đã đọc lại dữ liệu từ đĩa.');}));
const titles={scenes:['Phân cảnh','Biên tập từng khung hình, giữ mạch kể chuyện.'],script:['Kịch bản','Chỉnh lời thoại trực tiếp trong script.md.'],characters:['Nhân vật','Mô tả và ảnh tham chiếu đang có trong dự án.'],style:['Phong cách','Giữ ngôn ngữ hình ảnh đồng nhất qua từng cảnh.'],pipeline:['Quy trình & tệp','Biết bước nào đã có dữ liệu, bước nào chưa tích hợp.']};
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{
  const view=button.dataset.view;
  document.querySelectorAll('.view').forEach(el=>el.hidden=el.id!=='view-'+view);
  document.querySelectorAll('[data-view]').forEach(el=>el.classList.toggle('active',el===button));
  $('view-title').textContent=titles[view][0];$('view-subtitle').textContent=titles[view][1];
}));
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
load().catch(error=>notice(error.message,true));
