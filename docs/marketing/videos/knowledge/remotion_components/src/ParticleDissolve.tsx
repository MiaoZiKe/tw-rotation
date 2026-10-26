import React, {useEffect, useMemo, useRef} from 'react';
import {interpolate, random, useCurrentFrame} from 'remotion';
import {FONT, H, W} from './theme';

export type DissolveLine = {text: string; size: number; color: string; centerY: number; weight?: number; mono?: (ch: string) => number};

export type ParticleDissolveProps = {
  lines: DissolveLine[];
  startFrame: number;            // 開始消散的影格
  durationInFrames?: number;     // 消散長度，預設 24（0.8 秒）
  showStaticBefore?: boolean;    // 消散前由 Canvas 畫整齊的字（ex3 用）；demo 由 DOM 元件負責則設 false
  seed?: number;
};

const STEP = 4;

// 005 粒子消散：字由 Canvas 取樣成 4px 方塊，由左至右依序飛散，固定 seed 可重現。
export const ParticleDissolve: React.FC<ParticleDissolveProps> = ({
  lines, startFrame, durationInFrames = 24, showStaticBefore = true, seed = 3,
}) => {
  const frame = useCurrentFrame();
  const ref = useRef<HTMLCanvasElement>(null);

  const draw = (ctx: CanvasRenderingContext2D) => {
    for (const l of lines) {
      ctx.font = `${l.weight ?? 900} ${l.size}px ${FONT}`;
      ctx.fillStyle = l.color;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      put(ctx, l);
    }
  };

  const cells = useMemo(() => {
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    const ctx = c.getContext('2d', {willReadFrequently: true})!;
    const out: {x: number; y: number; a: number; col: string; d: number; vx: number; vy: number}[] = [];
    let n = 0;
    lines.forEach((l, li) => {
      ctx.clearRect(0, 0, W, H);
      draw1(ctx, l);
      const y0 = Math.max(0, Math.floor(l.centerY - l.size)), y1 = Math.min(H, Math.ceil(l.centerY + l.size));
      const img = ctx.getImageData(0, y0, W, y1 - y0).data;
      for (let y = 0; y < y1 - y0; y += STEP) for (let x = 0; x < W; x += STEP) {
        let aMax = 0;
        for (let dy = 0; dy < STEP && y + dy < y1 - y0; dy++) for (let dx = 0; dx < STEP; dx++) aMax = Math.max(aMax, img[((y + dy) * W + x + dx) * 4 + 3]);
        if (aMax < 24) continue;
        out.push({x, y: y + y0, a: aMax / 255, col: l.color, d: x / W, vx: random(`vx${seed}${n}`) - 0.35, vy: random(`vy${seed}${n}`), });
        n++;
      }
      void li;
    });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const ctx = ref.current!.getContext('2d')!;
    ctx.clearRect(0, 0, W, H);
    const f = frame - startFrame;
    if (f < 0) { if (showStaticBefore) draw(ctx); return; }
    if (f >= durationInFrames + 10) return;
    draw(ctx);
    const span = durationInFrames * 0.55;           // 發動時間分散在前 55%
    const life = durationInFrames * 0.45;           // 每顆飛行時間
    const minX = Math.min(...cells.map((c) => c.x)), maxX = Math.max(...cells.map((c) => c.x));
    cells.forEach((c, i) => {
      const t0 = ((c.x - minX) / (maxX - minX + 1)) * span * 0.8 + random(`dl${seed}${i}`) * span * 0.2;
      const t = (f - t0) / life;
      if (t <= 0) return;
      ctx.clearRect(c.x, c.y, STEP, STEP);          // 已離開的位置挖掉，剩下的字仍是銳利原字
      if (t >= 1) return;
      const px = c.x + c.vx * 340 * t;
      const py = c.y - c.vy * 260 * t + 520 * t * t;
      ctx.globalAlpha = c.a * (1 - t * t);
      ctx.fillStyle = c.col;
      const s = STEP * (1 - 0.45 * t);
      ctx.fillRect(px, py, s, s);
      ctx.globalAlpha = 1;
    });
    // 這裡的顏色以各行顏色為準
  }, [frame]);

  function draw1(ctx: CanvasRenderingContext2D, l: DissolveLine) {
    ctx.font = `${l.weight ?? 900} ${l.size}px ${FONT}`;
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    put(ctx, l);
  }
  function put(ctx: CanvasRenderingContext2D, l: DissolveLine) {
    const y = l.centerY + CANVAS_DY * l.size;
    if (!l.mono) { ctx.fillText(l.text, W / 2, y); return; }
    const chars = Array.from(l.text);
    const total = chars.reduce((s, c) => s + l.mono!(c), 0) * l.size;
    let x = (W - total) / 2;
    for (const c of chars) { const w = l.mono(c) * l.size; ctx.fillText(c, x + w / 2, y); x += w; }
  }
  return <canvas ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0}} />;
};

// Canvas 'middle' 基線與 DOM 行盒置中的垂直差，實測校正（見 校正記錄）
export const CANVAS_DY = 0.0;
