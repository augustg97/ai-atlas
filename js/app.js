/* AI Atlas — engine.
 *
 * The reusable core of a feature-engine time model: one scalar t drives everything,
 * every entity carries a window, cards rewrite themselves for the current time, and
 * the timeline is the table of contents.
 *
 * What to replace when you make this a real project:
 *   - project()      : swap the equirectangular default for the project's real
 *                      projection. If you vendor D3, use d3.geoEqualEarth() etc.
 *                      NOTE: a fixed projection plus a pre-reprojected basemap is
 *                      sharper and cheaper than live reprojection — but then the
 *                      projection constants and the basemap are A MATCHED PAIR.
 *   - drawBase()     : the substrate — basemap image, geometry, fields.
 *   - LAYERS         : the layer table from SCOPE.md §3.
 *
 * What NOT to change without reading Modeling Studio/references/ARCHITECTURE-PATTERNS.md:
 *   - render() is a pure function of state. No per-layer clocks, no accumulated state.
 *   - every entity is drawn through activeAt(); there is one window predicate, not five.
 *   - the card's tier heading. A generic list presented as local is a lie.
 */
'use strict';

const D = window.DATA;                                     // meta.js / eras.js / entities.js
const $ = s => document.querySelector(s);
const svg = $('#map');
const SVGNS = 'http://www.w3.org/2000/svg';

// ------------------------------------------------------------------ state --
const T0 = D.meta.t0, T1 = D.meta.t1, STEP = D.meta.step;
const SPEEDS = D.meta.speeds;                              // units per second

const state = {
  t: T0,
  playing: false,
  speed: 2,
  layers: {},                                              // filled from LAYERS
  selection: null,
};

const LAYERS = D.meta.layers;                              // [{id,label,on}]
LAYERS.forEach(l => { state.layers[l.id] = l.on !== false; });

// ------------------------------------------------------------- projection --
// Equirectangular placeholder. Replace with the project's real projection.
let VIEW = {x: 0, y: 0, w: 1, h: 1};

function project(lon, lat) {
  return [VIEW.x + (lon + 180) / 360 * VIEW.w,
          VIEW.y + (90 - lat) / 180 * VIEW.h];
}

function resize() {
  const r = svg.getBoundingClientRect();
  const s = Math.min(r.width / 360, (r.height - 150) / 180);
  VIEW = {w: 360 * s, h: 180 * s,
          x: (r.width - 360 * s) / 2, y: (r.height - 180 * s) / 2 - 30};
  render();
}

// -------------------------------------------------------------- time model --
/* One window predicate for every entity in the model. If you find yourself writing
   a second one, the schema is wrong, not the predicate. */
function activeAt(e, t) {
  if (e.from != null && t < e.from) return false;
  if (e.to   != null && t > e.to)   return false;
  return true;
}

/* Fade in rather than pop. Used by every layer so the map never flickers.
   An entity that already existed when the model window opened is fully present at t0 —
   otherwise everything inherited from before the start is invisible on load. */
function fadeIn(t, from, span) {
  if (from == null || from <= T0) return 1;
  return Math.max(0, Math.min(1, (t - from) / (span || STEP)));
}

/* Continuous series: [[t, v], …] ascending. One interpolator for all of them. */
function interpSeries(S, t) {
  if (!S || !S.length) return null;
  if (t <= S[0][0]) return S[0][1];
  if (t >= S[S.length - 1][0]) return S[S.length - 1][1];
  for (let i = 1; i < S.length; i++) {
    if (S[i][0] >= t) {
      const [a, av] = S[i - 1], [b, bv] = S[i];
      return av + (bv - av) * (t - a) / (b - a);
    }
  }
  return null;
}

/* Step-valued series: the last entry at or before t. */
function lastLE(S, t) {
  let v = null;
  for (const [tt, vv] of S || []) { if (tt <= t) v = vv; else break; }
  return v;
}

