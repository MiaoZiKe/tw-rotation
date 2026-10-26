import React from 'react';
import {Easing, interpolate, random, useCurrentFrame} from 'remotion';
import {C, FONT, W} from './theme';

export const LH = 1.25; // 行高倍率（Canvas 取樣版面也用同一個）

export type LightningSlamProps = {
  text: string;                 // 以 \n 換行
  startFrame?: number;          // 效果開始的影格
  durationInFrames?: number;    // 此效果的長度（預設 72 = 2.4 秒 @30fps）
  color?: string;               // 文字顏色
  glowColor?: string;           // 外發光顏色（只在字外圍，很淡）
  fontSize?: number;
  startScale?: number;          // 砸落前的放大倍數（1080 寬限制，預設 1.8）
  centerY?: number;
  seed?: number;
};

// 001 閃電砸落。拆解表見 remotion_components/拆解表.md
export const LightningSlam: React.FC<LightningSlamProps> = ({
  text, startFrame = 0, durationInFrames = 72, color = C.TXT, glowColor = C.TEAL,
  fontSize = 108, startScale = 1.8, centerY = 960, seed = 1,
}) => {
  const frame = useCurrentFrame();
  const f = frame - startFrame;
  if (f < 0) return null;
  const lines = text.split('\n');

  // 時機（影格，相對 startFrame；全部以 30fps 為基準，用 fps 比例換算寫在拆解表）
  const FLASH1 = 4, FLASH2 = 16, SLAM = 20, LAND = 25, GLOW = 30;
  const flash = (t: number) => interpolate(f, [t, t + 2, t + 7], [0, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const flashA = Math.max(flash(FLASH1), flash(FLASH2));

  // 閃電折線：固定 seed，每次閃光形狀不同但可重現
  const bolt = (n: number) => {
    const pts: string[] = [];
    let x = W / 2 + (random(`b${seed}${n}`) - 0.5) * 300;
    for (let i = 0; i <= 9; i++) {
      const y = (centerY - 760) + i * ((760 - 40) / 9);
      x += (random(`bx${seed}${n}${i}`) - 0.5) * 150;
      x = x * 0.8 + (W / 2) * 0.2;
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    return pts.join(' ');
  };
  const boltN = f >= FLASH2 ? 2 : 1;
  const boltA = f >= FLASH2 ? flash(FLASH2) : flash(FLASH1);

  // 砸落：2 幀內出現，5 幀縮回；落地後阻尼彈一下
  const slamScale = interpolate(f, [SLAM, LAND], [startScale, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic),
  });
  const g = Math.max(0, f - LAND);
  const bounce = f >= LAND ? 1 + 0.045 * Math.exp(-g / 4) * Math.sin(g * 1.3) : 1;
  const textA = f >= SLAM ? 1 : 0; // 硬切出現，不用半透明漸變（避免糊）
  const shake = f >= LAND ? 16 * Math.exp(-g / 4) : 0;
  const sx = shake * Math.sin(g * 2.6);
  const sy = shake * 0.6 * Math.cos(g * 2.1);
  // 震波：細線外擴
  const ringT = interpolate(f, [LAND, LAND + 15], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const ringA = f >= LAND && f < LAND + 15 ? 0.55 * (1 - ringT) : 0;
  // 柔和外發光：淡入後保持不動（不脈動）
  const glowA = interpolate(f, [GLOW, GLOW + 12], [0, 0.45], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const blockH = lines.length * fontSize * LH;
  const base: React.CSSProperties = {
    position: 'absolute', left: 0, width: W, top: centerY - blockH / 2, textAlign: 'center',
    fontFamily: FONT, fontWeight: 900, fontSize, lineHeight: LH,
    transform: `translate(${sx}px, ${sy}px) scale(${slamScale * bounce})`,
    transformOrigin: `${W / 2}px ${blockH / 2}px`, whiteSpace: 'pre', opacity: textA,
  };

  return (
    <div style={{position: 'absolute', inset: 0}}>
      {/* 閃光：局部放射（最大不透明度 0.35），不是整片白 */}
      <div style={{position: 'absolute', left: W / 2 - 520, top: centerY - 520, width: 1040, height: 1040,
        borderRadius: 520, opacity: flashA * 0.35,
        background: `radial-gradient(circle, #e8fffb 0%, ${C.TEAL}55 45%, transparent 70%)`}} />
      <svg width={W} height={1920} style={{position: 'absolute', inset: 0, opacity: boltA}}>
        <polyline points={bolt(boltN)} fill="none" stroke="#eafffb" strokeWidth={6} strokeLinejoin="round" />
        <polyline points={bolt(boltN)} fill="none" stroke={C.TEAL} strokeWidth={14} strokeLinejoin="round" opacity={0.35} />
      </svg>
      <svg width={W} height={1920} style={{position: 'absolute', inset: 0, opacity: ringA}}>
        <ellipse cx={W / 2} cy={centerY} rx={330 + 210 * ringT} ry={190 + 140 * ringT} fill="none" stroke={glowColor} strokeWidth={3} />
      </svg>
      {/* 外發光層在字下面（只有 10px 淡影），字本身在最上層保持銳利 */}
      <div style={{...base, color: 'transparent', textShadow: `0 0 10px ${glowColor}`, opacity: textA * glowA}}>{text}</div>
      <div style={{...base, color}}>{text}</div>
    </div>
  );
};
