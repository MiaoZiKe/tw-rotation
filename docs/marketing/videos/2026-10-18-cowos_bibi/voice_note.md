# 配音說明（CoWoS 比比主持版，2026-10-18 台北）

## 三個候選聲音（各一段約 10 秒試聽，同一段台詞）

| 檔案 | 聲音 | 語速／音高 | 聽起來 |
|---|---|---|---|
| `sample_hsiaoyu.mp3` | zh-TW-HsiaoYuNeural（曉雨） | +10%／原音高 | 年輕女聲、台灣口音，偏溫柔 |
| `sample_hsiaochen.mp3` | zh-TW-HsiaoChenNeural（曉臻） | +5%／原音高 | 成熟女聲、台灣口音，像新聞旁白，最清楚 |
| `sample_hsiaoyu_cute.mp3` | zh-TW-HsiaoYuNeural（曉雨）調整版 | +15%／+15Hz | 音高拉高、語速加快，較可愛活潑 |

試聽台詞：「嗨，我是比比！今天用一分鐘，帶你看懂 AI 晶片為什麼一直缺貨，關鍵就在台積電的 CoWoS 先進封裝。」

**正片用 `hsiaoyu_cute`（曉雨調整版）**：比比是白色毛球天竺鼠，曉雨本身就比曉臻年輕，音高再拉高 15Hz 比較像小動物主持人；
語速 +15% 讓 70 秒左右講得完又不趕。曉臻最清楚但偏「主播」，跟比比的可愛形象距離較遠。
三個聲音的整套正片配音都已產生（`voice/<聲音>/L01～L15.mp3`），Andy 選了別的聲音，只要換環境變數重出片：

```
COWOS_VOICE=hsiaochen python docs/marketing/videos/2026-10-18-cowos_bibi/render_cowos.py
```

（字幕對時、比比動作切換點都跟著新聲音的逐字時間軸自動重算。）

## 怎麼產生的

- `.github/workflows/tts.yml`（手動觸發，輸入＝本資料夾的 `tts_script.json`）：GitHub 雲端機器上 `pip install edge-tts==7.3.1`，
  逐句產生 mp3 與逐字時間軸 json（WordBoundary），commit 回同一分支的 `voice/`。不讀、不用任何 secrets。
- 這個開發容器連不到語音服務，所以放在 GitHub Actions 上跑。

## ⚠ 正式發佈前要改

- edge-tts 是微軟 Edge「大聲朗讀」功能的**非官方介面**，沒有服務條款保障商業使用，**這一版只當試做**。
- 正式發佈前改用 **Azure 語音服務（Azure AI Speech）官方 API**：同樣有 zh-TW-HsiaoYuNeural／HsiaoChenNeural，
  可用 SSML 設 rate／pitch，免費層每月有固定字數額度（以 Azure 官網當下公告為準），做這種短片綽綽有餘。
- 換法：`tts.yml` 改呼叫 Azure 語音 REST API（金鑰放 GitHub Secrets），`tts_script.json` 格式不變。
  **現在不需要 Andy 設定任何東西**；要正式發佈時再一步一步帶他申請。
- 發音注意：「CoWoS」由語音引擎自己念，試聽時請留意念法是否自然；不自然的話，正式版可用 Azure 的 SSML 音標（phoneme）指定念法。
