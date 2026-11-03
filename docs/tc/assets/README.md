# 科技透明圈（頻道二）貼文圖庫

整理於 2026-11-03。Andy 11-03 原話：「需要你找對應公司的圖片，以及產品圖 像是 我網頁內做的 3D架構圖等等」。
圖庫分三塊：**公司 LOGO（指稱用途）**、**架構圖（取自本站自己畫的剖析圖）**、**套版範例（瑞士極簡版型）**。
全部來源都在 repo 或本站內，沒有 AI 生成、沒有轉貼他人照片、沒有比比。

## 使用規則（法遵 7-3，六條全成立才可上貼文圖）

### 公司 LOGO
1. 緊貼公司名稱作標示，**不當主視覺**、不放封面大圖、不當大頭貼。
2. 原色原比例（本庫只做白底置中、等比例縮放、裁掉空白邊，不改色、不變形），**不與開口圈 LOGO 組合**。範例 A 的頁首因此用純文字「科技透明圈」，不放開口圈圖示。
3. 高度不超過公司名字高的 1.5 倍；多家並列時一樣大（範例 A1：LOGO 高 80px、公司名 120px，約 0.67 倍）。
4. **負面內容（工時長、抱怨、繁忙）只寫公司名、不放 LOGO**（範例 A2 就是這樣）。
5. 文末固定一句「與各公司無合作或授權關係」（範例 A 三張的頁底都有）。
6. 收到檢舉就換純文字版（範例 A1 同時附 `A1_cover_textonly.png` 當備案）。

⚠ 有疑慮的交給 legal-compliance 判斷；這個容器沒有派工工具，**尚未實際派 legal-compliance 複審**，見 review.md。

### 架構圖
- 一律標「示意圖，非實物比例」（每張底部已印）。
- **不畫公司 LOGO、不標客戶對應**：截圖時程式把卡片裡的台股膠囊、股票代號、含公司名的說明文字整個拿掉（程式掃描結果：可見文字 0 個公司名、0 個四位數代號）。圖內「CoWoS」是技術名稱，不是客戶對應。
- 取自 `site/diagrams.js`／`site/dg/*.js`／`site/themes3d.js` 的現有圖，淺色主題、2 倍解析度，已去掉網站導覽列與客服／吉祥物浮層。

## 一、公司 LOGO（`logos/`，512×512 白底）

來源只用 repo 內既有圖：`data/logos/<代號>.png`（多為 64px）與 `data/logos/tc/<網域>.png`（128px），沒有向外抓（這個容器對外網路被擋）。
對應規則見 DECISIONS #364、#365；公司→網域對照取自 `site/tc/logos.js`。
**狀態說明**：可用＝原圖內容寬 ≥96px；低解析＝32～95px（放大最多 4 倍，邊緣偏軟，**只適合小尺寸並列在公司名旁，不可放大當主視覺**）；缺圖＝repo 內沒有可用圖。

共 33 家（前 20 家＋薪資文用到的 13 家），29 張可出圖（16 張可用、13 張低解析），4 家缺圖：矽品（SPIL，已併入日月光、repo 無獨立圖）、緯創（3231，`data/logos` 無檔）、欣興（3037，`data/logos` 無檔）、緯穎（6669，原圖只殘留 14px 小圖示，不收）。
補圖做法：這個容器連不到官網與 Wikimedia；請有外網的環境跑 `pipeline/sources/tc_logos.py` 的代號補強（`pipeline/groups/tc_code_domains.json`）補這四家與低解析 13 家，補到後重跑 `scripts/build_logos.py`。

