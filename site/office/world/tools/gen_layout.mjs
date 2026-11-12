// 產生 world/data/layout.json（辦公室佈局的初始版本）。
// 用法：node site/office/world/tools/gen_layout.mjs
// 之後「整修」只要改 layout.json（或在網頁的整修模式拖曳），不必改程式。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const org = JSON.parse(fs.readFileSync(path.join(here, '../data/org.json'), 'utf8'));
const dept = Object.fromEntries(org.departments.map(d => [d.id, d]));

const W = 40, D = 30;
const rooms = [], walls = [], furniture = [], windows = [];
let seq = 0;
const F = (type, x, z, rot = 0, extra = {}) => {
  const f = { id: `${type}_${++seq}`, type, x: +x.toFixed(2), z: +z.toFixed(2), rot, ...extra };
  furniture.push(f); return f;
};
const wall = (x1, z1, x2, z2, h = 1.1) => walls.push({ x1, z1, x2, z2, h });

// ───────── 上排：有牆的房間 ─────────
rooms.push({ id: 'ceo', name: 'CEO 辦公室', kind: 'room', x: 0, z: 0, w: 8, d: 9, floor: '#f3dfc2' });
rooms.push({ id: 'meeting', name: '會議室', kind: 'room', x: 8, z: 0, w: 10, d: 9, floor: '#d9ecdc' });
rooms.push({ id: 'library', name: '資料櫃區', kind: 'room', x: 18, z: 0, w: 6, d: 9, floor: '#eadfcd' });
rooms.push({ id: 'pantry', name: '茶水間', kind: 'room', x: 24, z: 0, w: 6, d: 9, floor: '#fde6c4' });
rooms.push({ id: 'food', name: '食物區', kind: 'room', x: 30, z: 0, w: 10, d: 9, floor: '#fbe0d4' });

// 外牆（北、東、西高牆有窗；南牆矮，中間是大門）
const HO = 2.5;
wall(0, 0, W, 0, HO); wall(0, 0, 0, D, HO); wall(W, 0, W, D, HO);
wall(0, D, 19.4, D, 0.9); wall(21.6, D, W, D, 0.9);
// 房間之間的矮隔牆
for (const x of [8, 18, 24, 30]) wall(x, 0, x, 9);
// 房間南牆（留門）
wall(0, 9, 4.9, 9); wall(6.5, 9, 8, 9);              // CEO 門 4.9–6.5
wall(8, 9, 12, 9); wall(14, 9, 18, 9);               // 會議室門 12–14
wall(18, 9, 18.8, 9); wall(23.2, 9, 24, 9);          // 資料櫃區大開口
wall(24, 9, 26.2, 9); wall(27.8, 9, 30, 9);          // 茶水間門
wall(30, 9, 32.6, 9); wall(37.4, 9, 40, 9);          // 食物區大開口
// 窗（掛在高牆上；side 指牆面）
for (const x of [2.2, 5.8, 10.5, 15.5, 21, 27, 32.5, 37.5]) windows.push({ side: 'n', at: x, w: 2.2 });
for (const z of [4.5, 14, 20.5, 27]) { windows.push({ side: 'w', at: z, w: 2.4 }); windows.push({ side: 'e', at: z, w: 2.4 }); }

// CEO 辦公室
F('rug', 4, 5.3, 0, { w: 5.2, d: 3.6, color: '#f7c8a0', round: true });
F('ceo_desk', 4, 5.5, 2, { owner: 'ceo' });
F('bookshelf', 1.5, 0.55, 0); F('bookshelf', 6.4, 0.55, 0, { nospot: true });
F('sofa', 0.75, 2.6, 1, { color: '#f2b8a2', noseat: true });
F('plant_big', 7.3, 8.2); F('lamp', 0.7, 0.75); F('plant', 7.35, 2.2); F('plant', 0.7, 8.3);
F('roomsign', 4, 0.22, 0, { text: 'CEO 辦公室', color: '#ffb86b' });
F('board', 2.4, 9.42, 0, { owner: 'ceo', label: 'CEO 佈告欄' });

// 會議室
F('rug', 13, 4.9, 0, { w: 6.6, d: 6.6, color: '#bfe0c9', round: true });
F('meeting_table', 13, 4.9, 0);
F('whiteboard', 13, 0.42, 0);
F('plant_big', 8.8, 0.9); F('plant_big', 17.2, 0.9); F('plant', 8.75, 8.3); F('lamp', 17.3, 8.3);
F('roomsign', 10.2, 0.22, 0, { text: '會議室', color: '#8fd3a6' });

