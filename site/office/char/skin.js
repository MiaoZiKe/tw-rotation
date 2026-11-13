// 複製帶骨架的角色（SkeletonUtils.clone 的精簡版；vendor 裡沒有那支，所以自己寫）。
// 幾何、材質共用，骨頭與形態鍵權重各自獨立。
import * as THREE from 'three';
export function cloneSkinned(source) {
  const clone = source.clone(true), cb = {};
  clone.traverse(n => { if (n.isBone) cb[n.name] = n; });
  const src = [], dst = [];
  source.traverse(n => { if (n.isSkinnedMesh) src.push(n); }); clone.traverse(n => { if (n.isSkinnedMesh) dst.push(n); });
  src.forEach((s, i) => {
    const bones = s.skeleton.bones.map(b => cb[b.name]);
    dst[i].bind(new THREE.Skeleton(bones, s.skeleton.boneInverses.map(m => m.clone())), s.bindMatrix);
  });
  return clone;
}
