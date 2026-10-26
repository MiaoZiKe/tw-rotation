import React from 'react';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Bg} from './Bg';
import {Bibi} from './Bibi';
import {cell, DecodeNumber} from './DecodeNumber';
import {LightningSlam, LH} from './LightningSlam';
import {ParticleDissolve} from './ParticleDissolve';
import {C, FONT, W} from './theme';

const T = '練習用示意數字，非實際資料';
const Label: React.FC<{text: string; y: number; color?: string}> = ({text, y, color = C.MUTED}) => (
  <div style={{position: 'absolute', left: 0, width: W, top: y, textAlign: 'center', fontFamily: FONT, fontWeight: 700, fontSize: 48, color}}>{text}</div>
);

// 練習 1：001 閃電砸落，2.4 秒 = 72 幀
export const Ex1: React.FC = () => (
  <AbsoluteFill><Bg />
    <LightningSlam text={'AI 伺服器\n出貨創新高'} startFrame={0} durationInFrames={72} />
  </AbsoluteFill>
);

// 練習 2：013 亂碼解讀（數字版），3 秒 = 90 幀
export const Ex2: React.FC = () => (
  <AbsoluteFill><Bg />
    <Label text="近一季漲幅" y={560} color={C.TXT} />
    <DecodeNumber text="+38.6%" startFrame={6} durationInFrames={84} color={C.UP} />
    <Label text={T} y={1180} />
  </AbsoluteFill>
);

// 練習 3：005 粒子消散轉場，3.5 秒 = 105 幀。A 先完整停留 36 幀（1.2 秒），24 幀消散，B 在第 60 幀進場
const A_LINES = [
  {text: 'AI 伺服器', size: 108, color: C.TXT, centerY: 960 - 67.5},
  {text: '出貨創新高', size: 108, color: C.TXT, centerY: 960 + 67.5},
];
const SceneB: React.FC<{start: number}> = ({start}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const f = frame - start;
  if (f < 0) return null;
  const s = spring({frame: f, fps, config: {damping: 14, stiffness: 140}});
  const y = interpolate(s, [0, 1], [60, 0]);
  return (
    <div style={{position: 'absolute', left: 0, width: W, top: 960 - 135, textAlign: 'center', fontFamily: FONT, fontWeight: 900,
      fontSize: 108, lineHeight: LH, color: C.TEAL, whiteSpace: 'pre', opacity: interpolate(f, [0, 6], [0, 1], {extrapolateRight: 'clamp'}),
      transform: `translateY(${y}px)`}}>{'供應鏈\n跟著動'}</div>
  );
};
export const Ex3: React.FC = () => (
  <AbsoluteFill><Bg />
    <ParticleDissolve lines={A_LINES} startFrame={36} durationInFrames={24} seed={3} />
    <SceneB start={60} />
  </AbsoluteFill>
);

// 綜合示範 8 秒 = 240 幀
const CARDS = ['零組件：散熱、電源', '封裝與載板', '後續觀察：訂單能見度'];
const Scene2: React.FC<{start: number}> = ({start}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const f = frame - start;
  if (f < 0) return null;
  const head = interpolate(f, [0, 8], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 0, width: W, top: 380, textAlign: 'center', fontFamily: FONT, fontWeight: 900, fontSize: 100,
        color: C.TEAL, opacity: head, transform: `translateY(${(1 - head) * 40}px)`}}>接著看供應鏈</div>
      {CARDS.map((t, i) => {
        const s = spring({frame: f - 8 - i * 8, fps, config: {damping: 15, stiffness: 150}});
        return (
          <div key={i} style={{position: 'absolute', left: 90, width: 900, top: 560 + i * 210, height: 170, borderRadius: 28,
            background: C.CARD, border: `2px solid ${C.GRID}`, display: 'flex', alignItems: 'center', paddingLeft: 48,
            fontFamily: FONT, fontWeight: 700, fontSize: 56, color: C.TXT, opacity: Math.min(1, s * 1.4),
            transform: `translateX(${(1 - s) * 140}px)`}}>
            <span style={{color: C.ORANGE, marginRight: 24}}>{i + 1}</span>{t}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
const TITLE_Y = 560;
export const Demo: React.FC = () => {
  const frame = useCurrentFrame();
  const DIS = 150;
  const NUMY = 1010;
  return (
    <AbsoluteFill><Bg />
      {frame < DIS && <>
        <LightningSlam text={'AI 伺服器\n出貨創新高'} startFrame={0} durationInFrames={72} centerY={TITLE_Y} />
        <DecodeNumber text="+38.6%" startFrame={78} durationInFrames={72} color={C.UP} centerY={NUMY} />
        {frame >= 78 && <Label text={T} y={NUMY + 190} />}
      </>}
      <ParticleDissolve showStaticBefore={false} startFrame={DIS} durationInFrames={24} seed={5}
        lines={[
          {text: 'AI 伺服器', size: 108, color: C.TXT, centerY: TITLE_Y - 67.5},
          {text: '出貨創新高', size: 108, color: C.TXT, centerY: TITLE_Y + 67.5},
          {text: '+38.6%', size: 230, color: C.UP, centerY: NUMY + 230 * 0.0, mono: cell},
        ]} />
      <Scene2 start={DIS + 18} />
      <Bibi x={540} bottom={260} size={300} startFrame={20} mode="heart" loopFrames={30} />
    </AbsoluteFill>
  );
};
