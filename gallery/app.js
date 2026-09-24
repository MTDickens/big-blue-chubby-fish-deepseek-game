// 蓝色大肥鱼 角色展厅: character select, animations, expressions, three-view, lineup and the EP1 ending recreation.
// Deep links: #m=solo|three|lineup|hero&c=<character id>&a=<animation>&bg=<stage>  (+ &still=<seconds> for stills)
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { toonify } from './toon.js';
import { Stage, STAGES } from './stage.js';
import { CHARACTERS, LINEUP, EXPR_LABELS, EXPR_GROUPS } from './catalog.js';

const BASE = window.GALLERY_BASE ?? '';
const $ = (s, el = document) => el.querySelector(s);
const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') el.className = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null) el.setAttribute(k, v);
  }
  for (const c of kids.flat()) if (c !== null && c !== undefined) el.append(c);
  return el;
};
const byId = Object.fromEntries(CHARACTERS.map((c) => [c.id, c]));
const hash = new URLSearchParams(location.hash.slice(1));
const STILL = hash.has('still') ? +hash.get('still') : null;
const MODES = [['solo', '角色'], ['three', '三视图'], ['lineup', '全员合影'], ['hero', '片尾复刻']];

const state = {
  mode: MODES.some(([m]) => m === hash.get('m')) ? hash.get('m') : 'solo',
  char: byId[hash.get('c')] ? hash.get('c') : 'bluefish',
  anim: hash.get('a') || null,
  bg: STAGES[hash.get('bg')] ? hash.get('bg') : null,
  turn: false,
  expr: null,
};

// ---------- renderer / scene ----------
const canvas = $('#view');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: STILL !== null });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, innerWidth < 760 ? 1.75 : 2));
renderer.toneMapping = THREE.NeutralToneMapping;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
const scene = new THREE.Scene();
const stage = new Stage(renderer, scene, { base: BASE });
const world = new THREE.Group();
scene.add(world);
const camera = new THREE.PerspectiveCamera(30, 1, 0.02, 200);
const triCams = [0, 90, 180].map(() => new THREE.PerspectiveCamera(18, 1, 0.02, 200));
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = STILL === null;
controls.enablePan = false;
controls.maxPolarAngle = THREE.MathUtils.degToRad(97);
controls.autoRotateSpeed = 1.6;
const timer = new THREE.Timer();

// ---------- assets ----------
const loader = new GLTFLoader();
const gltfCache = new Map();
const progress = new Map();
const EYE_TRACK = /^eye[LR]\./;   // three strips dots from node names: eye.L -> eyeL

function loadGLB(file) {
  if (!gltfCache.has(file)) {
    const p = loader
      .loadAsync(BASE + file, (e) => {
        progress.set(file, [e.loaded, e.total || e.loaded]);
        showProgress();
      })
      .then((g) => {
        toonify(g.scene, { outlines: false });
        // Blinks layer on top of every other clip, so body clips must not own the eye bones.
        g.clips = new Map();
        for (const c of g.animations) {
          if (c.name === 'blink') g.blink = new THREE.AnimationClip('blink', c.duration, c.tracks.filter((t) => EYE_TRACK.test(t.name)));
          else g.clips.set(c.name, new THREE.AnimationClip(c.name, c.duration, c.tracks.filter((t) => !EYE_TRACK.test(t.name))));
        }
        progress.delete(file);
        showProgress();
        return g;
      });
    p.catch(() => gltfCache.delete(file));
    gltfCache.set(file, p);
  }
  return gltfCache.get(file);
}

function boxOf(obj) {
  obj.updateMatrixWorld(true);
  return new THREE.Box3().setFromObject(obj, true);
}

