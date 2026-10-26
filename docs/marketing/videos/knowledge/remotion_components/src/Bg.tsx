import React from 'react';
import {AbsoluteFill} from 'remotion';
import {C} from './theme';

// 純深色底＋極淡格線（靜態、不當主視覺；不用 015 漸層流動）
export const Bg: React.FC = () => (
  <AbsoluteFill style={{background: C.BG}}>
    <AbsoluteFill
      style={{
        backgroundImage: `linear-gradient(${C.GRID}55 1px, transparent 1px), linear-gradient(90deg, ${C.GRID}55 1px, transparent 1px)`,
        backgroundSize: '90px 90px',
      }}
    />
  </AbsoluteFill>
);
