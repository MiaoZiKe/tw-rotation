// 新角色檢視器（開發／驗收用）：?sp=bunny&old=0|1&pal=0&acc=badge,tie
// window.SV：cam(az, el, dist, ty)、pose(name)、advance(sec)、shot() 就緒旗標 ready。新舊都用同一組鏡頭與燈光，才能公平並排。
import * as THREE from 'three';
import { Stage, BG } from './stage.js';
import { loadMochi, MochiChar } from './mochi.js';
import { CharController, loadProfile } from './controller.js';
import { PhysWorld } from './physics.js';
import { NEW_KINDS, colorsFor, mergeProfile, PROFILE_OVERRIDE, applyBounce } from './kinds.js';
import { addAccs, addCherry } from './accs.js';
import { Character } from '../play/character.js';
import { stubWorld, stubFx } from '../play/lite.js';
import { SPECIES } from '../play/species.js';

const qs = new URLSearchParams(location.search), sp = qs.get('sp') || 'bunny', OLD = qs.get('old') === '1', pal = +(qs.get('pal') || 0), acc = (qs.get('acc') || '').split(',').filter(Boolean);
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true }); renderer.setPixelRatio(1); renderer.setSize(innerWidth, innerHeight); document.getElementById('view').appendChild(renderer.domElement);
const stage = new Stage(renderer), scene = stage.scene, camera = new THREE.PerspectiveCamera(26, innerWidth / innerHeight, 0.05, 40);
const SV = window.SV = { ready: false, cam, pose, advance, scene, camera, renderer, stage, wire, pos };
function wire(on) { if (scene.overrideMaterial) scene.overrideMaterial.dispose(); scene.overrideMaterial = on ? new THREE.MeshBasicMaterial({ color: 0x6a4636, wireframe: true }) : null; stage.floor.visible = !on; render(); }
function pos() { return OLD ? { x: old.pos.x, z: old.pos.z } : { x: ctl.body.x, z: ctl.body.z }; }
let ch = null, ctl = null, old = null, world = null;
function cam(az = 0, el = 0.12, dist = 3.6, ty = 0.36, tx = 0, tz = 0) { camera.position.set(tx + Math.sin(az) * dist * Math.cos(el), ty + Math.sin(el) * dist, tz + Math.cos(az) * dist * Math.cos(el)); camera.lookAt(tx, ty, tz); camera.updateMatrixWorld(); render(); }
function render() { if (ctl) stage.updateContact?.(); renderer.render(scene, camera); }
const chairMeshes = [];
function addChair(seatY, x = 0, z = 0) {   // 簡單的椅子：座面圓盤＋氣壓桿＋五星腳，高度＝seatY
  const g = new THREE.Group(), m = new THREE.MeshStandardMaterial({ color: 0x7d8490, roughness: 0.8 }), sm = new THREE.MeshStandardMaterial({ color: 0xb9a99a, roughness: 0.85 });
  const seat = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 0.06, 28), sm); seat.position.y = seatY - 0.03; const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, seatY - 0.06, 10), m); pole.position.y = (seatY - 0.06) / 2;
  const back = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.4, 0.05), sm); back.position.set(0, seatY + 0.22, -0.24); g.add(seat, pole, back); g.position.set(x, 0, z); scene.add(g); chairMeshes.push(g);
}
async function build() {
  if (OLD) {
    scene.environment = null; const space = new THREE.Group(); scene.add(space); const c = new Character({ species: sp, pal, acc }, scene, stubWorld(), stubFx, { space }); c.pos.set(0, 0, 0); c.yaw = 0; c.lookT = 1e9; c.face.blinkT = 1e9; c.idleT = 0;
    c.feet.forEach(f => { c.footHome(f, f.p); f.from.copy(f.p); f.m.position.copy(f.p); });
    for (let i = 0; i < 40; i++) { c.step(1 / 60, { mx: 0, mz: 0, run: false, jump: false }); c.animate(1 / 60, { look: null, cam: camera.position }); }
    old = c; SV.old = c; return;
  }
  const asset = await loadMochi({ species: sp, lod: 0 }), col = colorsFor({ species: sp, pal, hue: 0, acc, accColor: +(qs.get('ac') || 0), seed: 0 });
  ch = new MochiChar(asset, { preset: NEW_KINDS[sp].preset, color: col.color, top: col.top, zone: col.zone, zone2: col.zone2 }); scene.add(ch.root); stage.addContact(ch);
  if (acc.length) addAccs(ch, acc, col.acc);
  if (NEW_KINDS[sp].cherry) addCherry(ch, col.cherry);
  world = new PhysWorld({ minX: -3, maxX: 3, minZ: -3, maxZ: 3 }); world.addBox({ id: 'seat', cx: 0, cz: -0.9, hx: 0.25, hz: 0.25, y1: 0.42, face: 0 });   // 面向 +Z 的座位（椅背在 -Z 側）
  const base = await loadProfile('./profiles/mochi.json'); ctl = new CharController(ch, world, mergeProfile(base, PROFILE_OVERRIDE[sp]), { life: false, seed: 7 }); SV.ctl = ctl; SV.ch = ch; ctl.update(0.1);
}
function pose(name) {
  const secs = (t) => { for (let i = 0; i < t * 60; i++) { if (OLD) { old.step(1 / 60, SV.inp || { mx: 0, mz: 0, run: false, jump: false }); old.animate(1 / 60, { look: null, cam: camera.position }); } else { ctl.update(1 / 60); } } if (!OLD) applyBounce(ch, ctl, PROFILE_OVERRIDE[sp]?.bounce); };
  if (OLD) {
    if (name === 'sit') { addChair(0.42, 0, -0.9); old.pos.set(0, 0.38, -0.9); old.mode = 'sit'; old.modeT = 0; secs(2.5); }
    if (name === 'walk' || name === 'run') { SV.inp = { mx: 0, mz: 1, run: name === 'run', jump: false }; secs(1.2); }
    if (name === 'sleep') { old.mode = 'sleep'; old.modeT = 0; secs(2); }
    render(); return;
  }
  if (name === 'stand') { ctl.reset(0, 0, 0); secs(0.6); }
  if (name === 'sit') { addChair(0.42, 0, -0.9); ctl.reset(0, 0, 0); ctl.sitOn('seat'); secs(5); }
  if (name === 'walk' || name === 'run') { ctl.reset(0, 0, 0); ctl.setMove(0, 1, 1, name === 'run'); secs(1.2); }
  if (name === 'sleep') { ctl.reset(0, 0, 0); ctl.sleep(); secs(2); }
  render();
}
function advance(sec) { if (OLD) { for (let i = 0; i < sec * 60; i++) { old.step(1 / 60, SV.inp || { mx: 0, mz: 0, run: false, jump: false }); old.animate(1 / 60, { look: null, cam: camera.position }); } } else { for (let i = 0; i < sec * 60; i++) ctl.update(1 / 60); applyBounce(ch, ctl, PROFILE_OVERRIDE[sp]?.bounce); } render(); }
await build(); SV.ready = true; cam();