| 公司 | 檔名 | 狀態 | 原圖內容寬（px） | 來源（repo 內） |
|---|---|---|---|---|
| 台積電 | 台積電.png | 低解析 | 64 | data/logos/2330.png |
| 日月光 | 日月光.png | 低解析 | 64 | data/logos/3711.png |
| 聯發科 | 聯發科.png | 低解析 | 64 | data/logos/2454.png |
| 美光台灣 | 美光台灣.png | 可用 | 120 | data/logos/tc/micron.com.png |
| 台達電 | 台達電.png | 可用 | 128 | data/logos/tc/deltaww.com.png |
| 廣達 | 廣達.png | 低解析 | 64 | data/logos/2382.png |
| 聯電 | 聯電.png | 可用 | 123 | data/logos/tc/umc.com.png |
| 聯詠 | 聯詠.png | 低解析 | 51 | data/logos/3034.png |
| 華碩 | 華碩.png | 低解析 | 64 | data/logos/2357.png |
| 世界先進 | 世界先進.png | 可用 | 117 | data/logos/tc/vis.com.tw.png |
| 鴻海 | 鴻海.png | 可用 | 128 | data/logos/tc/foxconn.com.png |
| 南亞科 | 南亞科.png | 低解析 | 55 | data/logos/2408.png |
| 力積電 | 力積電.png | 可用 | 128 | data/logos/tc/powerchip.com.png |
| 瑞昱 | 瑞昱.png | 低解析 | 60 | data/logos/2379.png |
| 群聯 | 群聯.png | 低解析 | 63 | data/logos/8299.png |
| 矽品 | — | 缺圖 | — | 無 |
| 緯穎 | — | 缺圖（原圖僅殘留小圖示） | 14 | data/logos/6669.png |
| 緯創 | — | 缺圖 | — | 無 |
| Lam Research | Lam_Research.png | 可用 | 127 | data/logos/tc/lamresearch.com.png |
| 華邦電 | 華邦電.png | 低解析 | 64 | data/logos/2344.png |
| 應用材料（薪資文） | 應用材料.png | 可用 | 122 | data/logos/tc/appliedmaterials.com.png |
| ASML（薪資文） | ASML.png | 可用 | 128 | data/logos/tc/asml.com.png |
| 英業達（薪資文） | 英業達.png | 可用 | 114 | data/logos/tc/inventec.com.png |
| 和碩（薪資文） | 和碩.png | 可用 | 109 | data/logos/tc/pegatroncorp.com.png |
| 光寶（薪資文） | 光寶.png | 可用 | 128 | data/logos/tc/liteon.com.png |
| 瑞鼎（薪資文） | 瑞鼎.png | 可用 | 128 | data/logos/tc/rad-ic.com.png |
| 欣興（薪資文） | — | 缺圖 | — | 無 |
| KLA（薪資文） | KLA.png | 可用 | 128 | data/logos/tc/kla.com.png |
| NVIDIA（薪資文） | NVIDIA.png | 可用 | 127 | data/logos/tc/nvidia.com.png |
| 京元電子（薪資文） | 京元電子.png | 低解析 | 56 | data/logos/2449.png |
| 仁寶（薪資文） | 仁寶.png | 低解析 | 63 | data/logos/2324.png |
| 慧榮（薪資文） | 慧榮.png | 可用 | 127 | data/logos/tc/siliconmotion.com.png |
| 智易（薪資文） | 智易.png | 低解析 | 64 | data/logos/3596.png |

適合貼文類別：A「公司行情」封面（LOGO 小尺寸緊貼公司名）、公司介紹文、公司名單並列圖。不適合：薪資負面欄位頁、大頭貼、封面大圖。授權／使用條件：商標屬各公司所有，僅作指稱用途（標示是哪一家公司），不暗示合作或背書。

## 二、架構圖（`diagrams/`，1080×1350）

`*_2d.png` 是 2D 剖析圖，`*_3d.png` 是 3D 視角（headless 瀏覽器截一個固定視角，3D 外側文字框保留引線）。`diagrams/raw/` 是未加白邊與底部說明的原始截圖，給套版用。
來源：本站 `#industry/<產業鏈>/dg/<圖別>` 的剖析圖；授權：自家作品，無第三方素材。為了符合「不標客戶對應」，卡片已逐張拿掉（卡片放不進 1350 高度就拿掉），圖上對應編號圈一起隱藏；被含公司名的段落（晶圓代工、HBM、矽晶圓的導言）已隱藏。

