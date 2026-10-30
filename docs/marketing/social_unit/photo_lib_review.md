# 公司實景照片審核清單（art-director，2026-10-28 第 1 版）

Andy 10-28 原話：新聞卡上方的大數字灰框改成「對應的實景圖片」（例如報導 SK 海力士／三星就放該公司總部或廠房照片），圖片上方放標題（主體＋事件小標），大數字仍在下方大標。圖片保持原色，不得套色調遮罩。

## 一、來源與入庫

- 只用 Wikimedia Commons 的 **CC0／CC BY／CC BY-SA／公有領域**照片；禁止新聞媒體照片、Google 圖片、公司官網照片、任何 LOGO 圖。（官方新聞圖例外條件見第九節：須書面授權）
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

### 第二輪（2026-10-28，v2 圖池，art-director 依 952×424 中段裁切逐張檢視）

新抓 376 張：通過 190、退件 186。每張結論寫在各自 `pool.json`（通過：`reviewed:true`＋`review_note`；退件：移到 `rejected`，附原因，之後不再抓）。
主要退件原因：LOGO／招牌為主角、別家銀行分行（合作金庫／臺灣銀行／土地銀行被誤抓到他家金控）、人物為主角、同名誤抓（Quanta Crews、King's College 等）、與產品無關的零件特寫、事故或廢墟畫面、強烈色調。
審後覆蓋：67 家中 57 家有 ≥1 張（平均 2.2 張／家），類別池 15 類共 68 張；公司池仍無圖的 10 家（聯發科、智邦、聯電、和碩、合庫金、大立光、永豐金、聯詠、台灣大哥大、健策）改用類別池。偏少的類別池：網通 1、汽車 2、金融 2、電信 2，下次換查詢字補。

## 第五節　第三輪複審（2026-10-28，art-director 正式審核，複審所有工程自審 reviewed:true 的 215 張）

標準同第三節，逐張用 952×424 中段裁切檢視；額外加嚴三條：① 拍到的是「同名他物／他牌產品」一律退（例如 Motorola／TI／Mitsubishi 記憶體板冒充三星、SK 海力士、美光；Netgear 交換器冒充台達電）；② 畫面主體是台北 101 天際線的，不算金控本身，退；③ 圖上有浮水印、可辨識車牌、人物入鏡、施工／廢墟／濃霧色偏的退。

結果：通過 98／退件 117。通過者 pool.json 加 `reviewed_by: art-director`；退件者 `reviewed:false` 並寫 `reject_reason`（`social_news.py` 對 reviewed:false 一律不用）。

| 圖池 | 通過 | 退件 |
|---|---|---|
| _category/AI伺服器 | 4 | 2 |
| _category/PCB | 4 | 2 |
| _category/半導體 | 5 | 1 |
| _category/散熱 | 4 | 1 |
| _category/汽車 | 1 | 1 |
| _category/消費電子 | 3 | 1 |
| _category/石化 | 1 | 3 |
| _category/網通 | 0 | 1 |
| _category/總經 | 3 | 3 |
| _category/航運 | 7 | 1 |
| _category/記憶體 | 4 | 2 |
| _category/資料中心 | 1 | 5 |
| _category/金融 | 1 | 1 |
| _category/鋼鐵 | 2 | 2 |
| _category/電信 | 1 | 1 |
| advantech | 0 | 2 |
| alchip | 1 | 1 |
| alphabet | 1 | 1 |
| amazon | 2 | 2 |
| amd | 3 | 0 |
| anthropic | 0 | 3 |
| apple | 3 | 0 |
| ase | 1 | 1 |
| asml | 0 | 1 |
| asus | 2 | 1 |
| auras | 2 | 0 |
| broadcom | 1 | 1 |
| cathay | 0 | 1 |
| cdf | 1 | 1 |
| chunghwa_telecom | 2 | 2 |
| csc | 2 | 2 |
| ctbc | 2 | 1 |
| delta | 2 | 3 |
| esun | 1 | 1 |
| evergreen | 1 | 2 |
| fareastone | 0 | 5 |
| first_fin | 0 | 1 |
| formosa_plastics | 1 | 2 |
| foxconn | 0 | 1 |
| fpcc | 0 | 3 |
| fubon | 0 | 2 |
| hotai | 0 | 2 |
| hua_nan | 1 | 0 |
| intel | 2 | 1 |
| inventec | 0 | 1 |
| kingslide | 0 | 2 |
| liteon | 1 | 2 |
| mega | 1 | 2 |
| meta | 0 | 1 |
| micron | 1 | 2 |
| microsoft | 2 | 3 |
| nanya_plastics | 0 | 2 |
| nvidia | 2 | 1 |
| nxp | 2 | 0 |
| openai | 1 | 4 |
| qualcomm | 1 | 1 |
| quanta | 0 | 1 |
| realtek | 1 | 0 |
| samsung | 1 | 2 |
| sk_hynix | 0 | 1 |
| taishin | 0 | 2 |
| tcc | 1 | 2 |
| tesla | 1 | 4 |
| tsmc | 3 | 1 |
| uni_president | 1 | 0 |
| unimicron | 1 | 1 |
| wanhai | 2 | 2 |
| wistron | 2 | 2 |
| wiwynn | 0 | 2 |
| yageo | 1 | 0 |
| yangming | 1 | 3 |
| yuanta | 0 | 3 |

提醒：以下公司複審後**沒有任何通過的圖**，自動發文遇到這幾家會退回灰框大數字版，不會用錯圖：

_category/網通、advantech、anthropic、asml、cathay、fareastone、first_fin、foxconn、fpcc、fubon、hotai、inventec、kingslide、meta、nanya_plastics、quanta、sk_hynix、taishin、wiwynn、yuanta

## 第六節　第四輪（2026-10-28，art-director 正式審核 v3 初篩通過的 203 張）

