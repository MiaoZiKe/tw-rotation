# AI 生圖審查紀錄（新聞圖卡封面背景）
- 審查人：**非美編本人，是設計美編 agent 依 `docs/marketing/social_unit/ai_image_review.md` 十條清單自審**（本 session 沒叫 art-director；發布前請另派 art-director 覆核）
- 時間：2026-10-28 15:20（台北）
- 產圖：`.github/workflows/ai_news_images.yml`（run 40646327801），每題各 Pollinations（flux，768×768，右下有浮水印）與 SD-Turbo（CPU，768×512）1 張，結果在 `ai-image-trial` 分支 `news/20261028/`
- prompt：見 `bg/prompts_20261028.py`（共同尾句：明亮白天、無文字、無 logo、無招牌、無真實建築、無人臉特寫）
- 後處理（`render_news_cards.py` 的 `bg_uri`）：Pollinations 先裁掉底部 7% 浮水印帶；放大到 2 倍寬用 Lanczos＋輕微銳化；灰階均值 <130 者提亮到約 135；再縮到 952 寬。**成品是 768 寬放大到 952，仍有軟邊與色帶感，屬 SD-Turbo 解析度限制。**

## 挑選結果
兩個模型 14 張並排看過：Pollinations 的 fab 有人形、memory 有類字形、trading 偏暗、fed 為可辨識的真實式建築且有浮水印，整批退回；SD-Turbo 較亮較清楚，採用其 fab／datacenter／city。

| 圖 | 用在 | 1 無字 | 2 無真實建築人物 | 3 無畸形 | 4 亮度（成品區塊均值） | 5 色調 | 6 不擋標題 | 7 解析度 | 8 主題相符 | 9 版權 | 10 質感 | 結論 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `bg/sdturbo_fab.png` | pre1、intra1 | 通過 | 通過 | 通過（貨架排列略重複，可接受） | 通過 144～149 | 通過（銀灰冷白） | 通過 | **退回邊緣**：768 放大後偏軟；以氣氛圖用途先放行 | 通過（晶圓廠泛型） | 通過 | 通過 | 通過（附註解析度） |
| `bg/sdturbo_datacenter.png` | pre2 | 通過 | 通過 | 通過 | 通過 134 | 通過（青藍） | 通過 | 同上 | 通過（記憶體需求與 AI 伺服器相關，氣氛圖） | 通過 | 通過 | 通過（附註解析度） |
| `bg/sdturbo_city.png` | pre4、intra3 | 通過 | 通過（泛型虛構街區） | 通過（少數樓體交疊略糊，可接受） | 原圖 118 未過，提亮後 129 通過 | 通過（藍＋米） | 通過 | 同上 | 通過（金融區氣氛，不暗示漲跌） | 通過 | 通過 | 通過（附註提亮與解析度） |
| FOMC `fomc_day.jpg` | pre3 | 已通過先前審查（`2026-10-28-fomc-pre/ai_review.md`），本次只裁切不調色 | | | | | | | | | | 沿用 |

## 退回／不使用
- `memory`（SD-Turbo）：成品看起來像太陽能板，易被誤認，違反第 8 條，**不得使用**；原 pre2、intra2 改派。
- `packaging`：大面積綠（電路板），與台股紅漲綠跌語意衝突（第 5 條），**不得使用**。
- `trading`：卡通感、螢幕上有疑似字形，**不得使用**。`fed`（兩個模型）：可辨識為真實式政府建築，**不得使用**，pre3 改用已通過的 FOMC 背景。
- intra2（旺宏／力成財報）：沒有合格的圖，**改純色版**（無照片）。
- 兩個模型的 Pollinations 全部 7 張不採用（浮水印、偏暗、品質較差），僅留在 ai-image-trial 分支。

## 結論
採用 3 張 SD-Turbo 圖（fab、datacenter、city）＋既有 FOMC 背景；intra2 純色。**待 art-director 覆核**，覆核前不要排程。
