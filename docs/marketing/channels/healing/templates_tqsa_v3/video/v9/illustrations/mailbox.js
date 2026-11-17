 mailbox:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><rect x="0" y="${h-70}" width="888" height="70" fill="#CDB896"/>`;
  g+=`<line x1="444" y1="${h-70}" x2="444" y2="250" stroke="${LINE}" stroke-width="12"/><path d="M300 250 v-120 q0 -90 144 -90 q144 0 144 90 v120Z" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/>`;
  const dr=-35*SPR(t-.9,.5,10);g+=`<g transform="rotate(${dr.toFixed(1)} 300 250)"><path d="M300 250 v-120 q0 -90 30 -90 v210Z" fill="#9C6A50" stroke="${LINE}" stroke-width="3"/></g>`;
  const fa=-90*SPR(t-.4,.38,13);g+=`<g transform="rotate(${fa.toFixed(1)} 600 200)"><rect x="596" y="196" width="140" height="12" fill="${LINE}"/><rect x="700" y="170" width="50" height="40" fill="${LAMP}" stroke="${LINE}" stroke-width="2"/></g>`;
  g+=`<rect x="380" y="270" width="128" height="50" rx="8" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,306,'號 ?',32,700,TXT);
  const sw=6*Math.sin(t*1.6);g+=`<path d="M60 ${h-70} v-200" stroke="#8A6A52" stroke-width="14"/><circle cx="${60+sw}" cy="${h-300}" r="70" fill="#9CB38A" opacity=".85"/><circle cx="${110+sw*1.2}" cy="${h-260}" r="50" fill="#8FA078" opacity=".85"/>`;
  return g},
  sfx(t0,s,E){E(t0+.4,'click');E(t0+.9,'glide',{f0:400,f1:250,dur:.3,g:.07})}}