標準同第五節（含加嚴三條）。額外退件原則：他牌／同名他物（如 BP／Altona 煉油廠冒充 Aramco／台塑化、Freescale 開發板冒充研華、Raspberry Pi 冒充 Arm）、缺貨空架與舊版鈔票／硬幣（過時或暗示事件）、強烈調色（霓虹、黃光、藍光）、黑白老照片、機房雜亂、施工中、LOGO 特寫為主角。初篩點名的豐田上鄉工廠外道路、匯率子類舊日圓紙鈔均退。

結果：通過 121／退件 82。通過者 `reviewed:true`＋`reviewed_by: art-director`；退件者 `reviewed:false` 並寫 `reject_reason`。

| 圖池 | 通過 | 退件 |
|---|---|---|
| social/photo_lib/_category/總經 | 3 | 2 |
| social/photo_lib/_category/總經_利率債券 | 4 | 0 |
| social/photo_lib/_category/總經_匯率 | 2 | 1 |
| social/photo_lib/_category/總經_央行 | 5 | 0 |
| social/photo_lib/_category/總經_房市 | 4 | 0 |
| social/photo_lib/_category/總經_景氣 | 5 | 1 |
| social/photo_lib/_category/總經_物價就業 | 1 | 2 |
| social/photo_lib/_category/總經_能源 | 1 | 3 |
| social/photo_lib/_category/總經_貿易關稅 | 3 | 0 |
| social/photo_lib/_category/AI伺服器 | 2 | 1 |
| social/photo_lib/_category/PCB | 0 | 2 |
| social/photo_lib/_category/半導體 | 3 | 0 |
| social/photo_lib/_category/娛樂媒體 | 0 | 1 |
| social/photo_lib/_category/散熱 | 2 | 0 |
| social/photo_lib/_category/汽車 | 1 | 1 |
| social/photo_lib/_category/石化 | 4 | 0 |
| social/photo_lib/_category/網通 | 1 | 0 |
| social/photo_lib/_category/能源 | 7 | 0 |
| social/photo_lib/_category/航太 | 2 | 0 |
| social/photo_lib/_category/航運 | 1 | 0 |
| social/photo_lib/_category/資料中心 | 1 | 3 |
| social/photo_lib/_category/金融 | 4 | 0 |
| social/photo_lib/_category/鋼鐵 | 0 | 1 |
| social/photo_lib/_category/零售消費 | 1 | 4 |
| social/photo_lib/_category/電信 | 1 | 0 |
| social/photo_lib/accton | 1 | 0 |
| social/photo_lib/advantech | 0 | 2 |
| social/photo_lib/alibaba | 2 | 1 |
| social/photo_lib/alphabet | 2 | 0 |
| social/photo_lib/amazon | 2 | 0 |
| social/photo_lib/anthropic | 0 | 1 |
| social/photo_lib/apple | 1 | 0 |
| social/photo_lib/aramco | 1 | 2 |
| social/photo_lib/arm | 1 | 2 |
| social/photo_lib/ase | 1 | 0 |
| social/photo_lib/berkshire | 0 | 1 |
| social/photo_lib/boeing | 1 | 2 |
| social/photo_lib/byd | 2 | 0 |
| social/photo_lib/cathay | 1 | 0 |
| social/photo_lib/cdf | 1 | 0 |
| social/photo_lib/chunghwa_telecom | 0 | 1 |
| social/photo_lib/cisco | 2 | 1 |
| social/photo_lib/cocacola | 0 | 1 |
| social/photo_lib/csc | 3 | 0 |
| social/photo_lib/dell | 1 | 2 |
| social/photo_lib/delta | 1 | 0 |
| social/photo_lib/esun | 1 | 0 |
| social/photo_lib/evergreen | 1 | 2 |
| social/photo_lib/exxon | 0 | 2 |
| social/photo_lib/fareastone | 0 | 2 |
| social/photo_lib/first_fin | 1 | 1 |
| social/photo_lib/formosa_plastics | 1 | 1 |
| social/photo_lib/fpcc | 0 | 2 |
| social/photo_lib/fubon | 1 | 1 |
| social/photo_lib/goldman | 2 | 0 |
| social/photo_lib/hotai | 0 | 1 |
| social/photo_lib/hpe | 2 | 2 |
| social/photo_lib/huawei | 0 | 1 |
| social/photo_lib/intel | 2 | 0 |
| social/photo_lib/inventec | 0 | 1 |
| social/photo_lib/jpmorgan | 1 | 1 |
| social/photo_lib/kioxia | 1 | 0 |
| social/photo_lib/kla | 1 | 1 |
| social/photo_lib/liteon | 0 | 3 |
| social/photo_lib/marvell | 1 | 0 |
| social/photo_lib/meta | 2 | 0 |
| social/photo_lib/micron | 2 | 0 |
| social/photo_lib/microsoft | 1 | 2 |
| social/photo_lib/nanya_plastics | 0 | 2 |
| social/photo_lib/netflix | 1 | 1 |
| social/photo_lib/nike | 1 | 0 |
| social/photo_lib/nintendo | 1 | 2 |
| social/photo_lib/nxp | 0 | 1 |
| social/photo_lib/openai | 0 | 1 |
| social/photo_lib/oracle | 2 | 0 |
| social/photo_lib/pegatron | 0 | 1 |
| social/photo_lib/qualcomm | 1 | 0 |
| social/photo_lib/samsung | 0 | 1 |
| social/photo_lib/sony | 3 | 1 |
| social/photo_lib/supermicro | 1 | 1 |
| social/photo_lib/taiwan_mobile | 0 | 1 |
| social/photo_lib/tcc | 0 | 1 |
| social/photo_lib/tel | 1 | 1 |
| social/photo_lib/ti | 1 | 1 |
| social/photo_lib/toyota | 2 | 1 |
| social/photo_lib/unimicron | 1 | 1 |
| social/photo_lib/walmart | 0 | 2 |
| social/photo_lib/wanhai | 2 | 1 |
| social/photo_lib/wdc | 2 | 0 |
| social/photo_lib/yangming | 1 | 1 |


