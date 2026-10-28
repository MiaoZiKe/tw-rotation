# 公司實景照片審核清單（art-director，2026-10-28 第 1 版）

Andy 10-28 原話：新聞卡上方的大數字灰框改成「對應的實景圖片」（例如報導 SK 海力士／三星就放該公司總部或廠房照片），圖片上方放標題（主體＋事件小標），大數字仍在下方大標。圖片保持原色，不得套色調遮罩。

## 一、來源與入庫

- 只用 Wikimedia Commons 的 **CC0／CC BY／CC BY-SA／公有領域**照片；禁止新聞媒體照片、Google 圖片、公司官網照片、任何 LOGO 圖。
- 抓圖：`.github/workflows/company_photos.yml`（手動觸發＋每週一 03:17 台北）跑 `scripts/company_photos.py`，名單在 `social/photo_lib/targets.json`，中文主體名→slug 對照在 `social/photo_lib/aliases.json`（只做「完全相同名稱」比對，避免「南亞」吃到「南亞科」）。
- 每家存 `social/photo_lib/<slug>/photo.jpg`（原色、只縮放到寬 ≤1920）＋`meta.json`（license、author、source_url、file_title、reviewed:false）。
- 已審核（reviewed:true）的圖排程重抓時不會被覆蓋。

## 一之二、v2 圖池（Andy 10-28 原話：「為何有部分沒有圖片，若是沒有圖片可以改用相關產品圖片，並且圖片可以多樣，相關的也可以」）

- 每家改成圖池：`social/photo_lib/<slug>/photo_1..N.jpg`＋`pool.json`（`photos` 每張一筆 meta，含 `kind`：總部/廠房、產品、相關場景；`rejected` 記退件過的檔名，之後不再抓）。目標每家 3～5 張（總部/廠房 ≤2、產品 ≤2、相關場景 ≤1）。
- 查詢字在 `targets.json`：`queries`（總部／廠區）、`product_queries`（代表產品）、`related_queries`（相關產業通用圖）、`category`（所屬類別）。
- 類別通用圖池：`social/photo_lib/_category/<類別>/`（15 類，查詢字在 `categories.json`，每類 ≤8 張）。
- 產品圖、類別圖同樣不得以 LOGO／商標為主角；產品圖可以是同類產品（例如 HBM 記憶體），不必是該公司品牌，但不得是競爭對手 LOGO 特寫。
- 選圖順序（`render_news_cards.photo_pick`）：公司已審圖池（同公司近 14 天用過的往後排，輪替；紀錄在 `social/news/log/photo_usage.json`）→ 該公司類別圖池（主體不在名單、主題是總經 → 總經池）→ 灰框大數字。
- layout 標籤：`D-實景(公司)`／`D-實景(產品)`／`D-實景(類別)`／`D-無圖大數字`；meta 另寫 `photo_kind`。

## 二、審核流程

1. art-director 用 Read 看 `photo.jpg` 全解析度，並開 `source_url` 的授權資訊（meta.json 已存）。
2. 再看**套上 D-實景版型後的成品**（照片會被裁成 952 寬的橫幅，取中段）。
3. 逐項填下表，任一條退回＝整張退回。
4. 通過：把 meta.json 的 `reviewed` 改 `true`、`reviewer` 填 `art-director`、`review_note` 寫日期與結論；並在本檔第四節加一列。
5. 退回：刪掉該 slug 資料夾或在 `targets.json` 換更精準的查詢字，重跑工作流程（`refresh=true`）。
6. **reviewed=false 的照片，`scripts/social_news.py` 一律不用**，那篇自動退回灰框大數字版。

## 三、審核項目

| # | 項目 | 通過 | 退回 |
|---|---|---|---|
| 1 | 主體正確 | 總部/廠房：確實是該公司建築或船隊；產品：確實是該類產品；類別：確實是該產業場景 | 同名不同公司、別家公司建築、只是附近街景 |
| 2 | 授權 | CC0／CC BY／CC BY-SA／公有領域，作者欄可辨識；卡上標示「攝影：作者／授權・Wikimedia Commons」 | NC、ND、GFDL-only、授權不明、作者欄空白且無法補 |
| 3 | 無人臉、無個人 | 無可辨識人臉、車牌 | 主角是人物（執行長演講照等） |
| 4 | LOGO 佔比 | 建築上的招牌字只是場景的一部分、不是畫面主角 | 畫面主角是 LOGO 或招牌特寫 |
| 5 | 原色 | 未經套色、未加濾鏡遮罩（版型也不加） | 原圖本身是強烈濾鏡或黑白藝術照 |
| 6 | 裁切後 | 裁成 952×約 380～460 的橫幅後主體仍在畫面內、不被切掉 | 主體在畫面邊緣、裁完只剩天空或地面 |
| 7 | 清晰度 | 寬 ≥1200px，放大 100% 不糊 | 糊、色帶、壓縮方塊 |
| 8 | 時效與誤導 | 不暗示新聞事件本身（火災、抗議、施工事故） | 事故、示威、災害畫面 |
| 9 | 專業質感 | 構圖乾淨、日間、曝光正常 | 歪斜、嚴重逆光、雜物佔畫面 |

