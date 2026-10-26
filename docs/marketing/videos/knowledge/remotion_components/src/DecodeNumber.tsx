import React from 'react';
import {interpolate, random, useCurrentFrame} from 'remotion';
import {C, FONT, W} from './theme';

export type DecodeNumberProps = {
  text: string;                 // 例如 "+38.6%"
  startFrame?: number;
  durationInFrames?: number;    // 預設 90 = 3 秒
  color?: string;               // 解碼完成後的顏色（漲＝紅）
  fontSize?: number;
  centerY?: number;
  seed?: number;
};

const POOL = '0123456789#%@&$+-*=?';
export const cell = (ch: string) => (ch === '.' ? 0.34 : ch === '%' ? 0.92 : ch === '+' || ch === '-' ? 0.62 : 0.66);

// 013 亂碼解讀（數字版）。每 2 幀換一次亂碼，由左至右逐位鎖定。
export const DecodeNumber: React.FC<DecodeNumberProps> = ({
  text, startFrame = 0, durationInFrames = 90, color = C.UP, fontSize = 230, centerY = 960, seed = 7,
}) => {
  const frame = useCurrentFrame();
  const f = frame - startFrame;
  if (f < 0) return null;
  const chars = Array.from(text);
  const LOCK0 = 18, STEP = 5; // 第 18 幀鎖第一位，之後每 5 幀鎖一位
  const tick = Math.floor(f / 2);
  const total = chars.reduce((s, c) => s + cell(c), 0) * fontSize;
  return (
    <div style={{position: 'absolute', left: (W - total) / 2, top: centerY - fontSize * 0.7, display: 'flex',
      fontFamily: FONT, fontWeight: 900, fontSize, lineHeight: 1.4, height: fontSize * 1.4}}>
      {chars.map((ch, i) => {
        const lockAt = LOCK0 + i * STEP;
        const locked = f >= lockAt;
        const out = locked ? ch : (ch === '.' ? '.' : POOL[Math.floor(random(`${seed}-${i}-${tick}`) * POOL.length)]);
        const pop = locked ? interpolate(f - lockAt, [0, 3, 8], [1.14, 0.98, 1], {extrapolateRight: 'clamp'}) : 1;
        return (
          <span key={i} style={{display: 'inline-block', width: cell(ch) * fontSize, textAlign: 'center',
            color: locked ? color : C.MUTED, opacity: locked ? 1 : 0.8,
            transform: `scale(${pop})`, transformOrigin: '50% 60%'}}>{out}</span>
        );
      })}
    </div>
  );
};
