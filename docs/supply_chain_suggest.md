# supply_chain.yaml 校訂建議稿（2026-09-19）

> **這份檔案不會被程式讀。** `pipeline/groups/supply_chain.yaml` 的內容是 Andy 自己校訂的
> （CLAUDE.md：「groups.yaml / themes.yaml / supply_chain.yaml 的成分他會自己校訂」），
> 所以這裡只列「我在畫圖十的時候撞到的事實問題」，不自動改。
> 每一條都標了**為什麼會撞到**，勾掉一條就把對應的 YAML 改掉。

修完之後 `scripts/_uitest.py` 的 `SC_ISO_MAX`（孤立節點上限，目前 ai_server 10 / semiconductor 13）
可以一路往下調；那條驗收是棘輪，只准變少。

---

## A. 環節分類：設備／材料商被當成製程環節

`adv_pkg`（先進封裝 CoWoS/SoIC）這個環節裡混了三家**設備商**：

| 公司 | 現在的 segment | 建議 | 理由 |
| --- | --- | --- | --- |
| 弘塑 3131 | `adv_pkg` | 新環節 `pkg_equipment` | 濕製程設備，不是封裝廠 |
| 辛耘 3583 | `adv_pkg` | 新環節 `pkg_equipment` | 濕製程／再生晶圓設備 |
| 萬潤 6187 | `adv_pkg` | 新環節 `pkg_equipment` | 點膠／封裝設備 |

建議在 `segments:` 新增一段（**`role: equipment` 這個欄位前端已經吃了** ——
設備／材料環節的線會畫成灰色細線，不跟主鏈搶視覺）：

```yaml
- id: pkg_equipment
  chain: semiconductor
  layer: 3
  name: 封裝設備 / 濕製程
  role: equipment          # equipment | material，前端據此畫灰線
```

同理，`ccl`（CCL 銅箔基板）本質是**材料**，可以加 `role: material`。

## B. 可疑的邊

| 邊 | 疑點 |
| --- | --- |
| 台光電 2383 → 欣興 3037（CCL） | 欣興以 ABF 載板為主，載板用的是**味之素 ABF 膜＋玻纖布**，不是台光電的高速 CCL。台光電的 CCL 主要走**交換器／伺服器主板**（金像電、健鼎那條線）。建議改成 台光電 → 金像電 2368。 |
| `competes` 兩條 | 圖十已經**不畫**競爭關係（那不是上下游，畫了會被誤讀成供貨）。若要在畫面上表達競爭，之後另開一種呈現，不要塞在關聯圖裡。 |

## C. 缺的邊（造成節點孤立）

下面是**目前完全沒有任何上下游關聯**的公司，畫面上它們右上角會有一個橘色「?」。
括號裡是我猜的補法，請 Andy 確認之後再寫進 YAML。

### AI 伺服器鏈（10 家）

| 環節 | 孤立的公司 | 建議補的邊 |
| --- | --- | --- |
| IC 設計 | Marvell、瑞昱 2379 | Marvell → hyperscaler（ASIC／光通訊 DSP）；瑞昱 → switch（交換器晶片 → 智邦） |
| 晶圓代工 | 聯電 2303 | 聯電 → 瑞昱 / 聯詠類（成熟製程） |
| CCL | 台燿 6274 | 台燿 → 金像電 2368（高速 CCL） |
| ABF 載板 | 南電 8046、景碩 3189 | 兩家 → nvidia / amd（同 欣興 那條） |
| 先進封裝 | 辛耘 3583 | 改 `pkg_equipment` 後：辛耘 → 台積電（設備） |
| 散熱 | 健策 3653 | 健策 → nvidia（均熱片 VC） |
| 光通訊 | 波若威 3163、聯亞 3081 | 兩家 → 華星光 4979 或 → hyperscaler（光收發模組） |

### 半導體鏈（13 家）

| 環節 | 孤立的公司 | 建議補的邊 |
| --- | --- | --- |
| IP / EDA / 設計服務 | 創意 3443、世芯-KY 3661、智原 3035 | 這三家**在 AI 伺服器鏈裡有線**（→ hyperscaler），但 `hyperscaler` 不屬於半導體鏈的環節，所以在半導體鏈的圖上被整條丟掉。兩種解法：①補「設計服務 → 晶圓代工」的邊（三家都用台積電）②把 `hyperscaler` 也列進半導體鏈的 `CHAIN_EXTRA`。**建議①** —— 那才是半導體鏈上真的存在的關係。 |
| IC 設計 | Marvell、瑞昱 2379 | 同上 |
| 晶圓代工 | 聯電 2303 | 同上 |
| ABF 載板 | 南電 8046、景碩 3189、金像電 2368 | 同上 |
| 封測 / 測試 | 力成 6239、矽格 6257、穎崴 6515 | 力成／矽格 → 聯發科 / 瑞昱（封測代工）；穎崴是**測試介面**（探針卡／Socket），建議也歸 `role: equipment`，邊接到 日月光 3711 |
| 先進封裝 | 辛耘 3583 | 同上 |

## D. 順手記一下（不用改 YAML）

- `edges` 的 `strength`（1–5）現在**真的會影響線的粗細**了。以前 `index.html` 的
  `.chainmap .edge{stroke-width:1.2}` 會蓋掉 JS 算出來的粗細，所以每條線都一樣粗；
  現在改用 CSS 變數 `--w` 傳。沒寫 `strength` 的邊一律當 1（最細）。
- `rel` 目前用到的值：`supplies`（實線＋箭頭）、`produced_by`（同上）、
  `outsources_to`（虛線＋箭頭）、`competes`（不畫）。新增別的 `rel` 會退回實線。