## 四、審核紀錄

第一輪（2026-10-28，art-director，依 952×424 中段裁切逐張檢視）：通過 25／退件 27。授權欄位 52 張皆齊（license、author、source_url）。退件的 reviewed 維持 false，meta.json 寫 reject_reason；`social_news.py` 對這些公司退回灰框版。

| slug | 授權 | 結論 | 日期 | 備註／退件原因 |
|---|---|---|---|---|
| amazon | CC BY-SA 4.0 | 通過 | 2026-10-28 | 西雅圖 Amazon Spheres，Amazon 總部園區，空拍構圖清楚 |
| amd | CC BY-SA 4.0 | 通過 | 2026-10-28 | AMD 森尼韋爾園區建築，招牌小 |
| apple | CC BY-SA 4.0 | 通過 | 2026-10-28 | Apple Park 空拍，主體完整 |
| ase | CC BY-SA 4.0 | 通過 | 2026-10-28 | 日月光高雄總部，招牌為場景一部分 |
| cdf | CC BY-SA 4.0 | 通過 | 2026-10-28 | 開發金控總部玻璃帷幕大樓，日間曝光正常（無招牌，靠檔名佐證） |
| chunghwa_telecom | CC BY-SA 4.0 | 通過 | 2026-10-28 | 中華電信總部大樓，構圖乾淨 |
| csc | CC BY-SA 4.0 | 通過 | 2026-10-28 | 中鋼高雄總部玻璃帷幕，裁切後建築主體完整 |
| ctbc | CC BY-SA 4.0 | 通過 | 2026-10-28 | 中信金融園區雙塔，日間 |
| delta | CC BY-SA 4.0 | 通過 | 2026-10-28 | 台達電泰國廠區，LOGO 為小招牌；注意是海外廠區非台灣總部 |
| esun | CC BY-SA 3.0 | 通過 | 2026-10-28 | 玉山金控大樓，日間 |
| evergreen | CC BY-SA 3.0 | 通過 | 2026-10-28 | 長榮海運大樓，字樣於頂端略被裁切但可接受 |
| formosa_plastics | CC BY-SA 3.0 | 通過 | 2026-10-28 | 台塑大樓，構圖乾淨 |
| hua_nan | CC BY-SA 4.0 | 通過 | 2026-10-28 | 華南銀行總行大樓，招牌小字 |
| intel | CC BY-SA 4.0 | 通過 | 2026-10-28 | Intel 聖塔克拉拉總部；立面有大型肖像壁畫，屬建築裝飾、非人物照，可接受 |
| liteon | CC0 | 通過 | 2026-10-28 | 光寶科技大樓，天色略灰但可接受 |
| mega | CC BY-SA 4.0 | 通過 | 2026-10-28 | 兆豐銀行大樓，招牌小字 |
| microsoft | CC BY-SA 4.0 | 通過 | 2026-10-28 | Microsoft 雷德蒙園區建築，底部 LOGO 僅露一角 |
| nxp | CC BY-SA 3.0 | 通過 | 2026-10-28 | NXP 總部大樓，水岸構圖佳 |
| openai | CC BY-SA 4.0 | 通過 | 2026-10-28 | OpenAI 舊總部 Pioneer Building，無 LOGO；內容為建築外觀，若 OpenAI 搬遷需重審 |
| qualcomm | CC BY-SA 3.0 | 通過 | 2026-10-28 | Qualcomm 聖地牙哥總部，招牌為建築一部分 |
| samsung | CC BY-SA 2.0 | 通過 | 2026-10-28 | 三星首爾瑞草大樓，周邊他牌招牌小；可接受 |
| tesla | CC BY 4.0 | 通過 | 2026-10-28 | Giga Texas 廠房外牆，畫面單調但主體正確 |
| tsmc | CC BY 4.0 | 通過 | 2026-10-28 | 台積電 Fab 18，構圖與曝光佳 |
| wistron | CC BY-SA 4.0 | 通過 | 2026-10-28 | 緯創竹北總部大樓，日間 |
| yangming | CC BY-SA 4.0 | 通過 | 2026-10-28 | 陽明海運總部大樓，無招牌，裁切後主體完整 |
| anthropic | CC0 | 退件 | 2026-10-28 | 主角是人物演講與簡報螢幕，非公司建築（且為講座場地） |
| asml | Public domain | 退件 | 2026-10-28 | 天空過曝、塔樓頂端被裁、影像偏灰；畫質不合格 |
| asus | CC BY-SA 2.0 | 退件 | 2026-10-28 | 霧霾、施工鷹架，辨識不出華碩大樓 |
| broadcom | CC BY-SA 4.0 | 退件 | 2026-10-28 | 樹木遮住主體，建築幾乎看不到 |
| cathay | CC BY-SA 4.0 | 退件 | 2026-10-28 | ATM 與門面特寫，非總部主體 |
| fareastone | CC BY-SA 4.0 | 退件 | 2026-10-28 | 畫面主角是三星手機廣告看板，且是街邊門市 |
| first_fin | CC BY-SA 3.0 | 退件 | 2026-10-28 | 畫面主角是銀行招牌橫條，建築被機車與廣告搶戲 |
| foxconn | CC BY 2.0 | 退件 | 2026-10-28 | 畫面主角是 FOXCONN 招牌特寫（LOGO 為主角） |
| fpcc | CC BY-SA 4.0 | 退件 | 2026-10-28 | 主角是加油站與招牌，雨天灰暗，非廠房 |
| fubon | CC BY 2.0 | 退件 | 2026-10-28 | 原圖為強烈濾鏡／後製（紫色、紅外線風），違反原色 |
| hotai | CC BY-SA 4.0 | 退件 | 2026-10-28 | LOGO 金屬字特寫，LOGO 為主角 |
| inventec | CC BY-SA 4.0 | 退件 | 2026-10-28 | 畫面主角是施工中的台北表演藝術中心鋼構，非英業達大樓（同圖他物） |
| meta | CC0 | 退件 | 2026-10-28 | 建築在畫面左緣很小、主體是路口與天空，裁切後主體不成立 |
| micron | CC BY-SA 3.0 | 退件 | 2026-10-28 | 實為 Boise State 大學工程中心，非美光（同名誤抓） |
| nanya_plastics | CC BY-SA 4.0 | 退件 | 2026-10-28 | 霧天灰暗、主體是大門與路面，質感不足 |
| nvidia | CC BY 2.0 | 退件 | 2026-10-28 | 畫面主角是 NVIDIA 路牌 LOGO 特寫 |
| pegatron | CC0 | 退件 | 2026-10-28 | 主機板微距照，非和碩建築（同名誤抓） |
| quanta | CC BY-SA 4.0 | 退件 | 2026-10-28 | 天花鋼構特寫，看不出主體是廣達 |
| sinopac | CC BY-SA 4.0 | 退件 | 2026-10-28 | 大樓樓層指示牌特寫，且內容為兆豐證券，主體錯誤 |
| taishin | CC BY-SA 3.0 | 退件 | 2026-10-28 | 入口招牌近拍，無建築全貌，招牌為主角 |
| taiwan_mobile | CC BY-SA 3.0 | 退件 | 2026-10-28 | 實為 Panasonic 台灣總部，非台灣大哥大（同名誤抓） |
| tcc | CC BY-SA 3.0 | 退件 | 2026-10-28 | 畫面主角是兩面紅色 LOGO 布幔，夜間逆光 |
| tcfhc | CC BY-SA 3.0 | 退件 | 2026-10-28 | 合作金庫工會鐵捲門，非總部，無主體 |
| uni_president | CC BY-SA 4.0 | 退件 | 2026-10-28 | 統一蛋糕屋攤位活動照，主角是人物與攤位 |
| unimicron | CC BY-SA 4.0 | 退件 | 2026-10-28 | 樹木與雜物佔畫面、廠房被遮，構圖雜亂 |
| wanhai | CC BY-SA 2.0 | 退件 | 2026-10-28 | 動態模糊、樹叢遮擋，畫質不合格 |
| yuanta | CC BY-SA 4.0 | 退件 | 2026-10-28 | 樹木與路牌遮擋大樓，構圖雜亂 |
