import React, {useEffect, useState} from 'react';
import {continueRender, delayRender, staticFile} from 'remotion';
import {FONT} from './theme';

// 先把字型載好才渲染（Canvas 取樣與 DOM 都要用同一套字型）
export const FontGate: React.FC<{children: React.ReactNode}> = ({children}) => {
  const [ready, setReady] = useState(false);
  const [handle] = useState(() => delayRender('載入 Noto Sans TC'));
  useEffect(() => {
    const faces = [
      new FontFace(FONT, `url(${staticFile('fonts/NotoSansTC-Bold.ttf')})`, {weight: '700'}),
      new FontFace(FONT, `url(${staticFile('fonts/NotoSansTC-Black.ttf')})`, {weight: '900'}),
    ];
    Promise.all(faces.map((f) => f.load())).then((loaded) => {
      loaded.forEach((f) => document.fonts.add(f));
      setReady(true);
      continueRender(handle);
    });
  }, [handle]);
  return ready ? <>{children}</> : null;
};