class Actor {
  constructor(gltf, entry, file) {
    this.gltf = gltf;
    this.entry = entry;
    this.file = file;
    this.root = SkeletonUtils.clone(gltf.scene);
    this.root.updateMatrixWorld(true);
    this.rest = new Map();
    this.bones = new Map();
    this.expr = [];
    this.root.traverse((o) => {
      if (o.isBone) {
        // a bone sharing its name with a mesh (e.g. 'body') gets a numeric suffix from the loader
        const name = o.name.replace(/_\d+$/, '');
        const key = this.bones.has(name) ? o.name : name;
        this.bones.set(key, o);
        this.rest.set(key, o.matrixWorld.clone());
      }
      if (o.name.startsWith('expr_') && !o.parent.name.startsWith('expr_')) this.expr.push(o);
    });
    this.box = boxOf(this.root);
    this.mixer = new THREE.AnimationMixer(this.root);
    this.current = null;
    this.clipName = null;
    this.props = [];
    this.propToken = 0;
    this.blinkIn = 1 + Math.random() * 3;
  }

  play(name, { fade = 0.3, offset = 0, speed = 1 } = {}) {
    const clip = this.gltf.clips.get(name);
    if (!clip) return false;
    const act = this.mixer.clipAction(clip);
    const once = this.entry.once?.includes(name);
    if (this.current === act && !once) return true;
    act.reset();
    act.setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat, Infinity);
    act.clampWhenFinished = once;
    act.timeScale = speed;
    act.time = offset % clip.duration;
    act.play();
    if (this.current && this.current !== act) act.crossFadeFrom(this.current, fade, false);
    this.current = act;
    this.clipName = name;
    return true;
  }

  setExpr(names) {
    if (!this.expr.length || !names) return;
    const on = new Set(names);
    for (const o of this.expr) o.visible = on.has(o.name);
  }

  blink() {
    if (!this.gltf.blink) return;
    const a = this.mixer.clipAction(this.gltf.blink);
    a.reset();
    a.setLoop(THREE.LoopOnce, 1);
    a.play();
  }

  // Props sit where catalog.js says (character space at rest) and then ride their bone through the animation.
  async attach(spec) {
    const token = ++this.propToken;
    this.detach();
    if (!spec) return;
    const g = await loadGLB(spec.file);
    const bone = this.bones.get(spec.bone);
    if (token !== this.propToken || !bone) return;
    const obj = SkeletonUtils.clone(g.scene);
    const m = this.rest.get(spec.bone).clone().invert().multiply(new THREE.Matrix4().makeTranslation(...spec.pos));
    m.decompose(obj.position, obj.quaternion, obj.scale);
    bone.add(obj);
    this.props.push(obj);
  }

  detach() {
    for (const p of this.props) p.removeFromParent();
    this.props = [];
  }

  update(dt) {
    this.mixer.update(dt);
    if (this.gltf.blink && STILL === null) {
      this.blinkIn -= dt;
      if (this.blinkIn <= 0) {
        this.blink();
        this.blinkIn = 2.2 + Math.random() * 3.5;
      }
    }
  }
}

// ---------- layout helpers ----------
// The part of the screen not covered by HUD panels; characters are framed inside it.
function freeRect() {
  const W = innerWidth;
  const H = innerHeight;
  const top = $('#top').getBoundingClientRect();
  const ros = $('#roster').getBoundingClientRect();
  const pan = $('#panel').getBoundingClientRect();
  if (W < 760) {
    const y = Math.max(top.bottom, ros.bottom);
    return { x: 0, y, w: W, h: Math.max(120, pan.top - y) };
  }
  const x = ros.right + 12;
  return { x, y: top.bottom, w: Math.max(160, pan.left - 12 - x), h: H - top.bottom };
}

function applyOffset(rect) {
  const W = innerWidth;
  const H = innerHeight;
  camera.aspect = W / H;
  camera.setViewOffset(W, H, W / 2 - (rect.x + rect.w / 2), H / 2 - (rect.y + rect.h / 2), W, H);
  camera.updateProjectionMatrix();
}

// Distance that fits a width x height silhouette into a wPx x hPx part of a canvas Hpx tall, plus half the depth.
function fitDistance(width, height, depth, fov, wPx, hPx, Hpx, pad) {
  const t = Math.tan(THREE.MathUtils.degToRad(fov / 2));
  return Math.max((height * pad) / 2 / ((t * hPx) / Hpx), (width * pad) / 2 / ((t * wPx) / Hpx)) + depth / 2;
}

// Silhouette width and depth of a box seen from azimuth az (degrees).
function extent(size, az) {
  const a = THREE.MathUtils.degToRad(az);
  const c = Math.abs(Math.cos(a));
  const s = Math.abs(Math.sin(a));
  return [size.x * c + size.z * s, size.x * s + size.z * c];
}

