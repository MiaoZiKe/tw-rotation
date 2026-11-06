// 第 2 張地圖加料用的資料：npm `taiwan-atlas@2021.9.20`（MIT）的 towns-10t.json（原始來源：內政部國土測繪中心「鄉(鎮、市、區)界線」，
// 政府資料開放授權條款－第1版，使用須標示來源）。輸出 towns_path.json：
//  ① refs：科技重鎮參考點（用與 taiwan_path.json 相同的投影算出 x,y）；② grat：海面淡經緯網格；③ inset：桃園市各區界與龜山區（獨立縮放到小框）。
// 參考點座標（WGS84，公開地標常識值）：新竹科學園區 24.78N,121.01E；中部科學園區（台中）24.22N,120.62E；南部科學園區（台南）23.10N,120.28E；台北車站 25.05N,121.52E。
// 用法（在放有 node_modules 的資料夾）：npm i taiwan-atlas@2021.9.20 topojson-client@3.1.0 d3-geo@3.1.1 && node make_towns.mjs > towns_path.json
import fs from 'fs';
import * as topo from 'topojson-client';
import {geoMercator, geoPath, geoGraticule} from 'd3-geo';
const c = JSON.parse(fs.readFileSync('node_modules/taiwan-atlas/counties-10t.json'));
const keep = c.objects.counties.geometries.filter(g => !/金門|連江/.test(g.properties.COUNTYNAME || g.properties.NAME || ''));
const inBox = x => x[0] > 119.2 && x[0] < 122.2 && x[1] > 21.7 && x[1] < 25.5;
const land0 = topo.merge(c, keep);
const land = {type: 'MultiPolygon', coordinates: land0.coordinates.filter(p => inBox(p[0][0]))};
const feat = {type: 'Feature', geometry: land};
const p0 = geoMercator().fitExtent([[0, 0], [10000, 1000]], feat);
const b0 = geoPath(p0).bounds(feat);
const w = Math.ceil(b0[1][0] - b0[0][0]), h = Math.ceil(b0[1][1] - b0[0][1]);
const proj = geoMercator().fitExtent([[0, 0], [w, h]], feat);
const refs = [['竹科', 121.01, 24.78], ['中科', 120.62, 24.22], ['南科', 120.28, 23.10], ['台北', 121.52, 25.05]].map(([n, lo, la]) => ({n, x: +proj([lo, la])[0].toFixed(1), y: +proj([lo, la])[1].toFixed(1)}));
const grat = geoGraticule().extent([[118.5, 21], [123, 26.5]]).step([1, 1]).precision(1)();
const gpath = geoPath(proj).digits(1)(grat);
const t = JSON.parse(fs.readFileSync('node_modules/taiwan-atlas/towns-10t.json'));
const ty = t.objects.towns.geometries.filter(g => g.properties.COUNTYNAME === '桃園市');
const tyObj = {type: 'GeometryCollection', geometries: ty};
const tyFeat = topo.feature(t, tyObj);
const W = 250, H = 215;
const ip = geoMercator().fitExtent([[6, 6], [W - 6, H - 6]], tyFeat);
const ipath = geoPath(ip).digits(1);
const gs = ty.filter(g => g.properties.TOWNNAME === '龜山區');
const gsFeat = topo.feature(t, {type: 'GeometryCollection', geometries: gs});
const mesh = topo.mesh(t, tyObj, (a, b) => a !== b);
const outline = topo.merge(t, ty);
console.log(JSON.stringify({w, h, refs, grat: gpath, inset: {W, H, land: ipath(outline), borders: ipath(mesh), guishan: ipath(gsFeat), gs_c: ipath.centroid(gsFeat).map(v => +v.toFixed(1))},
  src: 'taiwan-atlas@2021.9.20 towns-10t (MIT); 內政部國土測繪中心 鄉(鎮、市、區)界線 (政府資料開放授權條款第1版)'}));