function eraAt(t) {
  return D.eras.find(e => t >= e.from && t < e.to) || D.eras[D.eras.length - 1];
}

// ----------------------------------------------------------------- render --
function render() {
  while (svg.firstChild) svg.removeChild(svg.firstChild);

  drawBase();
  for (const layer of LAYERS) {
    if (!state.layers[layer.id]) continue;
    drawLayer(layer.id);
  }

  updateReadout();
  updateTimeline();
  updateChapters();
  if (state.selection) openCard(state.selection);          // cards rewrite for t
}

function drawBase() {
  // The substrate. Replace with the project's basemap / geometry / field composite.
  const r = el('rect', {x: VIEW.x, y: VIEW.y, width: VIEW.w, height: VIEW.h,
                        fill: 'rgba(255,255,255,.028)', stroke: 'rgba(255,255,255,.09)'});
  svg.appendChild(r);
}

function drawLayer(id) {
  const g = el('g', {'data-layer': id});
  for (const e of D.entities) {
    if (e.layer !== id || !activeAt(e, state.t)) continue;
    const [x, y] = project(e.lon, e.lat);
    const a = fadeIn(state.t, e.from, STEP * 2);
    const mk = el('g', {class: 'mk', opacity: a});
    mk.appendChild(el('circle', {cx: x, cy: y, r: 4,
                                 fill: e.color || 'var(--accent2)',
                                 stroke: 'rgba(0,0,0,.55)', 'stroke-width': 1}));
    mk.appendChild(el('text', {x: x + 7, y: y + 3.5, class: 'mklab'}, e.name));
    mk.addEventListener('click', ev => { ev.stopPropagation(); select(e); });
    g.appendChild(mk);
  }
  svg.appendChild(g);
}