let framing = null;   // {box, az, elev, pad, target?}
function frame(box, { az = 0, elev = 7, pad = 1.2, focus = null, dist = null } = {}) {
  framing = { box: box.clone(), az, elev, pad, focus, dist };
  const rect = freeRect();
  applyOffset(rect);
  const size = box.getSize(new THREE.Vector3());
  const center = focus ? focus.clone() : box.getCenter(new THREE.Vector3());
  const [wide, deep] = extent(size, az);
  const d = dist ?? fitDistance(wide, size.y, deep, camera.fov, rect.w, rect.h, innerHeight, pad);
  const a = THREE.MathUtils.degToRad(az);
  const e = THREE.MathUtils.degToRad(elev);
  camera.position.set(center.x + Math.sin(a) * Math.cos(e) * d, center.y + Math.sin(e) * d, center.z + Math.cos(a) * Math.cos(e) * d);
  camera.near = Math.max(0.01, d / 100);
  camera.far = 200;
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.minDistance = d * 0.3;
  controls.maxDistance = d * 2.6;
  controls.update();
  stage.fit(box);
  if (state.mode === 'three') frameThree(box);
}

function frameThree(box) {
  const rect = freeRect();
  const pw = rect.w / 3;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  // one shared distance so the three views are drawn at the same scale
  const d = Math.max(...[0, 90].map((az) => {
    const [wide, deep] = extent(size, az);
    return fitDistance(wide, size.y, deep, triCams[0].fov, pw, rect.h, rect.h, 1.12);
  }));
  triCams.forEach((cam, i) => {
    cam.aspect = pw / rect.h;
    const a = THREE.MathUtils.degToRad([0, 90, 180][i]);
    const e = THREE.MathUtils.degToRad(3);
    cam.position.set(center.x + Math.sin(a) * Math.cos(e) * d, center.y + Math.sin(e) * d, center.z + Math.cos(a) * Math.cos(e) * d);
    cam.lookAt(center);
    cam.near = Math.max(0.01, d / 100);
    cam.updateProjectionMatrix();
  });
}

// ---------- scene management ----------
let actors = [];
let labels = [];   // {el, obj, y} : HTML tags pinned above characters
let sceneToken = 0;

function clearWorld() {
  for (const a of actors) {
    a.detach();
    a.mixer.stopAllAction();
  }
  world.clear();
  actors = [];
  labels = [];
  $('#labels').replaceChildren();
}

function place(list, gap) {
  let cursor = 0;
  for (const a of list) {
    const off = a.entry.offsets?.[a.file] || [0, 0, 0];
    a.root.position.set(cursor - a.box.min.x + off[0], off[1], off[2]);
    cursor += a.box.max.x - a.box.min.x + gap;
  }
  const shift = (cursor - gap) / 2;
  for (const a of list) a.root.position.x -= shift;
}

function worldBox(list) {
  const b = new THREE.Box3();
  for (const a of list) b.union(a.box.clone().translate(a.root.position));
  return b;
}

async function ensureStage(kind) {
  if (stage.kind === kind) return;
  await stage.set(kind);
  syncChips('#bgs', kind);
}

async function showSolo() {
  const entry = byId[state.char];
  const token = ++sceneToken;
  busy(true);
  const gltfs = await Promise.all(entry.files.map(loadGLB));
  await ensureStage(state.bg || 'studio');
  if (token !== sceneToken) return;
  clearWorld();
  actors = gltfs.map((g, i) => new Actor(g, entry, entry.files[i]));
  place(actors, entry.id === 'props' ? 0.14 : 0.1);
  actors.forEach((a) => world.add(a.root));
  const anim = entry.anims.some(([n]) => n === state.anim) ? state.anim : entry.anims[0][0];
  playAnim(anim, true);
  const box = worldBox(actors);
  // widen the display base only for rows of several models (babies, props); a tail may hang over the edge
  stage.setStand(true, actors.length > 1 ? Math.max(1, (Math.max(box.max.x, -box.min.x) + 0.1) / 0.5) : 1);
  frame(box, { az: state.mode === 'three' ? 0 : 12, elev: 4, pad: state.mode === 'three' ? 1.1 : 1.22 });
  if (state.mode === 'three') {
    const r = freeRect();
    ['正面', '侧面', '背面'].forEach((t, i) => {
      const el = h('div', { class: 'tri-label' }, t);
      el.style.left = `${r.x + (i + 0.5) * (r.w / 3)}px`;
      el.style.top = `${r.y + 10}px`;
      $('#labels').append(el);
    });
  }
  renderPanel();
  busy(false);
}

