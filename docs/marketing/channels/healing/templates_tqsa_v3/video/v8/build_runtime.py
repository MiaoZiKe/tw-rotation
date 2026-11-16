#!/usr/bin/env python3
"""（v8：字幕斷行在逗號處的門檻由 1/3 放寬到 1/4，避免把數字從中間切開。）
組出 video_runtime_v8.js：v7 的共用工具（緩動、標題、標籤、字幕、出處、片尾 LOGO、背景、轉場、renderAt）＋ v8 通用鏡型（_charts.js）＋ v8 音效事件（_sfx.js）。
插圖另外放 ill_<篇>.js（每篇量身，素材不跨篇），HTML 依序載入 ill 檔與本檔。用法：python3 v8/build_runtime.py"""
import os
B = os.path.dirname(os.path.abspath(__file__)); V7 = open(os.path.join(B, "..", "video_runtime_v7.js"), encoding="utf-8").read().split("\n")
L = lambda a, b: "\n".join(V7[a - 1:b])
hdr = "// 談晴說礙 數據短影音執行期 v8（2026-11-16 總編輯）＝v7 共用工具與片尾 LOGO（不動）＋通用鏡型（資料驅動）＋每篇量身插圖（ill_<篇>.js 註冊到 ILL）。由 v8/build_runtime.py 產生，不要手改。\n"
out = hdr + L(15, 55).replace("<s.length/3)best=Math.ceil(m)", "<s.length/4)best=Math.ceil(m)").replace("transform:scale(${sc.toFixed(3)}) rotate(", "transform:translateY(${beatHop(lt,0).toFixed(1)}px) scale(${sc.toFixed(3)}) rotate(") + "\n" + L(206, 207) + "\n" + open(os.path.join(B, "_charts.js"), encoding="utf-8").read().rstrip() + "\n" + L(159, 199) + "\n};\nconst SC=SCV;\n" + L(456, 477) + "\n" + open(os.path.join(B, "_render.js"), encoding="utf-8").read() + open(os.path.join(B, "_sfx.js"), encoding="utf-8").read()
open(os.path.join(B, "..", "video_runtime_v8.js"), "w", encoding="utf-8").write(out); print("video_runtime_v8.js", len(out))
