#!/usr/bin/env bash
# AI 辦公室「真的」端到端驗證：網站 ⇄ 收件服務（wrangler dev --local）⇄ 真的 Claude Code（claude -p 待命模式）。
# 說明與結果判讀：docs/ai_office/e2e_report_1115.md
#   bash scripts/e2e/ai_office_e2e.sh [輸出資料夾] [--model sonnet] [--keep]
# 需要：python3＋playwright（/opt/pw-browsers/chromium）、node／npm（第一次會把 wrangler 裝到輸出資料夾）、/opt/node22/bin/claude 已登入。
# 用到埠 8805（網站）、8806（收件服務）、8807（假會員服務）；有人在用就直接停下，不會去關別人的程式。
# 費用：只開一個 claude -p 工作階段（約 4 則小指令＋2 位子 Agent），一輪大約 6～10 分鐘。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-${TMPDIR:-/tmp}/ai_office_e2e_$(date +%Y%m%d_%H%M%S)}"
[ $# -gt 0 ] && shift
mkdir -p "$OUT"
echo "輸出資料夾：$OUT"
exec python3 "$ROOT/scripts/e2e/ai_office_e2e.py" --out "$OUT" "$@"