async function showLineup() {
  const token = ++sceneToken;
  busy(true);
  const entries = LINEUP.map((id) => byId[id]);
  const files = entries.flatMap((e) => e.files.map((f) => [e, f]));
  const gltfs = await Promise.all(files.map(([, f]) => loadGLB(f)));
  await ensureStage(state.bg || 'studio');
  if (token !== sceneToken) return;
  clearWorld();
  actors = gltfs.map((g, i) => new Actor(g, files[i][0], files[i][1]));
  // one row, babies huddled together; the tallest stand at the back row ends
  let cursor = 0;
  for (const e of entries) {
    const group = actors.filter((a) => a.entry === e);
    const gap = 0.02;
    let x0 = cursor;
    for (const a of group) {
      a.root.position.set(cursor - a.box.min.x, 0, 0);
      cursor += a.box.max.x - a.box.min.x + gap;
    }
    const groupBox = worldBox(group);
    const top = new THREE.Vector3((x0 + cursor - gap) / 2, groupBox.max.y, 0);
    const cm = Math.round((groupBox.max.y - groupBox.min.y) * 100);
    const el = h('div', { class: 'tag' }, h('b', {}, e.name), h('span', {}, `${cm} cm`));
    $('#labels').append(el);
    labels.push({ el, pos: top });
    cursor += 0.22;
  }
  const shift = (cursor - 0.22) / 2;
  for (const a of actors) a.root.position.x -= shift;
  for (const l of labels) l.pos.x -= shift;
  actors.forEach((a) => {
    world.add(a.root);
    a.play(a.entry.anims[0][0], { offset: Math.random() * 3 });
    a.setExpr(a.entry.expr?.default);
  });
  stage.setStand(false);
  const box = worldBox(actors);
  box.max.y += 0.18;   // room for the tags
  frame(box, { az: 0, elev: 5, pad: innerWidth < 760 ? 1.3 : 1.1 });
  renderPanel();
  busy(false);
}

// Seeded so every visit shows the same beach, and 「换一批」 reshuffles.
function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
let heroSeed = 7;
const heroState = { fish: 'sign', babies: 'mix' };

async function showHero() {
  const token = ++sceneToken;
  busy(true);
  const fishEntry = byId.bluefish;
  const babyEntry = byId.babies;
  const [fish, ...babies] = await Promise.all([fishEntry.files[0], ...babyEntry.files].map(loadGLB));
  await loadGLB(fishEntry.props.sign.file);
  await ensureStage(state.bg && state.bg !== 'studio' ? state.bg : 'beach');
  if (token !== sceneToken) return;
  clearWorld();
  const star = new Actor(fish, fishEntry, fishEntry.files[0]);
  star.root.rotation.y = THREE.MathUtils.degToRad(-8);
  world.add(star.root);
  actors = [star];
  const rand = rng(heroSeed);
  const spots = [];
  let tries = 0;
  while (spots.length < 22 && tries++ < 4000) {
    const x = (rand() * 2 - 1) * 2.6;
    const z = -3.2 + rand() * 4.6;
    if (Math.hypot(x, z) < 0.6) continue;
    if (z > -0.3 && Math.abs(x) < 0.34 + (z + 0.3) * 0.35) continue;   // keep the camera's view of her clear
    if (Math.abs(x) > 0.9 + (z + 3.2) * 0.45) continue;   // roughly inside the default view
    if (spots.some(([sx, sz]) => Math.hypot(sx - x, sz - z) < 0.36)) continue;
    spots.push([x, z]);
  }
  spots.forEach(([x, z], i) => {
    const g = babies[i % babies.length];
    const a = new Actor(g, babyEntry, babyEntry.files[i % babies.length]);
    const face = Math.atan2(0.3 - x, 3.5 - z) + (rand() - 0.5) * 2.2;
    a.root.position.set(x, 0, z);
    a.root.rotation.y = face;
    a.root.scale.setScalar(0.85 + rand() * 0.3);
    a.seed = rand();
    world.add(a.root);
    actors.push(a);
  });
  heroAnims();
  stage.setStand(false);
  // frame her (with a margin of beach) like the video's closing shot; the babies fill the rest of the screen
  const box = new THREE.Box3(new THREE.Vector3(-0.6, 0, -0.3), new THREE.Vector3(0.6, 1.0, 0.3));
  frame(box, { az: 3, elev: 7, pad: 1.15, focus: new THREE.Vector3(0.02, 0.44, 0) });
  renderPanel();
  busy(false);
}