// 資料櫃區
F('bookshelf', 19.4, 0.55, 0, { spot: 'library' }); F('bookshelf', 21.4, 0.55, 0, { spot: 'library' });
F('bookshelf', 18.55, 3.4, 1, { spot: 'library' }); F('bookshelf', 18.55, 5.6, 1, { spot: 'library' });
F('cabinet', 23.45, 2.2, 3, { spot: 'library' }); F('cabinet', 23.45, 3.4, 3, { spot: 'library' });
F('cabinet', 23.45, 4.6, 3, { spot: 'library' }); F('cabinet', 23.45, 5.8, 3, { spot: 'library' });
F('rug', 21, 5, 0, { w: 2.6, d: 2.6, color: '#e6c9a0', round: true });
F('side_table', 21, 5, 0); F('plant', 23.35, 7.6); F('plant', 23.2, 0.7);
F('roomsign', 20.4, 0.22, 0, { text: '資料櫃區', color: '#d9b282', high: true });

// 茶水間
F('counter', 26.6, 0.6, 0, { variant: 'coffee' });
F('water', 29.2, 0.62, 0);
F('side_table', 27, 5.2, 0, { tall: true });
F('rug', 27, 5.2, 0, { w: 3, d: 3, color: '#ffd9a8', round: true });
F('plant_big', 24.8, 8.2); F('plant', 29.3, 8.3);
F('roomsign', 27, 0.22, 0, { text: '茶水間', color: '#f3b76b', high: true });

// 食物區
F('fridge', 31, 0.68, 0); F('snack', 32.9, 0.55, 0);
F('counter', 36.2, 0.6, 0, { variant: 'microwave' });
F('dining', 33.2, 5.2, 0); F('dining', 37, 5.2, 0);
F('plant_big', 39.2, 0.9); F('plant', 30.7, 8.3); F('plant', 39.3, 8.3);
F('roomsign', 34.6, 0.22, 0, { text: '食物區', color: '#f29d86', high: true });

// ───────── 中段：11 個部門（開放式，地毯分區） ─────────
const bandA = [['video', 0, 9.2], ['social', 9.2, 17.2], ['design', 17.2, 25.2], ['frontend', 25.2, 32.6], ['industry', 32.6, 40]];
const bandB = [['quant', 0, 7], ['biz', 7, 14], ['ops', 14, 21], ['audit', 21, 28.4], ['data', 28.4, 34.2], ['legal', 34.2, 40]];
const PITCH = 1.8;
function deptZone(id, x0, x1, z0) {
  const d = dept[id], n = d.members.length, cols = Math.ceil(n / 2);
  const xc = (x0 + x1) / 2, zc = z0 + 3.45;
  rooms.push({ id, name: d.name, kind: 'dept', dept: id, x: x0 + 0.35, z: z0 + 0.15, w: x1 - x0 - 0.7, d: 5.75, floor: d.color });
  const sx = xc - (cols - 1) * PITCH / 2;
  d.members.forEach((m, i) => {
    const north = i < cols, col = north ? i : i - cols;
    F('workstation', sx + col * PITCH, zc + (north ? -0.38 : 0.38), north ? 2 : 0, { owner: m.id, dept: id });
  });
  F('deptsign', xc - 1.15, z0 + 0.5, 0, { text: d.name, color: d.color, dept: id });
  F('board', xc + 1.05, z0 + 0.5, 0, { owner: id, label: d.name + '佈告欄', small: true });
  F('plant', x0 + 0.85, z0 + 0.75); F('plant', x1 - 0.85, z0 + 5.3);
}
bandA.forEach(([id, a, b]) => deptZone(id, a, b, 11));
bandB.forEach(([id, a, b]) => deptZone(id, a, b, 17.6));

// ───────── 下排：遊樂區、後備區、入口、休息區 ─────────
rooms.push({ id: 'play', name: '遊樂區', kind: 'zone', x: 0.35, z: 24.6, w: 11.5, d: 5.05, floor: '#e3d8f6' });
rooms.push({ id: 'reserve', name: '後備區', kind: 'zone', x: 12.3, z: 24.6, w: 4.9, d: 5.05, floor: '#e8e2d6' });
rooms.push({ id: 'lobby', name: '入口大廳', kind: 'zone', x: 17.7, z: 24.6, w: 5.8, d: 5.05, floor: '#f6e7c9' });
rooms.push({ id: 'lounge', name: '休息區', kind: 'zone', x: 24, z: 24.6, w: 15.65, d: 5.05, floor: '#dcefdc' });

