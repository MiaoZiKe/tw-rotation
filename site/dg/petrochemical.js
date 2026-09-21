/* 輕油裂解 —— docs/diagram_plan.md 的第 13 張（族群 `petrochemical`、traditional 鏈）

   ★ 還沒畫。這個檔目前**不呼叫 `window.DG.register`**，
     所以 SLOTS 裡不會多出一個畫不出東西的空項目，
     圖別選單上也不會出現「點了沒反應」的入口。

   畫的時候：
     1. 先讀 `docs/diagram_specs/naphtha_cracker.md`（規格書就是合約，要不要 3D 在 §0 已經寫死）
     2. 用 `window.DG` 的共用工具（STYLE / labelRow / processBar / stampParts / p3 …），
        **不要自己造第二套**，也不要在 JS 裡寫死色值 —— 一律走 `--dg-*`
     3. 字級下限 12px：`--dg-fs-ttl` 16 / `--dg-fs-hd` 13.5 / `--dg-fs-lbl` 12.5 / `--dg-fs-min` 12
     4. 畫布 **980 寬**、宣告 `native: 980`（DECISIONS #227：欄寬才是字級守不住的根因）
     5. 最後在檔尾註冊：

        window.DG.register('petrochemical', {
          level: 'group', chain: 'traditional',
          name: '…', draw: <你的函式>, native: 980, scene: null,
          q: '這張圖回答什麼問題（會印在圖別選單與標題上）',
        });

   ⚠ `site/index.html` 已經把這個檔的 <script> 寫好了，**不要再去動 index.html**
     —— 那個檔一動就會跟同時在畫別張圖的人撞在一起。*/