function el(tag, attrs, text) {
  const n = document.createElementNS(SVGNS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (text != null) n.textContent = text;
  return n;
}

// ------------------------------------------------------------------ cards --
/* Time-aware prose. "California's card in 1849 is not California's card in 1950."
   The eras array must tile the entity's life with no gaps — audit it. */
function eraTextFor(o, t) {
  if (!o.eras || !o.eras.length) return o.text || '';
  const m = o.eras.find(e => t >= e.from && t < e.to);
  return m ? m.text : (t < o.eras[0].from ? o.eras[0] : o.eras[o.eras.length - 1]).text;
}

function eraSpanFor(o, t) {
  if (!o.eras || !o.eras.length) return '';
  const m = o.eras.find(e => t >= e.from && t < e.to) || o.eras[o.eras.length - 1];
  return `Describing ${fmtT(m.from)} – ${fmtT(m.to)}`;
}

function select(e) { state.selection = e; openCard(e); }

function openCard(o) {
  $('#infoTag').textContent  = o.kind || o.layer || '';
  $('#infoName').textContent = o.name;
  $('#infoRows').innerHTML   = (o.facts || [])
    .map(([k, v]) => `<div class="row"><b>${esc(k)}</b><span>${esc(v)}</span></div>`).join('');
  $('#infoDesc').innerHTML   = esc(eraTextFor(o, state.t)) + extraSections(o);
  $('#infoSpan').textContent = eraSpanFor(o, state.t);
  $('#infoCite').innerHTML   = (o.sources || []).length
    ? 'Sources: ' + o.sources.map(esc).join(' · ') : '';
  $('#info').classList.remove('hidden');
}

/* The three-tier fallback, with the heading naming which tier the reader is seeing.
 *   1. curated exception — the model must never speak over it
 *   2. model-derived for this place and time
 *   3. the generic list, UNDER A HEADING THAT SAYS IT IS GENERIC
 * The heading is the honesty mechanism. Do not remove it. */
function extraSections(o) {
  const parts = [];
  if (o.curated) {
    parts.push(tier('Recorded here', false) + list(o.curated));
  } else {
    const derived = deriveFor(o, state.t);
    if (derived && derived.length) parts.push(tier('Typical of this region', false) + list(derived));
    else {
      const generic = D.meta.genericAt ? D.meta.genericAt(state.t) : null;
      if (generic && generic.length)
        parts.push(tier('Typical of this period worldwide', true) + list(generic));
    }
  }
  return parts.join('');
}

function deriveFor(/* o, t */) { return null; }   // wire the research model in here

const tier = (label, generic) =>
  `<div class="tier${generic ? ' generic' : ''}">${esc(label)}</div>`;
const list = items => '<div>' + items.map(esc).join(' · ') + '</div>';

// --------------------------------------------------------------- readout --
function fmtT(t) { return D.meta.fmt ? D.meta.fmt(t) : String(Math.round(t)); }

function updateReadout() {
  $('#tBig').textContent = fmtT(state.t);
  const era = eraAt(state.t);
  $('#eraName').textContent = era ? era.name : '';
  $('#statsBlock').innerHTML = (D.meta.stats || []).map(s => {
    const v = s.series ? interpSeries(s.series, state.t) : s.at(state.t);
    return `<div class="statline"><b>${esc(s.label)}</b>${esc(s.fmt ? s.fmt(v) : v)}</div>`;
  }).join('');
}

// -------------------------------------------------------------- timeline --
const xOf = t => (t - T0) / (T1 - T0);

function buildTimeline() {
  const band = $('#eraBand'), labs = $('#eraLabels'), dots = $('#eventDots');
  band.innerHTML = labs.innerHTML = dots.innerHTML = '';
  D.eras.forEach((e, i) => {
    const d = document.createElement('div');
    d.style.left = xOf(e.from) * 100 + '%';
    d.style.width = (xOf(e.to) - xOf(e.from)) * 100 + '%';
    d.style.background = i % 2 ? 'rgba(224,164,88,.20)' : 'rgba(90,169,230,.18)';
    d.title = e.name;
    d.onclick = () => seek(e.from);
    band.appendChild(d);
    const s = document.createElement('span');
    s.style.left = (xOf(e.from) + xOf(e.to)) / 2 * 100 + '%';
    s.textContent = e.name;
    labs.appendChild(s);
  });
  (D.events || []).forEach(ev => {
    const d = document.createElement('div');
    d.style.left = xOf(ev.t) * 100 + '%';
    d.title = `${fmtT(ev.t)} — ${ev.name}`;
    d.onclick = e => { e.stopPropagation(); seek(ev.t); };
    dots.appendChild(d);
  });
}

function updateTimeline() {
  const f = xOf(state.t) * 100;
  $('#trackFill').style.width = f + '%';
  $('#thumb').style.left = f + '%';
  const near = (D.events || []).filter(e => Math.abs(e.t - state.t) <= STEP);
  $('#eventReadout').textContent = near.length ? near[0].name : '';
}

function buildChapters() {
  $('#chapterList').innerHTML = D.eras
    .map((e, i) => `<div data-i="${i}">${esc(e.name)}</div>`).join('');
  $('#chapterList').querySelectorAll('div').forEach(d =>
    d.onclick = () => seek(D.eras[+d.dataset.i].from));
}

function updateChapters() {
  const era = eraAt(state.t);
  $('#chapterList').querySelectorAll('div').forEach((d, i) =>
    d.classList.toggle('on', D.eras[i] === era));
}

// -------------------------------------------------------------- playback --
let raf = null, last = 0;

function tick(ts) {
  if (!state.playing) return;
  if (last) state.t = Math.min(T1, state.t + SPEEDS[state.speed] * (ts - last) / 1000);
  last = ts;
  if (state.t >= T1) pause();
  render(); syncHash();
  raf = requestAnimationFrame(tick);
}

function play()  { state.playing = true;  last = 0; $('#playIcon').textContent = '❚❚';
                   raf = requestAnimationFrame(tick); }
function pause() { state.playing = false; $('#playIcon').textContent = '▶';
                   if (raf) cancelAnimationFrame(raf); }

function seek(t) {
  state.t = Math.max(T0, Math.min(T1, t));
  render(); syncHash();
}

function jumpEvent(dir) {
  const es = (D.events || []).map(e => e.t).sort((a, b) => a - b);
  const next = dir > 0 ? es.find(t => t > state.t + 1e-6)
                       : [...es].reverse().find(t => t < state.t - 1e-6);
  if (next != null) seek(next);
}

// ------------------------------------------------------------------ hash --
/* The URL carries t, so every state is shareable. Four lines, always worth it. */
function syncHash() {
  history.replaceState(null, '', '#t=' + Math.round(state.t));
}
function readHash() {
  const m = /[#&]t=(-?\d+(?:\.\d+)?)/.exec(location.hash);
  if (m) state.t = Math.max(T0, Math.min(T1, parseFloat(m[1])));
}

// ------------------------------------------------------------------ wire --
function buildToggles() {
  $('#layerToggles').innerHTML = LAYERS.map(l =>
    `<label class="tog"><span>${esc(l.label)}</span>` +
    `<input type="checkbox" data-id="${l.id}"${state.layers[l.id] ? ' checked' : ''}><i></i></label>`
  ).join('');
  $('#layerToggles').querySelectorAll('input').forEach(i =>
    i.onchange = () => { state.layers[i.dataset.id] = i.checked; render(); });
}

function wire() {
  $('#playBtn').onclick  = () => state.playing ? pause() : play();
  $('#stepBack').onclick = () => seek(state.t - STEP);
  $('#stepFwd').onclick  = () => seek(state.t + STEP);
  $('#prevEvt').onclick  = () => jumpEvent(-1);
  $('#nextEvt').onclick  = () => jumpEvent(1);
  $('#speed').oninput = e => {
    state.speed = +e.target.value;
    $('#speedVal').textContent = SPEEDS[state.speed] + ' ' + D.meta.unit + '/s';
  };
  $('#speed').oninput({target: $('#speed')});

  const track = $('#track');
  const at = e => T0 + (e.clientX - track.getBoundingClientRect().left)
                      / track.clientWidth * (T1 - T0);
  let dragging = false;
  track.onpointerdown = e => { dragging = true; track.setPointerCapture(e.pointerId);
                               pause(); seek(at(e)); };
  track.onpointermove = e => { if (dragging) seek(at(e)); };
  track.onpointerup   = () => { dragging = false; };

  $('#infoClose').onclick  = () => { state.selection = null; $('#info').classList.add('hidden'); };
  $('#aboutBtn').onclick   = () => $('#about').classList.remove('hidden');
  $('#aboutClose').onclick = () => $('#about').classList.add('hidden');
  $('#chaptersChev').onclick = () => {
    const l = $('#chapterList');
    l.style.display = l.style.display === 'none' ? '' : 'none';
  };
  svg.addEventListener('click', () => {
    state.selection = null; $('#info').classList.add('hidden');
  });

  addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT') return;
    if (e.code === 'Space') { e.preventDefault(); state.playing ? pause() : play(); }
    else if (e.key === 'ArrowLeft')  e.shiftKey ? jumpEvent(-1) : seek(state.t - STEP);
    else if (e.key === 'ArrowRight') e.shiftKey ? jumpEvent(1)  : seek(state.t + STEP);
    else if (e.key === 'Escape') { state.selection = null; $('#info').classList.add('hidden'); }
  });

  addEventListener('resize', resize);
  addEventListener('hashchange', () => { readHash(); render(); });
}

const esc = s => String(s == null ? '' : s)
  .replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

// ------------------------------------------------------------------ boot --
readHash();
buildTimeline();
buildChapters();
buildToggles();
wire();
resize();

// Console handle, so verification is scriptable: APP.seek(1848), APP.state, APP.render().
window.APP = {state, seek, play, pause, render, project, activeAt, interpSeries, LAYERS};