## 第七節　第五輪：公司照片優先（2026-10-30）

> Andy 10-30（看著緊急加發「Alphabet 跌 12.6%」封面配了 Intel 處理器照片）：「相這種跟公司有關的 優先附上公司圖片」。
> 抓圖：`company_photos.yml` run 40987929655（2026-10-30 09:47 台北，32 家，`category=none`），新增 Commons 公司分類抓法（`targets.json` 的 `commons_categories`）。commit a1b0fb52。
> 審核：照第三節 9 項逐張看（952×424 中段裁切聯絡表＋關鍵幾張全解析度），執行者 social-ops-lead（照 art-director 清單）。共 103 張：通過 27／退件 76。授權全部是 CC0／CC BY／CC BY-SA／公有領域，作者與原始網址已存在 pool.json。
> 退件主因：人物為主角（官方參訪照）、施工中、同名不同公司（上海／汐止「日月光」住宅區）、他牌產品、LOGO 為主角。

| slug／檔名 | 授權 | 結論 | 說明 |
|---|---|---|---|
| alphabet/photo_5.jpg | CC BY-SA 4.0 | 通過 | Google 山景城園區的公司自行車（Google 配色），辨識度高、原色、無人臉 |
| alphabet/photo_6.jpg | CC BY-SA 4.0 | 退件 | Google LOGO 特寫為畫面主角（審核項 4） |
| alphabet/photo_7.jpg | CC BY-SA 4.0 | 退件 | 地面自行車標線，辨識不足 |
| alphabet/photo_8.jpg | CC BY-SA 4.0 | 通過 | Google 園區公司自行車，日間、構圖乾淨 |
| microsoft/photo_9.jpg | CC BY 2.0 | 通過 | Microsoft 雷德蒙園區 Building 42，日間、雪景，無人臉 |
| microsoft/photo_10.jpg | CC BY 2.0 | 退件 | 雜亂工作台，與 Microsoft 無直接關聯（審核項 9） |
| microsoft/photo_11.jpg | CC0 | 退件 | 線材特寫，無法辨識公司 |
| microsoft/photo_12.jpg | Public domain | 通過 | Microsoft 園區 Building 17 正門，日間、構圖乾淨 |
| microsoft/photo_13.jpg | Public domain | 退件 | 地圖（非實景照片） |
| apple/photo_6.jpg | CC BY-SA 4.0 | 通過 | Apple Park 環形主建築（樹後），黃昏原色、主體可辨 |
| apple/photo_7.jpg | CC BY-SA 4.0 | 退件 | Apple Park 模型、室內偏暗 |
| apple/photo_8.jpg | CC BY 2.0 | 退件 | 人物為主角（審核項 3） |
| apple/photo_9.jpg | CC BY-SA 4.0 | 通過 | Apple Park 建築入口，日間、構圖乾淨 |
| amazon/photo_8.jpg | CC BY-SA 4.0 | 通過 | Amazon Spheres 空拍，西雅圖總部園區 |
| amazon/photo_9.jpg | CC BY-SA 4.0 | 通過 | Amazon Spheres 外觀，日間 |
| amazon/photo_10.jpg | CC BY-SA 2.0 | 退件 | Spheres 室內噴霧特寫，辨識不足 |
| amazon/photo_11.jpg | CC BY-SA 4.0 | 通過 | Amazon Spheres 外觀，日間（檔名為西雅圖街景，畫面主體即 Spheres） |
| nvidia/photo_6.jpg | CC BY 2.0 | 退件 | 展場人群可辨識人臉（審核項 3） |
| nvidia/photo_7.jpg | CC BY 2.0 | 退件 | 人物為主角（審核項 3） |
| nvidia/photo_8.jpg | CC BY 2.0 | 退件 | 特斯拉汽車，非 NVIDIA（主體錯誤） |
| nvidia/photo_9.jpg | CC BY-SA 4.0 | 通過 | NVIDIA GPU 晶片特寫（代表產品），清晰，字樣為產品本身印字 |
| nvidia/photo_10.jpg | CC0 | 退件 | 他家展示機台，非 NVIDIA（主體錯誤） |
| intel/photo_6.jpg | CC BY-SA 4.0 | 通過 | Intel 聖塔克拉拉總部，日間、藍天 |
| amd/photo_6.jpg | CC BY-SA 3.0 | 通過 | AMD 森尼韋爾總部，日間 |
| amd/photo_7.jpg | CC BY-SA 3.0 de | 退件 | 港口筒倉，非 AMD（主體錯誤） |
| amd/photo_8.jpg | CC BY-SA 4.0 | 退件 | 2004 年施工中工地（審核項 8） |
| amd/photo_9.jpg | CC BY-SA 3.0 de | 退件 | 港口筒倉，非 AMD（主體錯誤） |
| broadcom/photo_4.jpg | CC BY-SA 4.0 | 通過 | Broadcom 晶片特寫（代表產品），清晰 |
| micron/photo_7.jpg | Public domain | 退件 | 人物為主角（審核項 3） |
| micron/photo_8.jpg | CC BY 2.0 | 退件 | 人物為主角（審核項 3） |
| micron/photo_9.jpg | Public domain | 退件 | 人物為主角（審核項 3） |
| micron/photo_10.jpg | CC BY-SA 4.0 | 通過 | Micron（Crucial）DDR4 伺服器記憶體模組（代表產品），背景乾淨 |
| tesla/photo_10.jpg | CC BY 4.0 | 退件 | 施工中鋼構（審核項 8） |
| tesla/photo_11.jpg | CC BY 4.0 | 退件 | 施工現場（審核項 8） |
| tesla/photo_12.jpg | CC BY 4.0 | 退件 | 施工中鋼構（審核項 8） |
| oracle/photo_4.jpg | CC BY-SA 4.0 | 退件 | 印度科技園區夜景，看不出 Oracle |
| oracle/photo_5.jpg | CC0 | 通過 | Oracle 聖荷西大樓仰角，招牌為建築一部分 |
| oracle/photo_6.jpg | CC BY-SA 3.0 | 退件 | 灰暗、看不出 Oracle |
| oracle/photo_7.jpg | CC BY-SA 4.0 | 通過 | Oracle 科羅拉多泉辦公大樓，日間、招牌小 |
| oracle/photo_8.jpg | CC BY 2.0 | 退件 | 人物為主角（審核項 3） |
| coreweave/photo_1.jpg | CC0 | 退件 | 債券殖利率圖表（非實景照片） |
| coreweave/photo_2.jpg | CC BY 4.0 | 退件 | Microsoft 資料中心，非 CoreWeave（主體錯誤） |
| openai/photo_9.jpg | Public domain | 退件 | 賽車塗裝，與 OpenAI 公司實景無關、易誤導 |
| openai/photo_10.jpg | Public domain | 退件 | 賽車塗裝，易誤導 |
| openai/photo_11.jpg | Public domain | 退件 | 賽車塗裝，易誤導 |
| anthropic/photo_6.jpg | CC BY 2.0 | 退件 | 人物為主角（審核項 3） |
| anthropic/photo_7.jpg | CC BY 2.0 | 退件 | 人物為主角（審核項 3） |
| anthropic/photo_8.jpg | CC BY-SA 2.0 | 退件 | 舊金山夜景，非 Anthropic 公司主體 |
| samsung/photo_8.jpg | CC BY 2.0 | 退件 | 首爾街景，看不出三星 |
| samsung/photo_9.jpg | CC BY-SA 3.0 | 退件 | 首爾街景，看不出三星 |
| samsung/photo_10.jpg | CC BY-SA 2.0 | 退件 | 漢江人工島，非三星 |
| samsung/photo_11.jpg | CC BY-SA 4.0 | 退件 | 首爾街景，看不出三星 |
| sk_hynix/photo_5.jpg | CC0 | 退件 | 多家公司 LOGO 拼貼（審核項 4） |
| sk_hynix/photo_6.jpg | CC BY-SA 4.0 | 通過 | SK hynix DDR5 記憶體模組（代表產品），標籤清楚 |
| sk_hynix/photo_7.jpg | CC BY-SA 4.0 | 通過 | SK hynix DDR5 SO-DIMM（代表產品） |
| tsmc/photo_6.jpg | CC BY 2.0 | 退件 | 人物為主角（審核項 3） |
| tsmc/photo_7.jpg | CC BY 2.0 | 退件 | 人物為主角（審核項 3） |
| tsmc/photo_8.jpg | CC BY-SA 4.0 | 退件 | 徵才活動人群（審核項 3） |
| tsmc/photo_9.jpg | CC0 | 退件 | 攤位人物（審核項 3） |
| mediatek/photo_4.jpg | CC BY-SA 2.0 | 退件 | 手部與小產品特寫、辨識不足 |
| mediatek/photo_5.jpg | CC BY-SA 4.0 | 通過 | 聯發科新竹總部（篤行一路 1 號），招牌立牌為場景一部分，日間 |
| foxconn/photo_5.jpg | CC BY-SA 4.0 | 通過 | 鴻海土城頂埔廠大門與廠區，日間、無人臉 |
| foxconn/photo_6.jpg | Public domain | 退件 | 人物為主角（審核項 3） |
| foxconn/photo_7.jpg | CC BY-SA 4.0 | 退件 | 主機板局部，看不出鴻海 |
| foxconn/photo_8.jpg | CC BY-SA 4.0 | 退件 | 散熱片局部，辨識不足 |
| quanta/photo_5.jpg | CC BY-SA 2.0 | 通過 | 廣達雲端伺服器（COSCUP 展示），代表產品，景深乾淨 |
| quanta/photo_6.jpg | CC BY 2.0 | 退件 | 人物為主角（審核項 3） |
| quanta/photo_7.jpg | CC BY 2.0 | 退件 | 2008 年舊產品、他牌展示卡入鏡 |
| quanta/photo_8.jpg | CC BY-SA 2.0 | 退件 | LOGO 牆為主角（審核項 4） |
| wistron/photo_8.jpg | CC0 | 通過 | 緯創越南廠區，招牌為場景一部分 |
| wistron/photo_9.jpg | CC BY-SA 4.0 | 退件 | 子公司緯創軟體大廳、LOGO 為主角 |
| wistron/photo_10.jpg | CC0 | 退件 | 公車亭為主角，非公司建築 |
| wistron/photo_11.jpg | CC0 | 通過 | 緯創捷克廠區建築，黃昏原色 |
| ase/photo_7.jpg | CC BY 3.0 | 退件 | 上海「日月光」住宅區，同名不同公司（主體錯誤） |
| ase/photo_8.jpg | CC BY 3.0 | 退件 | 汐止「日月光中心」，同名不同公司（主體錯誤） |
| ase/photo_9.jpg | CC BY 2.0 | 退件 | 無塵衣人物為主角（審核項 3） |
| ase/photo_10.jpg | CC BY 2.0 | 退件 | 無塵衣人物為主角（審核項 3） |
| umc/photo_2.jpg | CC BY-SA 3.0 | 退件 | 招牌立牌為畫面主角（審核項 4） |
| umc/photo_3.jpg | CC BY-SA 4.0 | 通過 | 聯電 8AB 廠外觀，日間 |
| umc/photo_4.jpg | CC BY-SA 4.0 | 通過 | 聯電竹科聯合大樓，日間藍天 |
| unimicron/photo_5.jpg | CC BY-SA 4.0 | 退件 | 1970 年代他牌電路板，非欣興 |
| nanya_tech/photo_1.jpg | CC BY 2.0 | 退件 | 人物為主角（審核項 3） |
| nanya_tech/photo_2.jpg | CC BY 2.0 | 退件 | 動土典禮會場（事件畫面） |
| nanya_tech/photo_3.jpg | CC BY 2.0 | 退件 | 祭祀供品特寫，非公司實景 |
| nanya_tech/photo_4.jpg | CC BY 2.0 | 退件 | 人物與媒體（審核項 3） |
| nanya_tech/photo_5.jpg | CC BY-SA 4.0 | 退件 | Infineon 產品，他牌 LOGO（主體錯誤） |
| nanya_tech/photo_6.jpg | CC BY-SA 4.0 | 退件 | Infineon 產品，他牌 LOGO（主體錯誤） |
| nanya_tech/photo_7.jpg | CC BY-SA 4.0 | 退件 | TI 晶片，他牌 LOGO（主體錯誤） |
| nan_ya_pcb/photo_1.jpg | CC BY-SA 4.0 | 退件 | 1970 年代他牌電路板，非南電 |
| nan_ya_pcb/photo_2.jpg | CC BY 4.0 | 退件 | 他牌音響電路板，非南電 |
| nan_ya_pcb/photo_3.jpg | CC BY-SA 3.0 | 退件 | 他牌電路板，非南電 |
| eml/photo_1.jpg | CC BY-SA 4.0 | 退件 | 倫敦街景倒影，非台光電（主體錯誤） |
| eml/photo_2.jpg | CC BY-SA 4.0 | 退件 | 倫敦街景倒影，非台光電（主體錯誤） |
| eml/photo_3.jpg | CC BY-SA 4.0 | 退件 | 他牌 DVD 電路板，非台光電 |
| eml/photo_4.jpg | CC BY-SA 4.0 | 退件 | 他牌電路板，非台光電 |
| eml/photo_5.jpg | CC BY 2.0 | 退件 | 他牌電路板，非台光電 |
| delta/photo_9.jpg | CC BY-SA 4.0 | 退件 | 警告標籤為主角 |
| delta/photo_10.jpg | CC BY-SA 3.0 | 退件 | 陰天灰暗、建築同框他家公司，主體存疑 |
| delta/photo_11.jpg | CC BY-SA 4.0 | 通過 | 台達電太陽能逆變器（2019 電腦展），代表產品 |
| delta/photo_12.jpg | CC BY-SA 4.0 | 通過 | 台達電鋰電池模組（2019 電腦展），代表產品 |
| arm/photo_5.jpg | Public domain | 退件 | 手寫信件，與 Arm 無關（主體錯誤） |
| arm/photo_6.jpg | CC BY-SA 4.0 | 退件 | Raspberry Pi 板子，非 Arm（他牌） |
| arm/photo_7.jpg | CC BY-SA 4.0 | 退件 | 他牌 PROM 晶片，非 Arm |

