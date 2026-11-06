// 由 world-atlas@2.0.2（ISC 授權；資料 Natural Earth，公有領域）的 countries-50m 取出台灣本島輪廓，
// 以麥卡托投影轉成 SVG path；另算桃園龜山（北緯 25.03、東經 121.36）的點位。
// 用法：npm i world-atlas@2.0.2 topojson-client@3.1.0 d3-geo@3.1.1 && node make_taiwan_path.mjs > taiwan_path.json
import fs from 'fs';
import * as topo from 'topojson-client';
import {geoMercator, geoPath} from 'd3-geo';
const t = JSON.parse(fs.readFileSync('node_modules/world-atlas/countries-50m.json'));
const g = t.objects.countries.geometries.filter(x => x.properties.name === 'Taiwan');
const geom = topo.feature(t, {type: 'GeometryCollection', geometries: g}).features[0].geometry;
const polys = geom.type === 'MultiPolygon' ? geom.coordinates : [geom.coordinates];
const main = polys.reduce((a, b) => (b[0].length > a[0].length ? b : a));   // 本島（另一塊是金門）
const feat = {type: 'Feature', geometry: {type: 'Polygon', coordinates: main}};
const H = 1000;
const proj = geoMercator().fitExtent([[0, 0], [10000, H]], feat);
const b = geoPath(proj).bounds(feat);
const w = Math.ceil(b[1][0] - b[0][0]) + 0, h = Math.ceil(b[1][1] - b[0][1]);
const proj2 = geoMercator().fitExtent([[0, 0], [w, h]], feat);
const p2 = geoPath(proj2);
const bb = p2.bounds(feat);
const pt = proj2([121.36, 25.03]);
console.log(JSON.stringify({w, h, d: p2(feat), pt, bounds: bb, src: 'world-atlas@2.0.2 countries-50m (ISC; Natural Earth, public domain)'}));
