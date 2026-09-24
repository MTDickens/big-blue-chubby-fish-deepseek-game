// Backdrops and light rigs: realistic photo panoramas (Poly Haven, CC0) around anime characters.
import * as THREE from 'three';
import { GroundedSkybox } from 'three/addons/objects/GroundedSkybox.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export const STAGES = {
  studio: {
    label: '展台', sun: [0.55, 0.62, 0.56], sunColor: '#fff6ea', sunI: 2.4,
    hemiSky: '#dfe8ff', hemiGround: '#8c93b8', hemiI: 1.15, exposure: 1.0,
  },
  beach: {
    label: '阳光海滩', file: 'assets/bg/beach.jpg', env: 'assets/bg/beach_env.jpg', rot: 0,
    sun: [0.727, 0.43, 0.535], sunColor: '#fff0da', sunI: 2.7, hemiSky: '#cfe2ff', hemiGround: '#ead7b0', hemiI: 1.05,
    exposure: 1.0, height: 1.2, shadow: 0.34,
  },
  night_street: {
    label: '夜晚旧城', file: 'assets/bg/night_street.jpg', env: 'assets/bg/night_street_env.jpg', rot: 0,
    sun: [0.774, 0.276, 0.57], sunColor: '#ffdcb4', sunI: 2.4, hemiSky: '#8a9bd6', hemiGround: '#6b5238', hemiI: 1.0,
    exposure: 1.0, height: 1.6, shadow: 0.42, envI: 0.45,
  },
  night_sea: {
    label: '夜晚海边', file: 'assets/bg/night_sea.jpg', env: 'assets/bg/night_sea_env.jpg', rot: 0,
    sun: [0.52, 0.496, 0.696], sunColor: '#dfe8ff', sunI: 2.2, hemiSky: '#6f84c4', hemiGround: '#b98578', hemiI: 0.95,
    exposure: 1.0, height: 1.6, shadow: 0.4, envI: 0.6,
  },
  harbor: {
    label: '港口白天', file: 'assets/bg/harbor.jpg', env: 'assets/bg/harbor_env.jpg', rot: 0,
    sun: [0.517, 0.527, 0.675], sunColor: '#fff3e2', sunI: 2.6, hemiSky: '#cfe2ff', hemiGround: '#cbbfa8', hemiI: 1.05,
    exposure: 1.0, height: 1.6, shadow: 0.34,
  },
};

function gradientTexture(top, bottom) {
  const c = document.createElement('canvas');
  c.width = 4;
  c.height = 256;
  const g = c.getContext('2d');
  const grd = g.createLinearGradient(0, 0, 0, 256);
  grd.addColorStop(0, top);
  grd.addColorStop(1, bottom);
  g.fillStyle = grd;
  g.fillRect(0, 0, 4, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export class Stage {
  constructor(renderer, scene, { base = '', studioColors = ['#3b5693', '#101a38'] } = {}) {
    this.renderer = renderer;
    this.scene = scene;
    this.base = base;
    this.cache = new Map();
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.kind = null;

    this.sun = new THREE.DirectionalLight('#ffffff', 2.5);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.normalBias = 0.01;
    this.sun.shadow.radius = 4;
    this.target = new THREE.Object3D();
    this.sun.target = this.target;
    this.hemi = new THREE.HemisphereLight('#ffffff', '#888888', 1.0);
    scene.add(this.sun, this.target, this.hemi);

    this.shadowPlane = new THREE.Mesh(new THREE.PlaneGeometry(12, 12), new THREE.ShadowMaterial({ opacity: 0.3 }));
    this.shadowPlane.rotation.x = -Math.PI / 2;
    this.shadowPlane.position.y = 0.0005;
    this.shadowPlane.receiveShadow = true;
    scene.add(this.shadowPlane);

    // studio display base, like a figure stand
    const baseGeo = new THREE.CylinderGeometry(0.5, 0.52, 0.035, 96);
    this.stand = new THREE.Mesh(baseGeo, new THREE.MeshStandardMaterial({ color: '#aebbd9', roughness: 0.38, metalness: 0.0 }));
    this.stand.position.y = -0.0175;
    this.stand.receiveShadow = true;
    scene.add(this.stand);
    this.studioBg = gradientTexture(studioColors[0], studioColors[1]);
    this.sky = null;
  }

  async load(url) {
    if (this.cache.has(url)) return this.cache.get(url);
    const p = new THREE.TextureLoader().loadAsync(this.base + url).then((t) => {
      t.colorSpace = THREE.SRGBColorSpace;
      t.mapping = THREE.EquirectangularReflectionMapping;
      return t;
    });
    this.cache.set(url, p);
    return p;
  }

  async set(kind) {
    const s = STAGES[kind] || STAGES.studio;
    this.kind = kind;
    const { scene } = this;
    this.renderer.toneMappingExposure = s.exposure ?? 1;
    this.sun.color.set(s.sunColor);
    this.sun.intensity = s.sunI;
    this.sunDir = new THREE.Vector3(...s.sun).normalize();
    this.hemi.color.set(s.hemiSky);
    this.hemi.groundColor.set(s.hemiGround);
    this.hemi.intensity = s.hemiI;
    if (this.sky) {
      scene.remove(this.sky);
      this.sky.geometry.dispose();
      this.sky = null;
    }
    if (!s.file) {
      scene.background = this.studioBg;
      if (!this.roomEnv) this.roomEnv = this.pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
      scene.environment = this.roomEnv;
      scene.environmentIntensity = 0.55;
      this.shadowPlane.material.opacity = 0.28;
    } else {
      const [bg, env] = await Promise.all([this.load(s.file), this.load(s.env)]);
      if (this.kind !== kind) return; // switched again while loading
      scene.background = bg;
      if (!env.userData.pmrem) env.userData.pmrem = this.pmrem.fromEquirectangular(env).texture;
      scene.environment = env.userData.pmrem;
      scene.environmentIntensity = s.envI ?? 0.8;
      // project the panorama onto a ground so the character stands on the photo's floor
      this.sky = new GroundedSkybox(bg, s.height, 60, 96);
      this.sky.position.y = s.height - 0.002;
      scene.add(this.sky);
      this.shadowPlane.material.opacity = s.shadow ?? 0.35;
    }
    this.applyStand();
    this.fit(this.lastBox);
    return s;
  }

  // Studio only: a figure base under the subject. Shadows land on it; elsewhere they land on an invisible floor.
  setStand(on, scale = 1) {
    this.standWanted = on;
    this.standScale = scale;
    this.applyStand();
  }

  applyStand() {
    const studio = !(STAGES[this.kind] || STAGES.studio).file;
    this.stand.visible = studio && this.standWanted !== false;
    this.stand.scale.setScalar(this.standScale || 1);
    this.shadowPlane.visible = !this.stand.visible;
  }

  // Aim the sun and size its shadow camera around the subject.
  fit(box) {
    this.lastBox = box;
    const center = new THREE.Vector3(0, 0.4, 0);
    let r = 1;
    if (box && !box.isEmpty()) {
      box.getCenter(center);
      r = Math.max(0.6, box.getSize(new THREE.Vector3()).length() * 0.6);
    }
    const d = this.sunDir || new THREE.Vector3(0.5, 0.6, 0.6).normalize();
    this.target.position.copy(center);
    this.sun.position.copy(center).addScaledVector(d, 6);
    const cam = this.sun.shadow.camera;
    cam.left = -r;
    cam.right = r;
    cam.top = r;
    cam.bottom = -r;
    cam.near = 0.5;
    cam.far = 14;
    cam.updateProjectionMatrix();
  }
}