審完各家已審張數：Alphabet 5、Microsoft 5、Apple 6、Amazon 7、Meta 2、NVIDIA 3、Intel 5、AMD 4、Broadcom 2、Micron 4、Tesla 1、Oracle 4、OpenAI 1、三星 1、SK 海力士 2、台積電 3、聯發科 1、鴻海 1、廣達 1、緯創 4、日月光 2、聯電 2、欣興 2、台達電 5、Qualcomm 2、Arm 1。**仍是 0 張**（主體出現時退到該公司類別池，不會用別家公司圖）：CoreWeave、Anthropic、南亞科、南電、台光電、ASML。下一步：`targets.json` 換更精準的 Commons 分類名重抓。

## 第八節　art-director 複審 10-30（2026-10-30）

> 任務：複審第七節新通過的 27 張，並補齊缺圖公司。逐張看 952×424 中段裁切聯絡表，疑慮張再看全解析度。檢查：確實是該公司（總部／廠區／產品）、非同名別家、無人物為主角、無浮水印、裁成封面橫幅後主體仍在、授權可商用且作者／原始網址完整（pool.json 已有，全部 CC0／CC BY／CC BY-SA／公有領域）。
> 附註：第七節表格漏列 delta/photo_11、photo_12（Delta 產品，品牌字樣清楚），這兩張也在 27 張內，複審通過。

