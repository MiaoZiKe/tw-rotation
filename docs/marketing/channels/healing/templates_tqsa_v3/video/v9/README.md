# v9 量產流程（稿件驅動）

- 格式：`SCRIPT_FORMAT.md`；插圖主體：`ILLUSTRATIONS.md`（`illustrations/`）
- 一支：`bash v9/make_video.sh queue/<名> [--voice]`（`--voice` 才配音，先念稿檢查；已有 narration_take.wav 就不送 TTS）
- 同批多支一次 TTS：`bash v9/voice_batch.sh <資料夾1> <資料夾2> … [--take 已有錄音.wav] [--no-render]`（≤5 支、≤1,200 字）
- 自動修正：`python3 v9/autofix.py <資料夾> [--voice]`（最多 3 輪）
- 驗證與搬家：`reverse_spec.py`、`verify_equiv.py`；念稿檢查：`check_narration.py`
- 不呼叫 TTS 的離線驗證已做（見 commit 訊息）；真送 TTS 的 voice_batch 尚未跑過。
