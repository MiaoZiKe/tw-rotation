# 3D 優先清單（Andy 10-19：「把前面 AI 伺服器補上」「並且先接續完成有 3D 圖的文章」）

排程每輪**最先**做這份清單（排在 queued 請求與 rework_queue 之前），由上往下取「待做」：
- 新文章：主題取 site/articles/topics.json 的 id，照 fast_path／visual_playbook／topic_gen「類別定義與內容要求」寫，文章裡**必須**用 scene 區塊嵌入表列的站內 3D（必要時再加 2.5D），上架後留評分紀錄 docs/articles/scores/<id>.json，並把那個主題從主題候選清單標為已用（照現有 used_topics 慣例：note 或 topic 欄位寫主題 id）。
- 重做：同一個文章 id 重新上架覆蓋，並同步把 rework_queue.md 對應列改「已重做」。
做完一列就把狀態改成「已上架 <日期> <分數> <文章 id>」並 commit。一輪最多 4 篇／50 分鐘（含 rework）。

| 順序 | 類型 | 主題 id／文章 | 3D 場景 id（scene kind 3d） | 狀態 |
|---|---|---|---|---|
| 1 | 重做 | 2026-10-14-intro-ai-server AI 伺服器產業鏈入門 | ai_server（另嵌 2.5D ai_server） | 待做 |
| 2 | 新文章 | k_ssd SSD 是什麼？ | memory_module（SSD） | 待做 |
| 3 | 新文章 | k_foundry IC 代工是什麼？ | foundry | 待做 |
| 4 | 新文章 | k_abf IC 載板是什麼？ | ic_substrate | 待做 |
| 5 | 新文章 | k_psu_bbu AI 伺服器電源是什麼？ | server_psu（另嵌 2.5D power_bbu） | 待做 |
| 6 | 重做 | know-cowos CoWoS 是什麼？ | 站內 CoWoS-L 立體剖面（查 diagram_inventory） | 待做 |
| 7 | 重做 | know-hbm HBM 跟一般記憶體差在哪？ | hbm | 待做 |
| 8 | 重做 | know-cpo CPO 是什麼？ | switch（800G 交換器，查 diagram_inventory）＋2.5D silicon_photonics | 待做 |
| 9 | 新文章 | k_sic_gan 第三代半導體是什麼？ | wide_bandgap | 待做 |
| 10 | 新文章 | k_wafer 矽晶圓是什麼？ | silicon_wafer | 待做 |
| 11 | 新文章 | k_mlcc MLCC 是什麼？ | mlcc | 待做 |

場景 id 以 docs/articles/diagram_inventory.md 為準（上表若與盤點表不同，以盤點表為準）。