function heroAnims() {
  const [star, ...babies] = actors;
  const fish = heroState.fish;
  star.play(fish);
  star.setExpr(byId.bluefish.expr[fish] || byId.bluefish.expr.default);
  star.attach(byId.bluefish.props[fish]);
  const pick = { mix: ['idle', 'hop', 'idle', 'flap', 'hop'], hop: ['hop'], spin: ['spin'], flap: ['flap'] }[heroState.babies];
  babies.forEach((a, i) => a.play(pick[i % pick.length], { offset: a.seed * 3, speed: 0.85 + a.seed * 0.3 }));
}

function playAnim(name, first = false) {
  state.anim = name;
  const entry = byId[state.char];
  for (const a of actors) a.play(name, { fade: first ? 0 : 0.3 });
  state.expr = [...(entry.expr?.[name] || entry.expr?.default || [])];
  for (const a of actors) a.setExpr(state.expr);
  const spec = entry.props?.[name];
  if (actors[0]) actors[0].attach(spec);
  for (const a of actors.slice(1)) a.detach();
  syncChips('#anims', name);
  syncExpr();
  writeHash();
}

// ---------- mode switching ----------
async function show() {
  document.body.dataset.mode = state.mode;
  syncChips('#modes', state.mode);
  syncRoster();
  controls.autoRotate = state.turn && state.mode === 'solo';
  controls.enabled = state.mode !== 'three';
  writeHash();
  try {
    if (state.mode === 'lineup') await showLineup();
    else if (state.mode === 'hero') await showHero();
    else await showSolo();
  } catch (e) {
    console.error(e);
    busy(false);
    toast('加载失败，请刷新重试');
  }
  if (STILL !== null) {
    for (const a of actors) a.mixer.update(STILL);
    await Promise.all(actors.map((a) => (a.props.length ? null : new Promise((r) => setTimeout(r, 50)))));
  }
  render();
  window.__ready = true;
}

function writeHash() {
  const p = new URLSearchParams();
  p.set('m', state.mode);
  if (state.mode === 'solo' || state.mode === 'three') p.set('c', state.char);
  if (state.bg) p.set('bg', state.bg);
  if (STILL !== null) p.set('still', STILL);
  try {
    history.replaceState(null, '', `#${p}`);
  } catch (e) {
    /* sandboxed frames may refuse; deep links are a nicety */
  }
}

// ---------- HUD ----------
function chip(label, on, attrs = {}) {
  return h('button', { class: 'chip', type: 'button', ...attrs, onclick: on }, label);
}

function syncChips(sel, value) {
  for (const b of document.querySelectorAll(`${sel} [data-v]`)) b.classList.toggle('on', b.dataset.v === value);
}

function syncRoster() {
  for (const b of document.querySelectorAll('#roster [data-id]')) {
    b.classList.toggle('on', (state.mode === 'solo' || state.mode === 'three') && b.dataset.id === state.char);
  }
}

function syncExpr() {
  const on = new Set(state.expr || []);
  for (const b of document.querySelectorAll('#expr [data-v]')) b.classList.toggle('on', on.has(b.dataset.v));
}

