// 被點選時「面向我」（擁有者 11-13：「我點擊該角色，他會面向我」）。
//
// 規則（照角色當下在做什麼分開處理，全部都是「選取期間」的暫時狀態，取消選取後回到原本的朝向與行為）：
//   站著        以最短角度轉身，約 0.3 秒，面向「鏡頭在地面上的方向」；選取期間鏡頭移動，他的朝向與視線持續跟著。
//   坐著        不離座、位置不動：轉椅子（身體朝向）面向鏡頭，最多轉到座位朝向的左右各 100 度（再多身體會別著桌子），
//               超過的部分靠頭與眼睛看過去；取消後椅子轉回原本的朝向。
//   走路中      停下腳步轉身面向鏡頭；取消選取後從原地繼續走原本的路（不是重新規劃）。
//   開會中      只轉頭看（身體留在會議的位置，不打斷討論）。
//   睡覺中      不叫醒（額度用完全員趴睡也是同一條規則）：只精神一振地動一下，當作「被注意到」；不轉身、不睜眼。
//   進入操控後  朝向改由移動方向決定（pilot.js），這裡不再管；角色視角（pov.js）時也不管。
// 「被注意到」的反應：選取的當下精神一振（身體微彈）＋開心的眼神，只做一次，不打斷手上的動作。
// 眼睛一律看向鏡頭（頭與眼球轉過去，角色底層有上限所以不會轉成貓頭鷹）。
import * as THREE from 'three';

const SEAT_LIM = 1.75;                                   // 坐著時身體最多轉離座位朝向的角度（弧度，約 100 度）
const angDiff = (a, b) => Math.atan2(Math.sin(a - b), Math.cos(a - b));
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

export function createAttention(W, X) {
  const A = { c: null, mode: '', saved: null, reacts: 0 }, camera = X.camera, pilot = X.pilot, D = () => X.director();
  const inMeeting = c => { const m = D().meeting; return !!(m && m.people.includes(c)); };

  function begin(c) {
    A.c = c; A.mode = ''; A.saved = { heading: c.heading, seated: c.state === 'sit' };
    A.reacts++; c.perk();                                // 被注意到：只在選取的那一下
  }
  function end(c, keepHeading) {
    c.lookAt(null); c.pause(false);
    if (!keepHeading && !c.piloted) {
      if (c.state === 'sit') c.swivel(null);
      else if (c.state === 'stand' && A.saved) c.heading = A.saved.heading;     // 站著的人轉回原本朝向；他若已經走開（state 不是 stand）就不管
    }
    A.c = null; A.mode = ''; A.saved = null;
  }

  A.frame = () => {
    const sel = pilot.sel, pov = W.pov && W.pov.on() ? W.pov.c : null;
    const want = sel && !sel.jobless && !sel.away && !sel.spec.pet && sel !== pov && !pilot.engaged && !sel.piloted ? sel : null;
    if (want !== A.c) { if (A.c) end(A.c, pilot.engaged && A.c === sel); if (want) begin(want); }
    const c = A.c; if (!c) return;
    const p = c.object3D.position, cp = camera.position;
    c.lookAt(cp);                                        // 眼睛與頭：一律看向鏡頭
    const dx = cp.x - p.x, dz = cp.z - p.z; if (dx * dx + dz * dz < 0.09) return;    // 鏡頭就在頭頂正上方時方向不明，不動
    const ty = Math.atan2(dx, dz);                       // 角色 → 鏡頭 的水平方向（與角色朝向同一套角度：0 ＝ +z）
    if (inMeeting(c)) { A.mode = 'meeting'; return; }                                        // 開會中：只轉頭
    if (c.sleeping || c.action === 'sleep' || c.inner.mode === 'sleep') { A.mode = 'sleep'; return; }   // 睡覺中：不叫醒
    if (c.state === 'sit') { A.mode = 'sit'; const seat = c._seat; if (seat) c.swivel(seat.face + clamp(angDiff(ty, seat.face), -SEAT_LIM, SEAT_LIM)); return; }
    if (c.state === 'walk') { if (!c._hop) { A.mode = 'walk'; c.pause(true); c.heading = ty; } return; }
    if (c.state === 'stand') { A.mode = 'stand'; c.pause(false); c.heading = ty; }
  };
  A.current = () => A.c;
  return A;
}
