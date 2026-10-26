import React from 'react';
import {Img, staticFile, useCurrentFrame} from 'remotion';

// 006 心跳放大（比比待機）：每 loopFrames 影格一組「咚咚」雙脈衝，frame % loopFrames 首尾無縫。
// 幅度 ±7%，不是閃爍；mode='pendulum' 為 026 鐘擺搖晃（±5 度，週期 2 秒）。
export const Bibi: React.FC<{x: number; bottom: number; size?: number; startFrame?: number; mode?: 'heart' | 'pendulum'; loopFrames?: number}> =
({x, bottom, size = 300, startFrame = 0, mode = 'heart', loopFrames = 30}) => {
  const frame = useCurrentFrame();
  const f = frame - startFrame;
  if (f < 0) return null;
  const t = f % loopFrames;
  const bump = (c: number, w: number) => { const d = (t - c) / w; return Math.abs(d) < 1 ? Math.cos(d * Math.PI / 2) ** 2 : 0; };
  const s = mode === 'heart' ? 1 + 0.07 * Math.max(bump(4, 4), 0.65 * bump(11, 4)) : 1;
  const rot = mode === 'pendulum' ? 5 * Math.sin((2 * Math.PI * (f % loopFrames)) / loopFrames) : 0;
  return (
    <Img src={staticFile('bibi/key.png')} style={{position: 'absolute', left: x - size / 2, top: 1920 - bottom - size, width: size, height: size,
      transform: `scale(${s}) rotate(${rot}deg)`, transformOrigin: '50% 90%'}} />
  );
};
