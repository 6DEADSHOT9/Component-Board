const $ = id => document.getElementById(id);
let components = [], me = {}, view = 'home', batch = 0, batchIds = [], skipped = new Set(JSON.parse(localStorage.getItem('skipped') || '[]')), onlySkipped = false;
const message = (text = '', error = false) => { $('message').textContent = text; $('message').className = error ? 'error' : ''; };
const escape = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, data) {
  const response = await fetch(path, {method: data === undefined ? 'GET' : 'POST', headers: data === undefined ? {} : {'Content-Type': 'application/json'}, body: data === undefined ? undefined : JSON.stringify(data), signal: AbortSignal.timeout(90000)});
  let value;
  try { value = await response.json(); } catch { throw Error('The free server is waking up. Wait 30–60 seconds, then try again.'); }
  if (!response.ok) { const error = Error(value.error || 'Could not save. Try again.'); error.transient = response.status === 503; throw error; }
  return value;
}
function show(id) { for (const name of ['access','onboarding','board','owner-access','paused']) $(name).hidden = name !== id; }
async function load() {
  me = await api('/api/me');
  if (!me.person && !me.owner) { show('onboarding'); return; }
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
function render() {
  show('board');
  $('view-title').textContent = view === 'home' ? 'Included so far' : view === 'owner' ? 'Review results' : 'A few good components.';
  $('view-description').textContent = view === 'home' ? 'The patterns the team has approved, and where they are in the adoption process.' : view === 'owner' ? 'Votes inform the decision. Mark a verified component approved when the team is ready.' : 'Review eight at a time. Look at the upstream design, then tell us whether it belongs in Implicity.';
  $('batch-controls').hidden = view !== 'review'; $('owner-tools').hidden = view !== 'owner';
  let rows = filtered();
  const pages = Math.max(1, Math.ceil(rows.length / 8)); batch = Math.min(batch, pages - 1);
  if (view === 'review') {
    // Keep the current batch stable while votes update filters and progress.
    if (!batchIds.length) batchIds = rows.slice(batch * 8, batch * 8 + 8).map(c => c.id);
    rows = rows.filter(c => batchIds.includes(c.id));
    const reviewed = components.filter(c => c.vote).length;
    $('progress').max = components.length; $('progress').value = reviewed;
    $('progress-label').textContent = `${reviewed} of ${components.length} reviewed`;
    $('batch-number').textContent = `${onlySkipped ? 'Skipped · ' : ''}Batch ${batch + 1} of ${pages}`;
    $('previous').disabled = batch === 0; $('next').disabled = batch + 1 >= pages;
  }
  const groups = Map.groupBy(rows, c => c.registry);
  $('cards').innerHTML = [...groups].map(([registry, cards]) => `<details open><summary>${escape(registry)}<small>${cards.length} ${cards.length === 1 ? 'component' : 'components'}</small></summary><div class="grid">${cards.map(card).join('')}</div></details>`).join('');
  $('empty').hidden = rows.length > 0;
  $('empty').textContent = view === 'home' ? 'No approved components match yet. Review the pilot to help the team choose.' : 'No components match these filters. Try another need or status.';
}
function card(c) {
 const id = escape(c.id), own = c.vote;
 const pictures = c.previews || {};
 return `<article class="card" data-id="${id}"><header><div><h2>${escape(c.name)}</h2><small>${escape(c.need)}</small></div><span class="tag">${escape(c.status)}</span></header>
 ${pictures.light ? `<div class="preview"><img src="${escape(pictures.light)}" alt="${escape(c.name)} in its upstream light appearance" loading="lazy" width="960" height="600"></div><div class="preview-tabs"><button data-preview="light">Light</button><button data-preview="dark">Dark</button>${pictures.interaction ? '<button data-preview="interaction">Interaction</button>' : ''}</div>` : '<p class="muted">Preview pending isolation run.</p>'}
 ${pictures.clip ? `<details><summary>Watch interaction</summary><div class="preview"><video src="${escape(pictures.clip)}" controls preload="none" playsinline aria-label="Upstream component interaction"></video></div></details>` : ''}
 <small>Upstream look; will be ported to Implicity’s design tokens.</small>
 <dl class="facts"><dt>Registry</dt><dd>${escape(c.registry)}</dd><dt>Licence</dt><dd><a href="${escape(c.license.url)}" target="_blank" rel="noreferrer">${escape(c.license.name)} · ${c.license.verified ? 'verified' : 'unverified'}</a></dd><dt>Dependencies</dt><dd>${escape(c.dependencies.join(', ') || 'None declared')}</dd><dt>Added size</dt><dd>${escape(c.addedSize || 'Not measured yet; adoption requires a port measurement')}</dd><dt>Porting effort</dt><dd>${escape(c.portingEffort)}</dd></dl>
 <details><summary>Signals this makes possible</summary><ul class="signals">${c.signals.map(s => `<li><strong>${escape(s.event)}</strong>: ${escape(s.possible)}<br><span class="muted">Integration: ${escape(s.integration)}</span></li>`).join('')}</ul><p class="port">These actions do not prove a preference. Data exists only after integration and consent controls.</p></details>
 <details><summary>Why shortlisted</summary><p class="port">${escape(c.why)}</p><p class="port">Revision ${escape(c.sourceRevision)} · rubric ${escape(JSON.stringify(c.rubric))}</p><a href="${escape(c.addressUrl)}" target="_blank" rel="noreferrer">Registry item source</a></details>
 ${view !== 'home' && me.person ? `<form class="vote-form"><label for="reason-${id}">One-line reason <span class="muted">(optional)</span></label><input id="reason-${id}" name="reason" maxlength="240" value="${escape(own?.reason || '')}"><div class="vote-buttons">${['yes','no','abstain'].map(choice => `<button type="submit" value="${choice}" aria-pressed="${own?.choice === choice}">${choice[0].toUpperCase() + choice.slice(1)}</button>`).join('')}<button type="button" data-skip>Skip</button></div></form>` : ''}
 <p class="results">${own ? `Your vote: ${escape(own.choice)} · ` : 'Not reviewed by you · '}${c.participation} participated${c.totals ? `<br>Yes ${c.totals.yes} · No ${c.totals.no} · Abstain ${c.totals.abstain}` : '<br>Totals appear after your vote.'}</p>
 ${view === 'owner' ? `<label>Status<select data-status>${['review','approved','ported','in the app'].map(s => `<option${c.status === s ? ' selected' : ''}>${s}</option>`).join('')}</select></label>` : ''}</article>`;
}
function handle(fn) { return async event => { event.preventDefault(); const submitter = event.submitter || (event.currentTarget instanceof HTMLButtonElement ? event.currentTarget : null); const label = submitter?.textContent; if(submitter) { submitter.disabled = true; submitter.textContent = 'Saving…'; } try { message(); await fn(event); } catch (error) { message(error.message, true); } finally { if(submitter) { submitter.disabled = false; submitter.textContent = label; } } }; }
$('access-form').onsubmit = handle(async () => { await api('/api/access', {code:$('access-code').value}); await load(); });
$('owner-form').onsubmit = handle(async () => { await api('/api/access', {code:$('owner-code').value, kind:'owner'}); view = 'owner'; await load(); });
$('onboard-form').onsubmit = handle(async () => { await api('/api/onboard', {name:$('name').value, email:$('email').value}); view = 'review'; await load(); });
for (const button of document.querySelectorAll('[data-view]')) button.onclick = handle(async () => { view = button.dataset.view; batch = 0; batchIds = []; onlySkipped = false; if(view === 'owner' && !me.owner) show('owner-access'); else await load(); });
for (const id of ['search','need','registry','status']) $(id).addEventListener(id === 'search' ? 'input' : 'change', () => { batch = 0; batchIds = []; render(); });
for (const [id, delta] of [['previous',-1],['next',1]]) $(id).onclick = () => { batch += delta; batchIds = []; render(); $('batch-controls').scrollIntoView({block:'start'}); };
$('skipped').onclick = () => { onlySkipped = !onlySkipped; batch = 0; batchIds = []; render(); };
$('later').onclick = () => show('paused'); $('resume').onclick = () => render();
$('cards').addEventListener('submit', handle(async event => {
 const c = components.find(c => c.id === event.target.closest('[data-id]').dataset.id);
 await api('/api/vote', {component:c.id, version:c.version, choice:event.submitter.value, reason:event.target.elements.reason.value});
 skipped.delete(c.id); localStorage.setItem('skipped', JSON.stringify([...skipped]));
 await load(); document.querySelector(`[data-id="${c.id}"] button[value="${c.vote?.choice || event.submitter.value}"]`)?.focus({preventScroll:true}); message('Vote saved. You can change it at any time.');
}));
$('cards').addEventListener('click', event => {
 const article = event.target.closest('[data-id]'); if(!article) return;
 const c = components.find(c => c.id === article.dataset.id);
 if(event.target.matches('[data-skip]')) { skipped.add(c.id); localStorage.setItem('skipped', JSON.stringify([...skipped])); article.hidden = true; message('Skipped for now. Use Review skipped to return to it.'); }
 if(event.target.dataset.preview) { const state = event.target.dataset.preview; const img = article.querySelector('.preview img'); img.src = c.previews[state]; img.alt = `${c.name} upstream ${state} appearance`; }
});
$('cards').addEventListener('change', handle(async event => { if(event.target.matches('[data-status]')) { await api('/api/status', {component:event.target.closest('[data-id]').dataset.id, status:event.target.value}); await load(); message('Status saved.'); } }));
$('import').onclick = handle(async () => { const file = $('import-file').files[0]; if(!file) throw Error('Choose a full JSON export first.'); await api('/api/import', JSON.parse(await file.text())); await load(); message('Data restored.'); });
$('delete').onclick = handle(async () => { await api('/api/delete-all', {confirm:$('confirm').value}); location.reload(); });
(async () => {
 try {
  const url = new URL(location.href), invite = url.searchParams.get('invite');
  if(invite) { history.replaceState(null, '', '/'); await api('/api/access', {code:invite}); }
  await load(); message();
 } catch(error) { show('access'); message(error.message, !error.message.includes('invite')); }
})();
