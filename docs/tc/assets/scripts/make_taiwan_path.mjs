// 台灣本島＋澎湖輪廓與縣市界：npm `taiwan-atlas@2021.9.20`（MIT）的 counties-10t.json，
// 資料原始來源 內政部國土測繪中心「直轄市、縣市界線(TWD97經緯度)」（data.gov.tw，政府資料開放授權條款－第1版，使用須標示來源）。
// 輪廓與縣市界取自同一份資料，海岸線和縣市線才對得齊；不含金門、連江。
// 用法：npm i taiwan-atlas@2021.9.20 topojson-client@3.1.0 d3-geo@3.1.1 && node make_taiwan_path.mjs > taiwan_path.json
import fs from 'fs';
import * as topo from 'topojson-client';
import {geoMercator, geoPath} from 'd3-geo';
const t = JSON.parse(fs.readFileSync('node_modules/taiwan-atlas/counties-10t.json'));
const all = t.objects.counties.geometries;
const keep = all.filter(g => !/金門|連江/.test(g.properties.COUNTYNAME || g.properties.NAME || ''));
const obj = {type: 'GeometryCollection', geometries: keep};
// 只留本島、澎湖與台灣周邊小島（龜山島、綠島、蘭嶼、小琉球）；高雄市轄的東沙、南沙離太遠，排除
const inBox = c => c[0] > 119.2 && c[0] < 122.2 && c[1] > 21.7 && c[1] < 25.5;
const land0 = topo.merge(t, keep), mesh0 = topo.mesh(t, obj, (a, b) => a !== b);
const land = {type: 'MultiPolygon', coordinates: land0.coordinates.filter(p => inBox(p[0][0]))};
const mesh = {type: 'MultiLineString', coordinates: mesh0.coordinates.filter(l => inBox(l[0]))};
const feat = {type: 'Feature', geometry: land};
const H = 1000;
const p0 = geoMercator().fitExtent([[0, 0], [10000, H]], feat);
const b0 = geoPath(p0).bounds(feat);
const w = Math.ceil(b0[1][0] - b0[0][0]), h = Math.ceil(b0[1][1] - b0[0][1]);
const proj = geoMercator().fitExtent([[0, 0], [w, h]], feat);
const path = geoPath(proj).digits(1);
console.log(JSON.stringify({w, h, land: path(feat), borders: path(mesh), pt: proj([121.36, 25.03]), src: 'taiwan-atlas@2021.9.20 counties-10t (MIT); 內政部國土測繪中心 直轄市、縣市界線 (政府資料開放授權條款第1版)'}));