function buildStaticHud() {
  $('#modes').replaceChildren(...MODES.map(([m, label]) => chip(label, () => {
    if (state.mode === m) return;
    state.mode = m;
    show();
  }, { 'data-v': m })));
  $('#roster').replaceChildren(...CHARACTERS.map((c) => h('button', {
    class: 'card', type: 'button', 'data-id': c.id, title: c.name,
    onclick: () => {
      const same = state.char === c.id && (state.mode === 'solo' || state.mode === 'three');
      if (state.char !== c.id) state.anim = null;
      state.char = c.id;
      if (state.mode !== 'three') state.mode = 'solo';
      if (!same) show();
    },
  }, h('img', { src: `${BASE}assets/portraits/${c.id}.jpg`, alt: '' }), h('span', { class: 'nm' }, c.name), h('span', { class: 'rl' }, c.role))));
  $('#bgs').replaceChildren(...Object.entries(STAGES).map(([k, s]) => chip(s.label, async () => {
    state.bg = k;
    writeHash();
    await stage.set(k);
    syncChips('#bgs', k);
  }, { 'data-v': k })));
  $('#shot').addEventListener('click', screenshot);
  $('#turn').addEventListener('click', () => {
    state.turn = !state.turn;
    $('#turn').classList.toggle('on', state.turn);
    controls.autoRotate = state.turn && state.mode === 'solo';
  });
  $('#reset').addEventListener('click', () => framing && frame(framing.box, framing));
}

function renderPanel() {
  const info = $('#info');
  const acts = $('#anims');
  const expr = $('#expr');
  if (state.mode === 'lineup') {
    info.replaceChildren(h('h2', {}, '全员合影'), h('p', { class: 'tags' }, h('span', {}, '身高对比')),
      h('p', { class: 'blurb' }, '三部视频里的角色站成一排。数字是模型身高，游戏里的城市会按这个比例来搭。'));
    const all = (v, pick) => chip(v === 'idle' ? '待机' : '走路', () => {
      actors.forEach((a) => a.play(pick(a)));
      syncChips('#anims', v);
    }, { 'data-v': v });
    acts.replaceChildren(all('idle', (a) => a.entry.anims[0][0]), all('walk', (a) => (a.gltf.clips.has('walk') ? 'walk' : 'hop')));
    syncChips('#anims', 'idle');
    expr.parentElement.hidden = true;
    return;
  }
  if (state.mode === 'hero') {
    info.replaceChildren(h('h2', {}, '片尾复刻'), h('p', { class: 'tags' }, h('span', {}, 'EP1 · 鲸鱼沙滩')),
      h('p', { class: 'blurb' }, '「喜欢的话可以点赞谢谢喵」——EP1 的结尾，大肥鱼举着木牌，小鲸鱼们在沙滩上蹦来蹦去。可以拖动视角。'));
    const row = (cls, opts, key) => h('div', { class: `row ${cls}` }, ...opts.map(([v, l]) => chip(l, () => {
      heroState[key] = v;
      heroAnims();
      syncChips(`#anims .${cls}`, v);
    }, { 'data-v': v })));
    acts.replaceChildren(
      h('div', { class: 'sub' }, '大肥鱼'),
      row('fish', [['sign', '举牌'], ['cheer', '欢呼'], ['idle', '待机']], 'fish'),
      h('div', { class: 'sub' }, '小鲸鱼'),
      row('babies', [['mix', '随意'], ['hop', '一起蹦'], ['spin', '转圈'], ['flap', '拍鳍']], 'babies'),
      chip('换一批小鲸鱼', () => {
        heroSeed += 1;
        showHero();
      }, { class: 'chip wide' }),
    );
    syncChips('#anims .fish', heroState.fish);
    syncChips('#anims .babies', heroState.babies);
    expr.parentElement.hidden = true;
    return;
  }
  const c = byId[state.char];
  info.replaceChildren(
    h('h2', {}, c.name),
    h('p', { class: 'tags' }, h('span', { class: 'gold' }, c.role), h('span', {}, `出场 ${c.from}`)),
    h('p', { class: 'blurb' }, c.blurb),
  );
  acts.replaceChildren(...c.anims.map(([v, l]) => chip(l, () => playAnim(v), { 'data-v': v })));
  syncChips('#anims', state.anim);
  const sets = c.exprSets ? Object.entries(c.exprSets) : [];
  expr.parentElement.hidden = !sets.length && !actors.some((a) => a.gltf.blink);
  expr.replaceChildren(
    ...sets.map(([group, names]) => h('div', { class: 'row' }, h('span', { class: 'sub' }, EXPR_GROUPS[group] || group),
      ...names.map((n) => chip(EXPR_LABELS[n] || n, () => {
        const keep = (state.expr || []).filter((x) => !names.includes(x));
        state.expr = [...keep, n];
        actors.forEach((a) => a.setExpr(state.expr));
        syncExpr();
      }, { 'data-v': n })))),
    actors.some((a) => a.gltf.blink) ? chip('眨眼', () => actors.forEach((a) => a.blink()), { class: 'chip wide' }) : null,
  );
  syncExpr();
}

