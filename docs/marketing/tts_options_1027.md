# 免費、可客製化的旁白聲音選項（2026-10-27）

| 方案 | 費用 | 能調什麼 | 商用 | 備註 | 信心 |
|---|---|---|---|---|---|
| edge-tts（目前用的） | 免費 | 語速、音高、音量；台灣聲音曉雨／曉臻／雲哲 | ⚠ 非官方介面，條款不明 | 隨時可能被擋 | 中 |
| Azure 語音 F0 免費層 | 每月 50 萬字元免費（神經語音） | 同 edge 聲音＋SSML（停頓、重音、情緒風格） | 免費層商用條款未查到，需確認 | 最平順的升級路徑：聲音不變 | 中（[官方定價頁](https://azure.microsoft.com/zh-tw/pricing/details/speech/)） |
| Google Cloud TTS 免費額度 | 每月有免費字元（數量這次未查證） | SSML、語速音高 | 依 Google Cloud 條款 | 台灣中文聲音選擇較少 | 低 |
| BreezyVoice（聯發科，CosyVoice 架構） | 開源自架、免費 | 台灣腔、多音字較準、可用幾秒樣本複製聲音 | 授權未查到，需看模型頁 LICENSE | 要 GPU 機器 | 中（[arXiv](https://arxiv.org/abs/2501.17790v1)） |
| OpenAI TTS（試聽 6 個聲音用的） | 付費、便宜 | 可用文字指示語氣 | 依 OpenAI 條款可商用 | 不是免費 | 中 |

建議：短期續用 edge-tts 的曉雨可愛版；正式商用前換 Azure F0（同一個聲音），並確認商用條款。

## 2026-10-27 補：「給一段錄音就能一直用」的聲音複製（Andy 原話：「旁白聲音需要是可以我選好適合的聲音，他能下載或是我只給你聽一段錄音檔，就能一直使用」）

| 方案 | 給多少錄音 | 費用 | 授權（可否商用） | 台灣腔 | 試玩／下載 | 信心 |
|---|---|---|---|---|---|---|
| **BreezyVoice（聯發科，建議）** | 約 5～10 秒 | 免費、開源 | 看到的副本標 Apache-2.0（可商用），官方 LICENSE 待讀 | ✅ 專為台灣華語、多音字較準 | [GitHub](https://github.com/mtkresearch/BreezyVoice)・[線上試玩](https://huggingface.co/spaces/paxton0222/BreezyVoice-Playground) | 中 |
| CosyVoice 2（阿里） | 約 3 秒 | 免費、開源 | 第三方標 Apache-2.0，官方待讀 | 普通話為主 | [GitHub](https://github.com/FunAudioLLM/CosyVoice) | 中 |
| GPT-SoVITS | 5 秒可用；1 分鐘微調最像 | 免費、開源 | MIT（可商用） | 看錄音本人 | [GitHub](https://github.com/RVC-Boss/GPT-SoVITS) | 中 |
| ElevenLabs | 約 1 分鐘 | 免費版**不能**複製也不能商用；Starter 約 5～6 美元／月才可 | 付費可商用 | 普通 | [定價](https://elevenlabs.io/pricing) | 中 |

注意：F5-TTS、Fish Speech 的模型權重是非商用授權，不採用。
建議流程：Andy 選一個現成聲音（或錄 10 秒自己的聲音）→ 存成 `docs/marketing/voice/reference.wav` → 每支影片由 GitHub Actions 用 BreezyVoice 以同一段參考音產出旁白。⚠ 用別人的聲音必須取得本人書面同意。