### 一、27 張複審：通過 23／退件 4

| 檔名 | 結論 | 說明 |
|---|---|---|
| apple/photo_6.jpg | 退件 | 環形屋頂被樹木遮住大半，裁成橫幅後主體辨識不足 |
| apple/photo_9.jpg | 退件 | 畫面無 Apple 招牌或標誌（只有門牌號碼），無法辨識為 Apple |
| micron/photo_10.jpg | 退件 | 記憶體條在畫面中很小、置於紙板上，無 Micron／Crucial 字樣可辨 |
| quanta/photo_5.jpg | 退件 | 伺服器無廣達標示，右下角有攝影者署名字樣（疑似浮水印） |
| 其餘 23 張 | 通過 | alphabet 5／8、amazon 8／9／11、amd 6、broadcom 4、delta 11／12、foxconn 5、intel 6、mediatek 5、microsoft 9／12、nvidia 9、oracle 5／7、sk_hynix 6／7、umc 3／4、wistron 8／11 |

通過但有提醒：mediatek/photo_5 招牌在畫面下緣，取封面橫幅時裁切要偏下（置中裁會切掉招牌，建築仍在）；foxconn/photo_5 廠區在畫面上半部，裁切要偏上；兩家都不要置中硬裁。

### 二、補圖（company_photos.yml run 40988913001、40989565773，改 `commons_categories`／queries，公司分類名額 4→6、總部/廠房 2→3）

