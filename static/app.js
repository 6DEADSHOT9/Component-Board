const $ = id => document.getElementById(id);
let components = [], me = {}, view = 'home', batch = 0, batchIds = [], skipped = new Set(JSON.parse(localStorage.getItem('skipped') || '[]')), onlySkipped = false;
let reviewMode = 'swipe', reviewIndex = 0, undoStack = [], previewIndex = 0;
const message = (text = '', error = false) => { $('message').textContent = text; $('message').className = error ? 'error' : ''; };
const escape = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, data, attempt = 0) {
  const response = await fetch(path, {method: data === undefined ? 'GET' : 'POST', headers: data === undefined ? {} : {'Content-Type': 'application/json'}, body: data === undefined ? undefined : JSON.stringify(data), signal: AbortSignal.timeout(90000)});
  if (response.status === 503 && data === undefined && attempt < 3) { message('The free server is waking up. Your saved reviews are retained; reconnecting…'); await new Promise(resolve => setTimeout(resolve, 4000)); return api(path, data, attempt + 1); }
  let value;
  try { value = await response.json(); } catch { throw Error('The free server is waking up. Wait 30–60 seconds, then try again.'); }
  if (!response.ok) { const error = Error(value.error || 'Could not save. Try again.'); error.transient = response.status === 503; throw error; }
  return value;
}
function show(id) { for (const name of ['access','onboarding','board','owner-access','paused']) $(name).hidden = name !== id; }
async function load() {
  me = await api('/api/me');
  if (!me.person && (!me.owner || view === 'review')) { show('onboarding'); return; }
  const data = await api('/api/components'); components = data.components;
  $('participation').textContent = `${data.participants} ${data.participants === 1 ? 'teammate' : 'teammates'} participating`;
  for (const [id, values] of [['need', [...new Set(components.map(c => c.need))]], ['registry', [...new Set(components.map(c => c.registry))]]]) {
    const previous = $(id).value;
    $(id).innerHTML = `<option value="">All ${id === 'need' ? 'needs' : 'registries'}</option>` + values.sort().map(v => `<option>${escape(v)}</option>`).join('');
    $(id).value = previous;
  }
  $('expiry').hidden = !me.expiryWarning; $('expiry').textContent = me.expiryWarning || '';
  render();
}
function filtered() {
  const q = $('search').value.toLowerCase();
  return components.filter(c => (view !== 'home' || c.status !== 'review') && (!q || `${c.name} ${c.registry}`.toLowerCase().includes(q)) && (!$('need').value || c.need === $('need').value) && (!$('registry').value || c.registry === $('registry').value) && (!$('status').value || ($('status').value === 'reviewed' ? c.vote : $('status').value === 'unreviewed' ? !c.vote : c.status === $('status').value)) && (!onlySkipped || skipped.has(c.id)));
}
function reviewRows() { return filtered().sort((a,b) => a.registry.localeCompare(b.registry) || a.name.localeCompare(b.name)); }
function render() {
  show('board');
  $('view-title').textContent = view === 'home' ? 'Included so far' : view === 'owner' ? 'Review results' : 'A few good components.';
  $('view-description').textContent = view === 'home' ? 'The patterns the team has approved, and where they are in the adoption process.' : view === 'owner' ? 'Votes inform the decision. Mark a verified component approved when the team is ready.' : 'One component at a time. Look at the upstream design, then tell us whether it belongs in Implicity.';
  $('batch-controls').hidden = view !== 'review'; $('owner-tools').hidden = view !== 'owner';
  $('filters').hidden = view === 'review' && reviewMode === 'swipe';
  if (view === 'review' && reviewMode === 'swipe') { renderSwipe(); return; }
  let rows = filtered(); const pages = Math.max(1, Math.ceil(rows.length / 8)); batch = Math.min(batch, pages - 1);
  if (view === 'review') {
    if (!batchIds.length) batchIds = rows.slice(batch * 8, batch * 8 + 8).map(c => c.id);
    rows = rows.filter(c => batchIds.includes(c.id));
    $('progress').max = components.length; $('progress').value = components.filter(c => c.vote).length;
    $('progress-label').textContent = `${components.filter(c => c.vote).length} of ${components.length} reviewed`;
    $('batch-number').textContent = `${onlySkipped ? 'Skipped · ' : ''}Batch ${batch + 1} of ${pages}`;
    $('previous').disabled = batch === 0; $('next').disabled = batch + 1 >= pages;
  }
  const groups = Map.groupBy(rows, c => c.registry);
  $('cards').innerHTML = [...groups].map(([registry, cards]) => `<details open><summary>${escape(registry)}<small>${cards.length} ${cards.length === 1 ? 'component' : 'components'}</small></summary><div class="grid">${cards.map(card).join('')}</div></details>`).join('');
  $('empty').hidden = rows.length > 0;
  $('empty').textContent = view === 'home' ? 'No approved components match yet. Review the pilot to help the team choose.' : 'No components match these filters. Try another need or status.';
}
function renderSwipe() {
  const rows = reviewRows(), current = rows[reviewIndex];
  $('progress').max = rows.length || 1; $('progress').value = Math.min(reviewIndex, rows.length);
  $('progress-label').textContent = `${Math.min(reviewIndex, rows.length)} of ${rows.length}`;
  $('batch-number').textContent = 'One at a time'; $('previous').disabled = true; $('next').disabled = true;
  $('cards').innerHTML = current ? swipeCard(current, rows) : `<section class="review-done"><h2>${rows.length ? 'You’re all caught up.' : 'No components match these filters.'}</h2><p>${rows.length ? 'You can review your skipped cards or switch to the list view.' : 'Adjust the filters or search to see components.'}</p></section>`;
  $('empty').hidden = true;
  $('undo').disabled = !undoStack.length;
}
function swipeCard(c, rows) {
  const id=escape(c.id), p=c.previews||{}, own=c.vote;
  const group=rows.filter(x=>x.registry===c.registry), position=group.findIndex(x=>x.id===c.id)+1;
  const slides=[['light',p.light],['dark',p.dark],p.clip?['clip',p.clip]:['interaction',p.interaction]].filter(([,src])=>src);
  previewIndex=Math.min(previewIndex,slides.length-1);
  const [kind,src]=slides[previewIndex]||[];
  const preview=kind==='clip'?`<video src="${escape(src)}" controls preload="none" playsinline aria-label="${escape(c.name)} interaction clip"></video>`:src?`<img src="${escape(src)}" alt="${escape(c.name)} upstream ${kind} appearance" width="960" height="600">`:'<p class="muted">Preview pending isolation run.</p>';
  return `<article class="card swipe-card" data-id="${id}"><div class="swipe-head"><div><p class="repository">Repository: ${escape(c.registry)} · ${position} of ${group.length}</p><h2>${escape(c.name)}</h2><p class="need">${escape(c.need)}</p></div><button class="details-button" data-details aria-label="Details for ${escape(c.name)}">Details <span>(I)</span></button></div>
  <small>Upstream look; will be ported to Implicity’s design tokens.</small><div class="swipe-preview" data-swipe-area>${preview}</div><div class="carousel-controls" aria-label="Preview carousel"><button data-slide="-1" aria-label="Previous preview" ${previewIndex===0?'disabled':''}>‹</button><span>${kind?`${kind==='clip'?'Interaction clip':kind[0].toUpperCase()+kind.slice(1)} · ${previewIndex+1} of ${slides.length}`:'No preview'} </span><button data-slide="1" aria-label="Next preview" ${previewIndex>=slides.length-1?'disabled':''}>›</button></div>
  ${own?`<p class="results">Your vote: ${escape(own.choice)} · ${c.participation} participated${c.totals?` · Yes ${c.totals.yes}, No ${c.totals.no}, Abstain ${c.totals.abstain}`:''}</p>`:''}
  <div class="swipe-actions"><button class="vote-no" data-vote="no" aria-label="No, reject ${escape(c.name)}">No</button><button class="skip-vote" data-vote="abstain" aria-label="Abstain on ${escape(c.name)}">Abstain</button><button class="vote-yes" data-vote="yes" aria-label="Yes, accept ${escape(c.name)}">Yes</button></div>
  <form class="reason-step" hidden><label for="no-reason">Why no? <span class="muted">Optional, one line</span></label><input id="no-reason" maxlength="240" aria-label="Optional reason for voting no"><div><button class="primary" type="submit">Save No vote</button><button type="button" data-no-skip>Skip reason</button></div></form></article>
  <dialog id="details-drawer" class="details-drawer" aria-labelledby="drawer-title"><div class="drawer-head"><h2 id="drawer-title">${escape(c.name)} details</h2><button data-close-details aria-label="Close details">Close</button></div><dl class="facts"><dt>Repository</dt><dd>${escape(c.registry)}</dd><dt>Licence</dt><dd><a href="${escape(c.license.url)}" target="_blank" rel="noreferrer">${escape(c.license.name)} · ${c.license.verified?'verified':'unverified'}</a></dd><dt>Dependencies</dt><dd>${escape(c.dependencies.join(', ')||'None declared')}</dd><dt>Size</dt><dd>${escape(c.addedSize||'Not measured yet')}</dd><dt>Porting effort</dt><dd>${escape(c.portingEffort)}</dd><dt>Signals it enables</dt><dd><ul>${c.signals.map(s=>`<li><strong>${escape(s.event)}</strong>: ${escape(s.possible)} <span class="muted">Integration: ${escape(s.integration)}</span></li>`).join('')}</ul><p class="muted">These actions do not prove a preference. Data exists only after integration and consent controls.</p></dd><dt>Why shortlisted</dt><dd>${escape(c.why)}<p><a href="${escape(c.addressUrl)}" target="_blank" rel="noreferrer">Registry item source</a></p></dd></dl></dialog>`;
}
function card(c) {
 const id = escape(c.id), own = c.vote;
 const pictures = c.previews || {};
 return `<article class="card" data-id="${id}"><header><div><h2>${escape(c.name)}</h2><small>${escape(c.need)}</small></div><span class="tag">${escape(c.status)}</span></header>
 ${pictures.light ? `<div class="preview"><a class="preview-full" target="_blank" rel="noreferrer" href="${escape(pictures.light)}"><img src="${escape(pictures.light)}" alt="${escape(c.name)} in its upstream light appearance" loading="lazy" width="960" height="600"></a></div><div class="preview-tabs"><button data-preview="light">Light</button><button data-preview="dark">Dark</button>${pictures.interaction ? '<button data-preview="interaction">Interaction</button>' : ''}</div>` : '<p class="muted">Preview pending isolation run.</p>'}
 ${pictures.clip ? `<details><summary>Watch interaction</summary><div class="preview"><video src="${escape(pictures.clip)}" controls preload="none" playsinline aria-label="Upstream component interaction"></video></div></details>` : ''}
 <small>Upstream look; will be ported to Implicity’s design tokens.</small>
 <dl class="facts"><dt>Registry</dt><dd>${escape(c.registry)}</dd><dt>Licence</dt><dd><a href="${escape(c.license.url)}" target="_blank" rel="noreferrer">${escape(c.license.name)} · ${c.license.verified ? 'verified' : 'unverified'}</a></dd><dt>Dependencies</dt><dd>${escape(c.dependencies.join(', ') || 'None declared')}</dd><dt>Added size</dt><dd>${escape(c.addedSize || 'Not measured yet; adoption requires a port measurement')}</dd><dt>Porting effort</dt><dd>${escape(c.portingEffort)}</dd></dl>
 <details><summary>Signals this makes possible</summary><ul class="signals">${c.signals.map(s => `<li><strong>${escape(s.event)}</strong>: ${escape(s.possible)}<br><span class="muted">Integration: ${escape(s.integration)}</span></li>`).join('')}</ul><p class="port">These actions do not prove a preference. Data exists only after integration and consent controls.</p></details>
 <details><summary>Why shortlisted</summary><p class="port">${escape(c.why)}</p><p class="port">Revision ${escape(c.sourceRevision)} · rubric ${escape(JSON.stringify(c.rubric))}</p><a href="${escape(c.addressUrl)}" target="_blank" rel="noreferrer">Registry item source</a></details>
 ${view !== 'home' && me.person ? `<form class="vote-form"><label for="reason-${id}">One-line reason <span class="muted">(optional)</span></label><input id="reason-${id}" name="reason" maxlength="240" value="${escape(own?.reason || '')}"><div class="vote-buttons">${['yes','no','abstain'].map(choice => `<button type="submit" value="${choice}" aria-pressed="${own?.choice === choice}">${choice[0].toUpperCase() + choice.slice(1)}</button>`).join('')}<button type="button" data-skip>Skip</button></div></form>` : ''}
 <p class="results">${own ? `Your vote: ${escape(own.choice)} · ` : 'Not reviewed by you · '}${c.participation} participated${c.totals ? `<br>Yes ${c.totals.yes} · No ${c.totals.no} · Abstain ${c.totals.abstain}` : '<br>Totals appear after your vote.'}</p>
 ${view === 'owner' ? `<details><summary>Individual reviews (${c.participation})</summary>${(c.reviews || []).map(r => `<p class="port"><strong>${escape(r.name)} · ${escape(r.choice)}</strong><br>${escape(r.reason || 'No reason added')}</p>`).join('') || '<p class="port">No reviews yet.</p>'}</details><label>Status<select data-status>${['review','approved','ported','in the app'].map(s => `<option${c.status === s ? ' selected' : ''}>${s}</option>`).join('')}</select></label>` : ''}</article>`;
}
function handle(fn) { return async event => { event.preventDefault(); const submitter = event.submitter || (event.currentTarget instanceof HTMLButtonElement ? event.currentTarget : null); const label = submitter?.textContent; if(submitter) { submitter.disabled = true; submitter.textContent = 'Saving…'; } try { message(); event.target.querySelector?.('.form-error')?.remove(); await fn(event); } catch (error) { message(error.message, true); if(event.target instanceof HTMLFormElement) { const note = document.createElement('p'); note.className = 'form-error danger'; note.setAttribute('role','alert'); note.textContent = error.message; event.target.append(note); } } finally { if(submitter) { submitter.disabled = false; submitter.textContent = label; } } }; }
$('access-form').onsubmit = handle(async () => { await api('/api/access', {code:$('access-code').value}); await load(); });
$('owner-form').onsubmit = handle(async () => { await api('/api/access', {code:$('owner-code').value, kind:'owner'}); view = 'owner'; await load(); });
$('onboard-form').onsubmit = handle(async () => { await api('/api/onboard', {name:$('name').value, email:$('email').value}); view = 'review'; await load(); });
for (const button of document.querySelectorAll('[data-view]')) button.onclick = handle(async () => { view = button.dataset.view; batch = 0; batchIds = []; onlySkipped = false; reviewIndex=0; reviewMode='swipe'; if(view === 'owner' && !me.owner) show('owner-access'); else await load(); });
for (const id of ['search','need','registry','status']) $(id).addEventListener(id === 'search' ? 'input' : 'change', () => { batch = 0; batchIds = []; if(view==='review')reviewIndex=0; render(); });
for (const [id, delta] of [['previous',-1],['next',1]]) $(id).onclick = () => { if(view==='review'&&reviewMode==='swipe')return; batch += delta; batchIds = []; render(); $('batch-controls').scrollIntoView({block:'start'}); };
$('skipped').onclick = () => { onlySkipped = !onlySkipped; batch = 0; batchIds = []; reviewIndex=0; $('skipped').textContent=onlySkipped?'All components':'Review skipped'; render(); };
$('list-view').onclick = () => { reviewMode=reviewMode==='swipe'?'list':'swipe'; reviewIndex=0; batchIds=[]; $('list-view').textContent=reviewMode==='swipe'?'List view':'Swipe review'; render(); };
$('undo').onclick=handle(async()=>{const last=undoStack.at(-1);if(!last)return;await api('/api/vote/undo',{component:last.component,version:last.version,choice:last.choice,reason:last.reason});undoStack.pop();reviewIndex=Math.max(0,last.index);await load();$('undo').disabled=!undoStack.length;message('Last vote undone.');});
$('later').onclick = () => show('paused'); $('resume').onclick = () => render();
$('cards').addEventListener('submit', handle(async event => {
 if(event.target.matches('.reason-step')) { const article=event.target.closest('[data-id]'); await saveSwipeVote(article,'no',$('no-reason').value); return; }
 const c = components.find(c => c.id === event.target.closest('[data-id]').dataset.id);
 await api('/api/vote', {component:c.id, version:c.version, choice:event.submitter.value, reason:event.target.elements.reason.value});
 skipped.delete(c.id); localStorage.setItem('skipped', JSON.stringify([...skipped])); await load(); document.querySelector(`[data-id="${c.id}"] button[value="${event.submitter.value}"]`)?.focus({preventScroll:true}); message('Vote saved. You can change it at any time.');
}));
async function saveSwipeVote(article,choice,reason='') { const c=components.find(x=>x.id===article.dataset.id);undoStack.push({component:c.id,version:c.version,choice:c.vote?.choice??null,reason:c.vote?.reason??'',index:reviewIndex});await api('/api/vote',{component:c.id,version:c.version,choice,reason});skipped.delete(c.id);localStorage.setItem('skipped',JSON.stringify([...skipped]));reviewIndex++;await load();$('undo').disabled=false;announceCard(); }
function skipCurrent(){const c=reviewRows()[reviewIndex];if(!c)return;skipped.add(c.id);localStorage.setItem('skipped',JSON.stringify([...skipped]));reviewIndex++;render();announceCard();}
function announceCard(){const c=reviewRows()[reviewIndex];$('message').textContent=c?`Next component: ${c.name}. ${c.need}. Repository ${c.registry}.`:'Review complete. You can undo your last vote.';}
$('cards').addEventListener('click', event => {
 if(event.target.matches('[data-close-details]')) { $('details-drawer').close(); return; }
 const article = event.target.closest('[data-id]'); if(!article) return;
 const c = components.find(c => c.id === article.dataset.id);
 if(event.target.matches('[data-skip]')) { skipped.add(c.id); localStorage.setItem('skipped', JSON.stringify([...skipped])); article.hidden = true; message('Skipped for now. Use Review skipped to return to it.'); }
 if(event.target.dataset.preview) { const state = event.target.dataset.preview; const img = article.querySelector('.preview img'); img.src = c.previews[state]; article.querySelector('.preview-full').href = c.previews[state]; img.alt = `${c.name} upstream ${state} appearance`; }
 if(event.target.matches('[data-vote="no"]')) { event.target.closest('.swipe-card').querySelector('.reason-step').hidden=false; $('no-reason').focus(); }
 if(event.target.matches('[data-vote="yes"],[data-vote="abstain"]')) handle(()=>saveSwipeVote(article,event.target.dataset.vote))({preventDefault(){},target:event.target});
 if(event.target.matches('[data-no-skip]')) saveSwipeVote(article,'no').catch(error=>message(error.message,true));
 if(event.target.matches('[data-details]')) $('details-drawer').showModal();
 if(event.target.matches('[data-slide]')) {previewIndex=Math.max(0,Math.min((c.previews.clip?2:1),previewIndex+Number(event.target.dataset.slide)));render();}
});
$('cards').addEventListener('change', handle(async event => { if(event.target.matches('[data-status]')) { await api('/api/status', {component:event.target.closest('[data-id]').dataset.id, version:components.find(c => c.id === event.target.closest('[data-id]').dataset.id).version, status:event.target.value}); await load(); message('Status saved.'); } }));
let pointerStart=null;
$('cards').addEventListener('pointerdown',e=>{if(view!=='review'||reviewMode!=='swipe'||!e.target.closest('.swipe-preview'))return;pointerStart={x:e.clientX,y:e.clientY,article:e.target.closest('.swipe-card')};});
$('cards').addEventListener('pointerup',e=>{if(!pointerStart)return;const dx=e.clientX-pointerStart.x,dy=e.clientY-pointerStart.y,article=pointerStart.article;pointerStart=null;if(Math.abs(dx)<70||Math.abs(dx)<Math.abs(dy)*1.2)return;const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;if(!reduce){article.style.transition='transform 160ms ease-out';article.style.transform=`translateX(${Math.sign(dx)*100}vw) rotate(${Math.sign(dx)*5}deg)`;}if(reduce){article.classList.add('swipe-crossfade');setTimeout(()=>saveSwipeVote(article,dx<0?'no':'yes'),120);}else setTimeout(()=>saveSwipeVote(article,dx<0?'no':'yes'),160);});
$('cards').addEventListener('pointermove',e=>{if(!pointerStart||matchMedia('(prefers-reduced-motion: reduce)').matches)return;const dx=e.clientX-pointerStart.x,dy=e.clientY-pointerStart.y;if(Math.abs(dx)>Math.abs(dy))pointerStart.article.style.transform=`translateX(${dx}px) rotate(${dx/24}deg)`;});
$('cards').addEventListener('pointercancel',()=>{pointerStart=null;const card=document.querySelector('.swipe-card');if(card)card.style.transform='';});
document.addEventListener('keydown',e=>{if(view!=='review'||reviewMode!=='swipe'||$('details-drawer').open||['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName))return;if(e.key==='i'||e.key==='I'){document.querySelector('[data-details]')?.click();return;}if(['ArrowLeft','ArrowRight','ArrowDown'].includes(e.key)){e.preventDefault();if(e.key==='ArrowDown'){skipCurrent();return;}const choice=e.key==='ArrowLeft'?'no':'yes';document.querySelector(`[data-vote="${choice}"]`)?.click();}});
$('import').onclick = handle(async () => { const file = $('import-file').files[0]; if(!file) throw Error('Choose a full JSON export first.'); await api('/api/import', JSON.parse(await file.text())); await load(); message('Data restored.'); });
$('delete').onclick = handle(async () => { await api('/api/delete-all', {confirm:$('confirm').value}); location.reload(); });
(async () => {
 try {
  const url = new URL(location.href), invite = url.searchParams.get('invite');
  if(invite) { history.replaceState(null, '', '/'); await api('/api/access', {code:invite}); }
  await load(); message();
 } catch(error) { show('access'); message(error.message, !error.message.includes('invite')); }
})();