| 檔名 | 內容 | 適合貼文 |
|---|---|---|
| ai_adv_packaging_2d | CoWoS 先進封裝剖面：晶粒、微凸塊、中介層、載板 | 技術白話：先進封裝是什麼 |
| foundry_2d | 平面／FinFET／GAA 三代電晶體與製程迴圈 | 技術白話：晶圓代工、電晶體演進 |
| hbm_2d、hbm_3d | HBM 堆疊 DRAM、TSV、底下邏輯晶粒與 GPU 的相對位置 | 技術白話：HBM；面試題（TSV） |
| silicon_wafer_2d | CZ 提拉法長晶、晶圓為何越大越划算 | 技術白話：矽晶圓；面試題（良率／面積） |
| ai_server_2d | AI 機櫃、運算托盤、整櫃出貨 | 技術白話：AI 伺服器長什麼樣 |
| pcb_rigid_2d | 多層 PCB 剖面、貫孔與走線 | 技術白話：PCB／載板疊構 |
| ic_substrate_2d、ic_substrate_3d | ABF 載板增層剖面、BGA 球 | 技術白話：載板是什麼 |
| air_cooling_2d、air_cooling_3d | 風扇、鰭片、熱管、風壓風量曲線 | 技術白話：散熱 |
| liquid_cooling_2d | 冷板、均熱板 VC、熱管、CDU 迴路 | 技術白話：液冷 |
| server_psu_2d | 機房到晶片的電力路徑、PSU、板上降壓 | 技術白話：伺服器電源 |
| ai_interconnect_2d | 連接器、高速訊號走線與金手指 | 技術白話：連接器 |
| switch_wireless_2d | 交換器板卡、光模組、CPO | 技術白話：網通 |
| mlcc_2d | MLCC 疊層剖面 | 技術白話：被動元件 |

共 16 張（13 張 2D、3 張 3D）。限制：①圖內說明文字原本是 12px 級，縮進 1080 寬約 17px，手機上偏小，建議貼文用「單一重點裁切」或搭配大字標題；②3D 只截一個固定視角，不是可轉動的；③液冷、氣冷、CPO 等圖的細部結構正確性仍待 mechanical-engineer 複審（見 review.md）。

## 三、套版範例（`samples/`，瑞士極簡版型，1080×1350）

版型：頻道二第 3 套瑞士極簡（白底、黑 #111111、瑞士紅 #D4231A、輔助灰 #595959、細線 #CFCFCF、淡灰面 #EFEFEF），字型 Noto Sans TC。內容全是〔待填〕或教學用假設值，每張標「示意・範例」。

| 檔名 | 內容 | 說明 |
|---|---|---|
| A1_cover_logo | 公司行情封面，台積電名稱大字＋LOGO 小尺寸緊貼 | 符合法遵六條 |
| A1_cover_textonly | 同上，純文字版 | 收到檢舉時換這張 |
| A2_fields_textonly | 七欄位表（含加班等欄位），只有公司名 | 負面欄位不放 LOGO |
| A3_cta | 結尾互動頁，頁底有「與各公司無合作或授權關係」 | |
| B1_cover | 技術白話封面：CoWoS 是什麼 | 頁首帶開口圈 LOGO |
| B2_diagram | 帶 CoWoS 剖面示意圖 | 底部標示意圖 |
| B3_points | 三個重點 | |
| C1_question | 面試題：面積放大 2 倍良率會剛好剩一半嗎 | |
| C2_diagram | 示意晶圓：同樣 8 顆缺陷，小晶粒 vs 大晶粒（程式算出良品數） | 示意圖，缺陷位置隨機 |
| C3_answer | 答案：Y＝e^(−A·D₀)，面積加倍良率變平方（0.905²≈0.819） | 教學假設值，非任何公司數字 |

重疊檢查：程式 10 張 0 筆（`samples/overlap_report.json`；量測每個文字區塊與圖片的外框、兩兩比對，並檢查出界、溢出與小於 24px 的字）。人工逐張目視另見 review.md。

## 重新產生

腳本在 `scripts/`（路徑寫死在這個容器，換環境要改開頭的常數）：`build_logos.py`（LOGO）、`mini_data.py`＋`shoot2.py`＋`compose_dg.py`（2D 架構圖；完整 `build_payload` 在 16GB 容器會被 OOM 殺掉，所以只產開頁需要的 4 個小 JSON）、`compose3d.py`、`render_samples.py`（套版＋重疊檢查）。Noto Sans TC 字型（68MB）不進 repo，`npm pack @fontsource/noto-sans-tc` 解開後用 `TW_FONT_DIR` 指到那個資料夾。