第一輪共抓 65 張新圖：通過 10／退件 55；第二輪抓 41 張：通過 0／退件 41（全是主體錯誤或有人物）。

通過的 10 張：asml 3（ASML 品牌貨櫃）、asml 4（維爾德霍芬 Gebouw 3）、asml 7（維爾德霍芬總部）、openai 12／14（Pioneer Building，OpenAI 舊金山總部，14 有「PIONEER BUILDING」招牌）、samsung 13（Galaxy Fold 展示，勉強通過：背景略暗）、tesla 13（Powertrain 展示）／15（總部大門＋Tesla Semi）／18（帕羅奧圖總部）、meta 8（Ray-Ban Meta 眼鏡）。

| 公司 | 已審通過張數（補前→補後） | 備註 |
|---|---|---|
| 台積電 tsmc | 3→3 | 兩輪都補不到無人物新圖（Commons 的 TSMC 分類以人物活動照為主，全退） |
| NVIDIA | 3→3 | 新抓 0 張 |
| OpenAI | 1→3 | 達標 |
| 三星 samsung | 1→2 | 差 1 張：Commons 只有門市／展場（行人入鏡）與他牌記憶體條 |
| Tesla | 1→4 | 達標 |
| Arm | 1→1 | 只有 Raspberry Pi／手稿等無關圖 |
| Meta | 2→3 | 達標 |
| 日月光 ase | 2→2 | 新抓 0 張（上一輪的同名住宅區已列退件名單，不再抓） |
| 欣興 unimicron | 2→2 | 新抓 0 張 |
| ASML | 0→3 | 達標 |
| CoreWeave | 0→0 | 找不到 |
| Anthropic | 0→0 | 找不到 |
| 南亞科 nanya_tech | 0→0 | 找不到 |
| 南電 nan_ya_pcb | 0→0 | 找不到 |
| 台光電 eml | 0→0 | 找不到 |

### 三、仍不足的公司與查過的分類／關鍵字（容器連不到 Commons，只能靠 Actions 搜尋；WebSearch 搜不到 Commons 頁面）

- CoreWeave：分類 CoreWeave、CoreWeave Inc.、CoreWeave data centers、Core Scientific、Livingston New Jersey；查詢 CoreWeave headquarters／Livingston office／Lancaster data center／Ellendale／GB200 NVL72 rack。結果只抓到無關資料中心與州景。公司 2017 年成立、2025 年上市，Commons 幾乎沒有實景照。
- Anthropic：分類 Anthropic、Anthropic PBC、Claude (language model／chatbot)、Anthropic headquarters、500 Howard Street、Salesforce Tower San Francisco；查詢辦公室、Seattle office。結果只有 Dario Amodei 人物照與無關場景，全退。
- 南亞科：分類 Nanya Technology（含 Corporation／Corp／headquarters／Linkou／Taoyuan／DDR4／buildings）、Taishan New Taipei、Linkou District；查詢含中文「南亞科技 林口／泰山」。只有動土典禮人物與他牌 DRAM（Infineon、Samsung），全退。
- 南電：分類 Nan Ya PCB（含 Corp／Corporation／Printed Circuit Board／Kunshan／Shulin Plant／Taoyuan plant）、Nanya PCB、Formosa Plastics Group、Nanya Plastics；查詢含「南亞電路板 樹林廠」、ABF substrate。抓到的是台塑集團他廠（南亞塑膠、台塑化纖）與他牌電路板，不是南電，全退。
- 台光電：分類 Elite Material（含 Co Ltd／Co., Ltd.／Corporation Taiwan／EMC laminate）、Taoyuan Zhongli Industrial Zone；查詢含「台光電子材料」「台光電子 楊梅」。抓到倫敦／休士頓／曼徹斯特無關建築與他牌電路板，全退。
- Arm：分類 Arm Holdings（含 Ltd／headquarters／Cortex／Neoverse／Cambridge Peterhouse Technology Park／110 Fulbourn Road）；只有 Raspberry Pi 等非 Arm 品牌圖。
- 三星、日月光、欣興：各補到上限仍差 1 張，查過分類見 targets.json 的 commons_categories。
- 建議（Commons 找不到的公司）：這些公司短期內封面維持用類別通用圖池（資料中心、記憶體、PCB 基板等），或由 Andy 提供／授權公司新聞稿官方圖；不要用人物照或他牌圖頂替。

## 第九節　官方新聞圖使用規則（法遵初判，2026-10-30）

> ★ 這是**風險盤點與待確認清單，不是法律意見**。每條標「出處＋信心度＋要不要找專業人士」。
> 查證方式：只用 WebSearch 摘要（容器打不開原網頁），所以多數公司的「原文條款」是**未確認**，不是「沒有條款」。
> 起因：Andy 10-30「跟公司有關的優先附上公司圖片」；第八節列出 Commons 找不到實景照的公司（CoreWeave、Anthropic、南亞科、南電、台光電、Arm），以及照片偏少的三星、日月光、欣興。

### 一、先講結論

**預設不可以**直接把公司新聞室／press kit／新聞稿附圖拿來當 IG／Threads 封面。要用，只有兩條路：
1. 該公司條款**明文**允許「非媒體、在社群轉貼、可裁切」的用途（目前查到的公司**沒有一家**明文允許）；或
2. **書面授權**（寄信給公關窗口，拿到回覆信，存檔）。

理由（三點，逐條附出處）：

