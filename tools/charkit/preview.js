// QA renderer for charkit models: clean turnarounds / close-ups / lineups for review.
// Query: m=path.glb[,path2.glb] anim=name t=seconds view=turn4|front|q|side|back|face|hero
//        bg=studio|beach|night_street|night_sea|harbor flat=#hex outline=0|1 w= h= hide=obj1,obj2 show=obj1
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { toonify } from '../../gallery/toon.js';
import { Stage } from '../../gallery/stage.js';

const q = new URLSearchParams(location.search);
const W = +(q.get('w') || 1600);
const H = +(q.get('h') || 900);
const models = (q.get('m') || '').split(',').filter(Boolean);
const anim = q.get('anim');
const t = +(q.get('t') || 0);
const view = q.get('view') || 'turn4';
const hide = (q.get('hide') || '').split(',').filter(Boolean);
const show = (q.get('show') || '').split(',').filter(Boolean);

try {
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(W, H);
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  document.body.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const stage = new Stage(renderer, scene, { base: '../../' });
  await stage.set(q.get('bg') || 'studio');
  if (q.get('flat')) scene.background = new THREE.Color(q.get('flat'));
  if (q.get('stand') === '0') stage.stand.visible = false;

  const loader = new GLTFLoader();
  const group = new THREE.Group();
  scene.add(group);
  let cursor = 0;
  for (const m of models) {
    const gltf = await loader.loadAsync('../../' + m);
    const root = gltf.scene;
    toonify(root, { outlines: q.get('outline') !== '0', envMap: scene.environment });
    root.traverse((o) => {
      if (hide.some((h) => o.name.startsWith(h))) o.visible = false;
      if (show.some((h) => o.name.startsWith(h))) o.visible = true;
    });
    if (anim) {
      const clip = THREE.AnimationClip.findByName(gltf.animations, anim);
      if (clip) {
        const mixer = new THREE.AnimationMixer(root);
        mixer.clipAction(clip).play();
        mixer.setTime(t);
      } else {
        console.warn('no clip', anim, gltf.animations.map((a) => a.name));
      }
    }
    root.updateMatrixWorld(true);
    const b = new THREE.Box3().setFromObject(root, true);
    if (models.length > 1) {
      root.position.x = cursor - b.min.x;
      cursor += b.max.x - b.min.x + 0.12;
    }
    group.add(root);
  }
  if (models.length > 1) group.position.x = -cursor / 2;
  scene.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(group, true);
  stage.fit(box);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());

  const fov = 30;
  const camera = new THREE.PerspectiveCamera(fov, W / H, 0.01, 200);
  const place = (az, aspect, { elev = 6, pad = 1.12, focus = center, frame = size } = {}) => {
    camera.aspect = aspect;
    const vfit = (frame.y * pad) / 2 / Math.tan(THREE.MathUtils.degToRad(fov / 2));
    const hfov = 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(fov / 2)) * aspect);
    const wide = Math.max(frame.x, frame.z);
    const hfit = (wide * pad) / 2 / Math.tan(hfov / 2);
    const dist = Math.max(vfit, hfit) + wide / 2;
    const a = THREE.MathUtils.degToRad(az);
    const e = THREE.MathUtils.degToRad(elev);
    camera.position.set(focus.x + Math.sin(a) * Math.cos(e) * dist, focus.y + Math.sin(e) * dist, focus.z + Math.cos(a) * Math.cos(e) * dist);
    camera.lookAt(focus);
    camera.updateProjectionMatrix();
  };
  const views = { front: 0, q: 35, side: 90, back: 180, qb: 145 };
  if (view === 'turn4' || view === 'turn3') {
    const angles = view === 'turn4' ? [0, 45, 90, 180] : [0, 90, 180];
    const pw = W / angles.length;
    renderer.setScissorTest(true);
    angles.forEach((az, i) => {
      renderer.setViewport(i * pw, 0, pw, H);
      renderer.setScissor(i * pw, 0, pw, H);
      place(az, pw / H);
      renderer.render(scene, camera);
    });
    renderer.setScissorTest(false);
  } else if (view === 'face') {
    const head = new THREE.Vector3(center.x, box.max.y - size.y * 0.25, center.z);
    const az = +(q.get('az') || 0);
    place(az, W / H, { focus: head, frame: new THREE.Vector3(size.x * 0.5, size.y * 0.5, size.z * 0.4), elev: 2, pad: 1.0 });
    renderer.render(scene, camera);
  } else {
    const az = q.get('az') !== null ? +q.get('az') : (views[view] ?? 20);
    place(az, W / H, { elev: +(q.get('elev') || 6) });
    renderer.render(scene, camera);
  }
  window.__ready = true;
} catch (e) {
  console.error(e);
  window.__error = String(e && e.stack || e);
}