F('rug', 3.4, 27.3, 0, { w: 5.4, d: 3.6, color: '#cdbcf0' });
F('pingpong', 3.4, 27.3, 0);
F('arcade', 7.6, 25.25, 0); F('arcade', 8.75, 25.25, 0, { color: '#8ecfe6' });
F('beanbag', 7.4, 28.3, 0, { color: '#f7b0c6' }); F('beanbag', 8.9, 28.9, 0, { color: '#ffd27a' }); F('beanbag', 10.3, 28.0, 0, { color: '#a4c2f7' });
F('plant_big', 0.85, 25.3); F('lamp', 11.3, 25.3); F('plant', 0.8, 29.3);
F('roomsign', 10.4, 25.0, 0, { text: '遊樂區', color: '#b79cf0', stand: true });

F('reserve_seat', 13.3, 26.6, 0, { owner: 'bibi-planner' });
F('reserve_seat', 14.75, 26.6, 0, { owner: 'bibi-review' });
F('reserve_seat', 16.2, 26.6, 0, { owner: 'bibi-efficiency' });
F('roomsign', 14.75, 25.0, 0, { text: '後備區', color: '#c9bca6', stand: true });
F('plant', 12.8, 29.2); F('side_table', 14.75, 28.6, 0);

F('rug', 20.5, 26.6, 0, { w: 3.4, d: 3.4, color: '#f9d9a6', round: true });
F('doormat', 20.5, 28.9, 0);
F('door', 20.5, 30, 0);
F('plant_big', 18.6, 29.2); F('plant_big', 22.4, 29.2);
F('kiosk', 22.7, 27.2, 3);

F('rug', 27.6, 27.5, 0, { w: 5.6, d: 3.6, color: '#bfe3c6' });
F('sofa', 27.6, 25.75, 0, { color: '#f7b0c6' });
F('armchair', 24.9, 27.6, 1, { color: '#ffd27a' });
F('armchair', 30.3, 27.6, 3, { color: '#a4c2f7' });
F('coffee_table', 27.6, 27.7, 0);
F('rug', 35.4, 27.5, 0, { w: 5.6, d: 3.6, color: '#ffe0b0' });
F('sofa', 35.4, 25.75, 0, { color: '#97dfcc' });
F('armchair', 32.7, 27.6, 1, { color: '#f4a59d' });
F('armchair', 38.1, 27.6, 3, { color: '#cbb2f2' });
F('coffee_table', 35.4, 27.7, 0);
F('beanbag', 29.2, 29.1, 0, { color: '#ffc48f' }); F('beanbag', 33.8, 29.1, 0, { color: '#aedb9a' });
F('plant_big', 39.2, 29.2); F('lamp', 39.3, 25.3); F('plant', 24.6, 29.3); F('bookshelf', 31.5, 25.1, 0, { spot: 'shelf2' });
F('roomsign', 24.9, 25.0, 0, { text: '休息區', color: '#86cfa0', stand: true });

// 走道上的點綴
F('rug', 20, 10.05, 0, { w: 37, d: 1.25, color: '#f6cfa8' });
F('plant', 8.4, 9.5); F('plant', 17.6, 9.5); F('plant', 29.6, 9.5); F('bench', 21, 23.95, 0);

const layout = {
  version: 1,
  note: '單位公尺；x 向右、z 向下（南）。rot 為 90 度的倍數（0 正面朝南、1 朝東、2 朝北、3 朝西）。整修只改這份資料。',
  size: { w: W, d: D }, cell: 0.25,
  rooms, walls, windows, furniture,
  spots: [
    { name: 'door_in', x: 20.5, z: 28.9, face: 2 },
    { name: 'door_out', x: 20.5, z: 31.2, face: 0 },
    { name: 'outside', x: 20.5, z: 34.2, face: 0 }
  ]
};
const out = path.join(here, '../data/layout.json');
fs.writeFileSync(out, JSON.stringify(layout, null, 1));
console.log('已寫出', out, '家具', furniture.length, '房間', rooms.length, '牆', walls.length);