| # | 理由 | 出處 | 信心度 | 要不要找專業人士 |
|---|---|---|---|---|
| 1 | 授權範圍「約定不明的部分推定為未授權」。press kit 通常寫給媒體報導用，我們不是媒體，超出範圍就是未授權。 | 著作權法第 37 條第 1 項（植根法律網轉載條文摘要） | 高 | 否（條文明確） |
| 2 | 第 52 條「引用」要以**自己的著作為主、被引用的為附屬**；臺北地院 113 年度智字第 16 號把他人照片原樣上傳臉書，認定不適用第 52、65 條。封面圖是整張圖片的主視覺，不是附屬。 | 著作權法第 52、64、65 條；臺北地院 113 智 16 判決（司法院判決書 PDF 摘要） | 中高 | 是（若要主張合理使用） |
| 3 | 第 49 條「時事報導」限**報導者在報導過程中接觸到的著作**，且法院見解偏向「當日事件的單純報導」；新聞室圖庫的照片不是報導過程中接觸到的，而且我們的帳號是網站行銷管道，主張「報導者」身分偏弱。 | 著作權法第 49 條；理律／淡江時報整理的智慧財產法院見解；智財法院 105 民著上易 2（營利媒體使用攝影著作不構成合理使用） | 中 | 是 |

另外兩個加重因素：
- **帳號性質**：IG／Threads 是網站的導流管道，網站之後可能收訂閱費（見本專案證顧法熱點）。「非商業」的主張會隨收費而變弱。信心度：中。
- **加工**：我們的版型會**裁切**＋在下方白底加字。多家條款寫「不得修改」（三星半導體新聞室明文「禁止任意修改」），裁切可能就踩線。信心度：中。

### 二、逐家結果（2026-10-30 查證）

| 公司 | 官方媒體資源 | 查到的條款 | 判斷 | 信心度 | 專業確認 |
|---|---|---|---|---|---|
| CoreWeave | 新聞室在官網 Newsroom；新聞稿經 Business Wire 發布、部分附多媒體；媒體窗口 press@coreweave.com | **未確認**（沒找到媒體資源頁或圖片條款） | **不可用**（待授權） | 中 | 取得授權後免 |
| Anthropic | anthropic.com/news 有「下載 press kit」；窗口 press@anthropic.com | **未確認**（press kit 授權文字查不到） | **不可用**（待授權）；另注意 Anthropic 標誌屬商標，即使能下載也不代表可當行銷封面 | 中 | 取得授權後免 |
| 南亞科（2408） | 官網 nanya.com 有新聞稿區（未驗證）；沒找到圖庫 | **未確認** | **不可用**（待授權） | 中 | 取得授權後免 |
| 南電（8046） | 官網 nanyapcb.com.tw（Yahoo 股市公司資料頁列出）；沒找到圖庫 | **未確認** | **不可用**（待授權） | 中 | 取得授權後免 |
| 台光電（2383） | 沒找到官方媒體資源頁 | **未確認** | **不可用**（待授權） | 中 | 取得授權後免 |
| Arm | newsroom.arm.com/media 只提供**公司標誌與使用規範**下載；其他素材（含企業影片）要寫信給 Global-PRteam@arm.com | 新聞稿文字可「署名、不修改」自由分享，但**這句只涵蓋新聞稿文字，不涵蓋照片** | **不可用**（照片沒有公開圖庫，要申請） | 中高 | 取得授權後免 |
| 三星（記憶體／半導體） | 三星半導體新聞室 news.samsungsemiconductor.com；三星全球新聞室圖庫 news.samsung.com/medialibrary | 半導體新聞室：依 CCL 授權，**僅限個人、非商業**、須標示原作者、**禁止商業用途與任意修改**；三星開發者論壇的三星人員回覆「新聞室圖片只能用於媒體刊物」（非正式） | **有條件可用（很窄）**：①不裁切、不疊字（整張完整放、四周留白）②標「圖：Samsung Semiconductor Newsroom」③帳號與網站**沒有收費、沒有廣告**時才成立。網站一旦收費 → 改成不可用 | 中低 | **是**（「行銷導流帳號是否算非商業」要專業確認） |
| 日月光 | 官網 ase.aseglobal.com 有新聞稿；沒找到圖庫；北美／歐洲與亞太媒體窗口在 Business Wire 新聞稿中有列 | **未確認** | **不可用**（待授權） | 中 | 取得授權後免 |
| 欣興 | 官網 unimicron.com；沒找到圖庫 | **未確認** | **不可用**（待授權） | 中 | 取得授權後免 |

⚠ 表中「未確認」的意思是**查不到條款原文**，不代表「沒禁止所以可以用」。著作權法第 37 條：約定不明推定為未授權。

### 三、三堆分開

**可以做**
- 用 Wikimedia Commons 的 CC0／CC BY／CC BY-SA／公有領域照片（第一節既有規則，不變）。信心度：高。
- 用類別通用圖池（資料中心、記憶體、PCB 基板等，第八節建議）。信心度：高。
- 用我們自己畫的圖（K 線、營收長條、站內圖表截圖）當封面。信心度：高。
- 封面用**文字**寫公司名（例如「南亞科（2408）」），不放標誌。信心度：高。

**要改做法才能做**
- **官方新聞圖** → 先寄信取得書面授權（範本見第四節），回信存 `social/photo_lib/<slug>/license_email.txt`（**不得含個人信箱以外的敏感資料；repo 是 public，對方姓名與電話要遮掉**），`meta.json` 的 license 寫 `written-permission`，再走 art-director 審核。
- **三星半導體新聞室圖** → 只在「完整不裁切、不疊字、標來源、帳號未收費」四條件同時成立時用；收費前要整批下架或換圖。這條要專業人士確認後才上線。

