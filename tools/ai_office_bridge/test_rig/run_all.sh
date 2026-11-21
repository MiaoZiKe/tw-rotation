#!/usr/bin/env bash
# 一鍵重跑主要實測。用法：bash run_all.sh [工作資料夾]（預設 /tmp/aio_bridge_test）
# 需要：已登入的 Claude Code（claude --version 能跑）、python3、curl。全程只連 127.0.0.1:8765。
# 會用到少量模型額度（每段一兩個很短的回合，模型用 haiku）。不會動到你的 ~/.claude 設定：
# 專案掛鉤寫在工作資料夾自己的 .claude/settings.json；外掛安裝那段用獨立的 CLAUDE_CONFIG_DIR。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(dirname "$HERE")"
W="${1:-/tmp/aio_bridge_test}"; mkdir -p "$W/logs" "$W/p1" "$W/p2" "$W/p3"; echo hello > "$W/p1/a.txt"; echo x > "$W/p2/b.txt"; echo y > "$W/p3/c.txt"
export AIO_LOGDIR="$W/logs"
python3 "$HERE/receiver.py" 8765 >/dev/null 2>&1 & RPID=$!; trap 'kill $RPID 2>/dev/null' EXIT; sleep 1
C="--setting-sources project,local --model haiku --permission-mode dontAsk"
push(){ curl -s --noproxy '*' -X POST 127.0.0.1:8765/inbox/push -H 'Content-Type: application/json' -d "{\"text\":\"$1\"}" >/dev/null; }

echo "== 1 所有事件的欄位（專案掛鉤）→ $W/logs/e1.jsonl"
python3 "$HERE/gen_settings.py" "$W/p1" all
(cd "$W/p1" && AIO_LOG="$W/logs/e1.jsonl" claude -p "請用 Agent 工具派出一個 general-purpose 子 Agent，說明寫「列出檔案」，請它用 Bash 執行 ls 並回報檔名。拿到結果後一句話回報。" $C --allowedTools Agent "Bash(ls:*)" --output-format json </dev/null >"$W/logs/e1_out.json")
python3 -c "import json,sys;[print(json.loads(l)['tag']) for l in open('$W/logs/e1.jsonl')]"

echo "== 2 HTTP 掛鉤：正常／很慢／連不上／回 500 → $W/logs/http_events.jsonl、e2_debug.log"
python3 "$HERE/gen_settings.py" "$W/p1" http
(cd "$W/p1" && AIO_TOKEN=test-token-not-secret AIO_LOG="$W/logs/e2.jsonl" claude -p "用 Bash 執行 ls 一次，然後回答看到的檔名。" $C --allowedTools "Bash(ls:*)" --output-format json --debug-file "$W/logs/e2_debug.log" </dev/null >"$W/logs/e2_out.json")
grep -E 'HTTP hook|Slow' "$W/logs/e2_debug.log" | cut -c1-160

echo "== 3 Stop 掛鉤把網站訊息交給 Claude（腳本版）→ 應看到 391"
python3 "$HERE/gen_settings.py" "$W/p1" stopcmd; push "請再告訴我 17 乘以 23 等於多少，只回數字。"
(cd "$W/p1" && claude -p "只回答兩個字：收到" $C --output-format json </dev/null | python3 -c "import json,sys;d=json.load(sys.stdin);print('最後回覆:',d['result'],'回合數:',d['num_turns'])")
echo "== 3b 同上，但由 HTTP 掛鉤的回應直接帶 decision（不需腳本）"
python3 "$HERE/gen_settings.py" "$W/p1" stophttp; push "請再告訴我 17 乘以 23 等於多少，只回數字。"
(cd "$W/p1" && claude -p "只回答兩個字：收到" $C --output-format json </dev/null | python3 -c "import json,sys;d=json.load(sys.stdin);print('最後回覆:',d['result'],'回合數:',d['num_turns'])")
echo "   收件端收到的回覆："; cut -c1-200 "$W/logs/replies.jsonl"

echo "== 4 UserPromptSubmit／SessionStart 附加內容 → 應列出兩個暗號"
python3 "$HERE/gen_settings.py" "$W/p1" ctx
(cd "$W/p1" && claude -p "你的上下文裡有沒有看到「暗號」？有就逐一列出。" $C --output-format json </dev/null | python3 -c "import json,sys;print(json.load(sys.stdin)['result'])")

echo "== 5 外掛（使用者範圍安裝，獨立設定資料夾）在兩個沒有任何設定的專案都觸發"
export CLAUDE_CONFIG_DIR="$W/cfg"; mkdir -p "$CLAUDE_CONFIG_DIR"
claude plugin marketplace add "$ROOT/plugin" | tail -1; claude plugin install ai-office-bridge@ai-office-local --scope user | tail -1
for d in p2 p3; do (cd "$W/$d" && AIO_URL=http://127.0.0.1:8765 AIO_TOKEN=test-token-not-secret AIO_RAW_LOG="$W/logs/e5.jsonl" claude -p "請用 Agent 工具派出一個 general-purpose 子 Agent（說明寫「數檔案」），請它用 Bash 執行 ls 並回報檔名。拿到結果後一句話回報。" --model haiku --permission-mode dontAsk --allowedTools Agent "Bash(ls:*)" --output-format json </dev/null >/dev/null); done
python3 -c "import json;[print(json.loads(l)['tag'], json.loads(l)['payload'].get('cwd','')[-3:], json.loads(l)['payload'].get('agent_type','')) for l in open('$W/logs/e5.jsonl')]"
unset CLAUDE_CONFIG_DIR

echo "== 6 自建 MCP 收件匣工具 → 應回 42"
push "請回報 12 加 30 等於多少"
echo "{\"mcpServers\":{\"aioffice\":{\"command\":\"python3\",\"args\":[\"$HERE/mcp_inbox.py\"]}}}" > "$W/logs/mcp.json"
(cd "$W/p2" && claude -p "請呼叫 aioffice 的 get_pending_messages 工具讀取待處理訊息；有訊息就照內容回答，並用 send_reply 送回去。" --mcp-config "$W/logs/mcp.json" --strict-mcp-config $C --allowedTools mcp__aioffice__get_pending_messages mcp__aioffice__send_reply --output-format json </dev/null | python3 -c "import json,sys;print(json.load(sys.stdin)['result'])")

echo "== 7 閒置喚醒（asyncRewake）：回合結束 20 秒後才推訊息 → 應自己醒來回 81"
mkdir -p "$W/p3/.claude"
echo "{\"hooks\":{\"Stop\":[{\"hooks\":[{\"type\":\"command\",\"command\":\"python3 $HERE/wait_inbox.py\",\"asyncRewake\":true,\"timeout\":90}]}]}}" > "$W/p3/.claude/settings.json"
rm -f "$W/logs/fifo"; mkfifo "$W/logs/fifo"
(cd "$W/p3" && AIO_WAIT=45 timeout 70 claude -p --input-format stream-json --output-format stream-json --verbose $C <"$W/logs/fifo" >"$W/logs/e7_out.jsonl" 2>&1 &)
exec 9>"$W/logs/fifo"; echo '{"type":"user","message":{"role":"user","content":"只回答兩個字：收到"}}' >&9
sleep 20; push "請告訴我 9 乘以 9 等於多少，只回數字。"; sleep 20; exec 9>&-; sleep 5
grep '"type":"result"' "$W/logs/e7_out.jsonl" | python3 -c "import json,sys;[print('回覆:',json.loads(l).get('result')) for l in sys.stdin]"
echo "完成。原始紀錄在 $W/logs/"
