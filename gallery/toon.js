// Converts glTF materials exported by tools/charkit into the look used in the game:
//   toon_*  -> MToon anime shading + outline      face_*  -> unlit decal (eyes, mouth, blush)
//   pbr_* / metal_* -> kept as physically based materials (props live in the realistic world)
// Shading parameters come from the material's glTF extras ("style" JSON written by charkit).
import * as THREE from 'three';
import { MToonMaterial } from '@pixiv/three-vrm-materials-mtoon';

function styleOf(m) {
  try {
    return m.userData && m.userData.style ? JSON.parse(m.userData.style) : {};
  } catch (e) {
    return {};
  }
}

// Anime shade: darker, a bit more saturated, hue nudged toward blue.
export function shadeOf(c, k = 0.58) {
  const hsl = {};
  c.getHSL(hsl);
  const h = hsl.h < 0.12 || hsl.h > 0.9 ? hsl.h - 0.015 : hsl.h + 0.012;
  return new THREE.Color().setHSL((h + 1) % 1, Math.min(1, hsl.s * 1.1 + 0.06), hsl.l * k);
}

function makeToon(src, st, vertexColors) {
  const m = new MToonMaterial();
  m.name = src.name;
  m.color.copy(src.color);
  if (src.map) m.map = src.map;
  m.shadeColorFactor.copy(st.shade ? new THREE.Color(st.shade) : shadeOf(src.color));
  m.shadingToonyFactor = st.toony ?? 0.88;
  m.shadingShiftFactor = st.shift ?? -0.05;
  m.giEqualizationFactor = st.gi ?? 0.9;
  m.parametricRimColorFactor.set(st.rim ?? '#bcd6ff').multiplyScalar(st.rimStrength ?? 0.28);
  m.parametricRimFresnelPowerFactor = st.rimPower ?? 4.0;
  m.parametricRimLiftFactor = st.rimLift ?? 0.0;
  m.rimLightingMixFactor = 1.0;
  if (st.emissive) {
    m.emissive.set(st.emissive);
    m.emissiveIntensity = st.emissiveIntensity ?? 1;
  }
  const w = st.outline ?? 0.0022;
  m.outlineWidthMode = w > 0 ? 'worldCoordinates' : 'none';
  m.outlineWidthFactor = w;
  m.outlineColorFactor.copy(st.outlineColor ? new THREE.Color(st.outlineColor) : shadeOf(m.shadeColorFactor.clone(), 0.55));
  m.outlineLightingMixFactor = st.outlineMix ?? 0.35;
  if (vertexColors) {
    m.vertexColors = true;
    m.ignoreVertexColor = false;
  }
  m.side = st.double ? THREE.DoubleSide : THREE.FrontSide;
  return m;
}

// MToon's shader multiplies with a vec3 vColor; glTF from Blender carries RGBA, so drop alpha.
function rgbOnly(geometry) {
  const c = geometry.attributes.color;
  if (!c || c.itemSize === 3) return;
  const out = new Float32Array(c.count * 3);
  for (let i = 0; i < c.count; i++) {
    out[i * 3] = c.getX(i);
    out[i * 3 + 1] = c.getY(i);
    out[i * 3 + 2] = c.getZ(i);
  }
  geometry.setAttribute('color', new THREE.BufferAttribute(out, 3));
}

function addOutline(mesh) {
  const surface = mesh.material;
  if (!(surface instanceof MToonMaterial) || surface.outlineWidthMode === 'none' || !(surface.outlineWidthFactor > 0)) return;
  const outline = surface.clone();
  outline.name += ' (Outline)';
  outline.isOutline = true;
  outline.side = THREE.BackSide;
  mesh.material = [surface, outline];
  const g = mesh.geometry;
  const count = g.index ? g.index.count : g.attributes.position.count;
  g.clearGroups();
  g.addGroup(0, count, 0);
  g.addGroup(0, count, 1);
}

// Figure (手办) look: soft physically based shading with gloss, like a painted PVC figure.
function makeFigure(src, st, vertexColors) {
  const m = new THREE.MeshPhysicalMaterial({
    name: src.name,
    color: src.color,
    map: src.map || null,
    vertexColors,
    roughness: st.rough ?? 0.55,
    metalness: st.metal ?? 0.0,
    clearcoat: st.coat ?? 0.0,
    clearcoatRoughness: st.coatRough ?? 0.25,
    sheen: st.sheen ?? 0.0,
    sheenRoughness: st.sheenRough ?? 0.6,
    sheenColor: new THREE.Color(st.sheenColor ?? '#ffffff'),
    envMapIntensity: st.env ?? 0.9,
    side: st.double ? THREE.DoubleSide : THREE.FrontSide,
  });
  if (st.emissive) {
    m.emissive.set(st.emissive);
    m.emissiveIntensity = st.emissiveIntensity ?? 0.12;
  }
  return m;
}

// Returns the list of MToon materials so callers can tweak them (e.g. outline toggle).
export function toonify(root, { outlines = true, envMap = null } = {}) {
  const mtoons = [];
  root.traverse((o) => {
    if (!o.isMesh) return;
    const src = o.material;
    if (Array.isArray(src)) return;
    const name = src.name || '';
    const st = styleOf(src);
    const vc = !!o.geometry.attributes.color;
    if (name.startsWith('toon_')) {
      if (vc) rgbOnly(o.geometry);
      o.material = makeToon(src, st, vc);
      mtoons.push(o.material);
      if (outlines) addOutline(o);
      o.castShadow = true;
      o.receiveShadow = false;
    } else if (name.startsWith('fig_')) {
      o.material = makeFigure(src, st, vc);
      o.castShadow = true;
      o.receiveShadow = true;
    } else if (name.startsWith('face_')) {
      o.material = new THREE.MeshBasicMaterial({
        name, map: src.map || null, color: src.color, transparent: true, depthWrite: false,
        alphaTest: 0.01, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4, toneMapped: st.toneMapped ?? true,
      });
      o.renderOrder = 3;
      o.castShadow = false;
    } else {
      if (st.rough !== undefined) src.roughness = st.rough;
      if (envMap) src.envMap = envMap;
      src.envMapIntensity = st.env ?? 1.0;
      o.castShadow = true;
      o.receiveShadow = true;
    }
    o.frustumCulled = false;
  });
  return mtoons;
}