**不要做**（每條附替代做法）
| 不要做 | 替代做法 |
|---|---|
| 直接從新聞室、press kit、Business Wire 新聞稿附圖、公司官網抓圖當封面 | Commons 圖／類別通用圖池／自製圖表；或先拿書面授權 |
| 用「圖：公司官方」標示當作已取得授權 | 標示是第 64 條的義務，**不是授權**；先授權、再標示 |
| 用媒體報導裡的照片（中央社、工商、Getty 等） | 同上。中央社明文「非經授權不得轉載」；Getty 是付費授權 |
| 用公司標誌（logo）當封面主視覺 | 文字寫公司名；標誌涉及商標與著作權，非必要不用 |
| 用人物照（董事長、執行長）當封面 | 人像另有肖像權問題；改用總部／產品／類別圖 |
| 用 AI 生成「看起來像某公司廠房」的圖 | 會讓人誤以為是實景，也可能被當成仿冒；不做 |

### 四、取得授權信範本（可直接貼上）

主旨：申請使用貴公司新聞照片於財經資訊社群貼文

> 您好，我們是「台股資金輪動儀表板」（https://liguligu-puipui.com/）的經營者，在 Instagram 與 Threads 發布台股與科技產業的公開資料整理貼文。
>
> 想申請使用貴公司新聞室的下列照片：〔照片標題或網址〕，用途如下：
> 1. 作為報導貴公司相關公開消息（例如月營收、法說會、重大訊息）貼文的封面圖；
> 2. 版面會將照片等比例縮放，可能裁切邊緣，並在照片**下方**白底區加上標題文字，不會在照片上覆蓋文字、不改變顏色與內容；
> 3. 每篇標示「圖：〔公司名〕官方」；
> 4. 貼文為免費公開內容，不作為任何產品的廣告。
>
> 請問是否同意上述使用？若有署名格式、使用期限或不得使用的情境，也請告知，我們會照辦。若不同意，我們不會使用。
>
> 謝謝。〔署名〕〔聯絡信箱〕

外商（CoreWeave、Anthropic、Arm、三星）寄出前翻成對方語言；窗口：press@coreweave.com、press@anthropic.com、Global-PRteam@arm.com（窗口以寄信當下官網為準）。

### 五、實作規則（給 social-live 與 art-director）

1. `meta.json` 的 `license` 只准是：`CC0`、`CC BY*`、`CC BY-SA*`、`PD`、`written-permission`。其他值（含 `press-kit`、`newsroom`、`editorial`）一律不准排程。
2. `written-permission` 必須有同資料夾的授權信存檔，且信中用途涵蓋「社群貼文封面＋裁切」；沒涵蓋裁切就只能完整放。
3. 授權有期限的，到期前 7 天要從圖池移除。
4. 有人（公司或攝影者）來信要求下架 → 當天下架、回信、記在本節第六項，不爭辯。
5. 網站開始收費前，本節全部重新評估一次（特別是三星「非商業」那條）。

### 六、待專業人士確認（法遵帳）

| # | 問題 | 為什麼要確認 | 優先度 |
|---|---|---|---|
| 1 | 網站導流用的社群帳號，發免費新聞整理貼文，算不算「商業使用」？收費後呢？ | 決定三星「非商業」條款能不能用，也影響第 65 條合理使用判斷 | 高 |
| 2 | 我們的貼文能不能主張第 49 條「時事報導者」？ | 若可以，當日重大訊息的配圖空間會變大；目前判斷偏弱 | 中 |
| 3 | 等比例縮放＋裁切邊緣，算不算條款中的「修改」？ | 決定拿到「不得修改」授權時能不能照現在的版型 | 中 |

### 七、查證來源（WebSearch 摘要，非原文）

- 三星半導體新聞室使用條款：https://news.samsungsemiconductor.com/global/terms-of-use （CCL、個人非商業、須標示原作者、禁止商業與任意修改）— 信心度中
- 三星開發者論壇（新聞室圖片僅供媒體刊物）：https://forum.developer.samsung.com/t/using-an-official-samsung-image-as-a-store-asset/22012 — 非正式，信心度低中
- 三星行動媒體網站條款：https://samsungmobilepress.com/terms （個人、資訊性、非商業）— 信心度中
- Arm 新聞室媒體頁：https://newsroom.arm.com/media （只提供標誌下載，其他素材洽 Global PR）— 信心度中高
- Anthropic 新聞室（press kit 連結、press@anthropic.com）：https://www.anthropic.com/news （透過封存頁摘要得知）— 信心度中
- CoreWeave 新聞稿（Business Wire，媒體窗口）：https://www.businesswire.com/news/home/20250715975958/en — 信心度中
- 日月光 Business Wire 新聞稿（媒體窗口）：https://www.businesswire.com/news/home/20240320843248/en — 信心度中
- 南電官網網址：https://tw.stock.yahoo.com/quote/8046.TW/profile — 信心度中
- 著作權法第 49、52、65 條判決見解整理：https://www.leeandli.com/TW/Newsletters/5895.htm 、https://tkutimes.az.tku.edu.tw/fpdf/59263.pdf — 信心度中
- 臺北地院 113 年度智字第 16 號（臉書上傳他人照片不適用第 52、65 條）：https://judgment.judicial.gov.tw/FILES/TPDV/113,智,16,20241206,1.pdf — 信心度中高
- 著作權法第 37 條「約定不明推定未授權」：https://www.rootlaw.com.tw/LetterContent.aspx?LCode=13&SOID=251813 — 信心度高
- 中央社版權聲明（不得轉載）：https://www.cna.com.tw/news/afe/202510073004.aspx — 信心度高
- 查不到條款的公司（南亞科、南電、台光電、日月光、欣興、CoreWeave、Anthropic）用過的關鍵字：「新聞中心 圖片 下載」「網站使用條款」「版權所有」「media kit images」「press kit terms」「photo courtesy」；來源類型：官網、Business Wire、財經媒體、股市資料站。
