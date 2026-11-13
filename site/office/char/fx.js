// 小特效（第四階段）：睡覺的 Zzz。只有三張共用貼圖＋最多 4 個精靈；角色離開睡覺狀態就淡出，dispose() 會釋放貼圖與材質。
import * as THREE from 'three';

function zTexture(ch, col) {
  const s = 128, cv = document.createElement('canvas'); cv.width = cv.height = s; const g = cv.getContext('2d');
  g.font = '700 92px "Noto Sans TC", system-ui, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.lineJoin = 'round'; g.lineWidth = 12; g.strokeStyle = 'rgba(255,250,243,0.9)'; g.strokeText(ch, s / 2, s / 2 + 4); g.fillStyle = col; g.fillText(ch, s / 2, s / 2 + 4);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export class SleepFx {
  constructor(scene) {
    this.scene = scene; this.group = new THREE.Group(); this.group.name = 'sleepfx'; scene.add(this.group);
    this.tex = [zTexture('z', '#9a6f5e'), zTexture('Z', '#8a5f50')];
    this.items = []; this.t = 0; this.next = 0; this.n = 0;
    for (let i = 0; i < 4; i++) {
      const m = new THREE.SpriteMaterial({ map: this.tex[i % 2], transparent: true, depthWrite: false, depthTest: false, opacity: 0 }), sp = new THREE.Sprite(m); sp.visible = false; sp.renderOrder = 20; this.group.add(sp);
      this.items.push({ sp, age: 99, life: 2.6, x: 0, y: 0, z: 0, ph: 0 });
    }
  }
  /** 每幀呼叫：ctl 是 CharController。睡著超過 0.7 秒開始冒 Zzz（每 1.1 秒一個），離開睡覺不再冒、已冒的飄完。 */
  update(dt, ctl) {
    this.t += dt;
    const sleeping = ctl && ctl.state === 'sleep' && ctl.sleepT > 0.7;
    if (sleeping) { this.next -= dt; if (this.next <= 0) { this.next = 1.1; const it = this.items.find(i => i.age >= i.life); if (it) { it.age = 0; it.life = 2.6; it.ph = this.n++ * 1.7; it.sp.material.map = this.tex[this.n % 2]; it.sp.material.needsUpdate = true; } } } else this.next = 0.2;
    const b = ctl ? ctl.body : null;
    for (const it of this.items) {
      if (it.age >= it.life) { it.sp.visible = false; continue; }
      it.age += dt; const u = it.age / it.life, e = Math.min(1, u / 0.18), fade = u > 0.65 ? 1 - (u - 0.65) / 0.35 : 1;
      it.sp.visible = true; it.sp.material.opacity = Math.max(0, 0.9 * e * fade); const k = 0.15 + 0.2 * u;   // 愈飄愈大
      it.sp.scale.set(k, k, 1);
      if (b) { const c = Math.cos(b.yaw), s = Math.sin(b.yaw), lx = 0.3 + 0.22 * u + 0.03 * Math.sin(it.age * 3 + it.ph), lz = 0.05; it.sp.position.set(b.x + lx * c + lz * s, b.y + 0.66 + 0.5 * u, b.z - lx * s + lz * c); }
    }
  }
  get active() { return this.items.filter(i => i.sp.visible).length; }
  dispose() { for (const it of this.items) it.sp.material.dispose(); for (const t of this.tex) t.dispose(); this.scene.remove(this.group); this.items.length = 0; this.tex.length = 0; }
}
