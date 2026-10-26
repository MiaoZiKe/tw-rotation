import React from 'react';
import {Composition} from 'remotion';
import {Demo, Ex1, Ex2, Ex3} from './Compositions';
import {FontGate} from './FontGate';

const wrap = (C: React.FC) => () => <FontGate><C /></FontGate>;
const common = {fps: 30, width: 1080, height: 1920};
export const Root: React.FC = () => (
  <>
    <Composition id="Ex1" component={wrap(Ex1)} durationInFrames={72} {...common} />
    <Composition id="Ex2" component={wrap(Ex2)} durationInFrames={90} {...common} />
    <Composition id="Ex3" component={wrap(Ex3)} durationInFrames={105} {...common} />
    <Composition id="Demo" component={wrap(Demo)} durationInFrames={240} {...common} />
  </>
);