let toastTimer = 0;
function toast(text) {
  const el = $('#banner');
  el.textContent = text;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2400);
}

function showProgress() {
  let loaded = 0;
  let total = 0;
  for (const [l, t] of progress.values()) {
    loaded += l;
    total += t;
  }
  const bar = $('#load i');
  if (bar) bar.style.width = total ? `${Math.round((loaded / total) * 100)}%` : '0%';
  $('#load b').textContent = total ? `${(loaded / 1048576).toFixed(1)} / ${(total / 1048576).toFixed(1)} MB` : '';
}

function busy(on) {
  $('#load').classList.toggle('show', on);
}

function screenshot() {
  const saved = camera.view && { ...camera.view };
  if (state.mode !== 'three') {
    camera.clearViewOffset();
    camera.updateProjectionMatrix();
  }
  render();
  canvas.toBlob((blob) => {
    if (!blob) return;
    const a = h('a', { href: URL.createObjectURL(blob), download: `蓝色大肥鱼-${state.mode === 'solo' ? byId[state.char].name : state.mode}.png` });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    toast('截图已保存');
  });
  if (saved && state.mode !== 'three') {
    camera.setViewOffset(saved.fullWidth, saved.fullHeight, saved.offsetX, saved.offsetY, saved.width, saved.height);
    camera.updateProjectionMatrix();
  }
}

// ---------- frame loop ----------
function render() {
  if (state.mode === 'three') {
    const r = freeRect();
    const pw = r.w / 3;
    renderer.setScissorTest(false);
    renderer.setViewport(0, 0, innerWidth, innerHeight);
    renderer.setClearColor('#0b132c');
    renderer.clear();
    renderer.setScissorTest(true);
    triCams.forEach((cam, i) => {
      const x = r.x + i * pw;
      const y = innerHeight - (r.y + r.h);
      renderer.setViewport(x, y, pw, r.h);
      renderer.setScissor(x, y, pw, r.h);
      renderer.render(scene, cam);
    });
    renderer.setScissorTest(false);
    renderer.setViewport(0, 0, innerWidth, innerHeight);
  } else {
    renderer.render(scene, camera);
  }
  if (labels.length) {
    const v = new THREE.Vector3();
    for (const l of labels) {
      v.copy(l.pos).project(camera);
      l.el.style.transform = `translate(${((v.x + 1) / 2) * innerWidth}px, ${((1 - v.y) / 2) * innerHeight}px) translate(-50%, -100%)`;
    }
  }
}

function resize() {
  renderer.setSize(innerWidth, innerHeight);
  if (framing) frame(framing.box, framing);
  if (state.mode === 'three') {
    const r = freeRect();
    document.querySelectorAll('.tri-label').forEach((el, i) => {
      el.style.left = `${r.x + (i + 0.5) * (r.w / 3)}px`;
      el.style.top = `${r.y + 10}px`;
    });
  }
}

function loop(now) {
  timer.update(now);
  const dt = Math.min(timer.getDelta(), 0.1);
  if (STILL === null) for (const a of actors) a.update(dt);
  controls.update(dt);
  render();
}

buildStaticHud();
resize();
addEventListener('resize', resize);
show().then(() => {
  if (STILL === null) {
    renderer.setAnimationLoop(loop);
    toast(state.mode === 'hero' ? '喜欢的话可以点赞谢谢喵' : '欢迎来到蓝色大肥鱼的世界');
  }
});
