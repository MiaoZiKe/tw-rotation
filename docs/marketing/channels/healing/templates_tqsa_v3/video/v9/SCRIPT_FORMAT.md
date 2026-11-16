# v9 稿件驅動（script.json）

放在 `queue/<日期_名稱>/script.json`（資料夾名＝`queue`＝`id`）。一支指令：`bash v9/make_video.sh queue/<名> [--voice]`；同批多支：`bash v9/voice_batch.sh <資料夾1> <資料夾2> …`。

```json
{ "id": "20261117v_studentloan", "queue": "20261117v_studentloan", "asof": "2026/11/16", "cover_t": 1.9, "narr_para": false,
  "scenes": [
    { "id": "s1", "layout": "hook", "say": "旁白（也是字幕）", "caption": "（選填）字幕改用這段，會覆蓋旁白文字",
      "title": ["第一行", "第二行"], "tag": "已確定｜機構、報告", "source": "資料：機構；報告（日期）",
      "subject": { "id": "rateboard", "keywords": ["新標籤1"], "labels": {"原字": "新字"}, "colors": {"#F4B860": "#E8A040"} },
      "data": { "...": "版型專屬資料，欄位同 v8 specs（見下表）" },
      "opts": { "dur": 6.8, "tagAll": true, "tagAt": 0.42, "capDy": 8, "capBal": true, "once": true, "noglide": true, "tfs": 80 } } ],
  "outro": { "keyword": "學貸", "next": "2027 年的最低工資" } }
```

- `layout`：`hook`（大字＋迷你圖）、`versus`、`ask`、`next`（資料攤平到鏡上：hook＝ulw／big／mini；versus＝a／b／mid／em／emw；ask＝recap／opt；next＝slip／row）；
  圖表 `donut／bars→hbars／vbars／dumbbell／lollipop／slope／band／gantt／stack／steps／people／tiles／split2／lanes／odometer`（資料放 `data`，轉成同名鍵；odometer→`odo`）。
- `subject`：插圖主體，來自 `v9/illustrations/`（清單 `v9/ILLUSTRATIONS.md`）。`keywords` 依「可換標籤」順序逐一取代、`labels` 指定原字→新字、`colors` 換色。要貼近該篇文案，不准放無關通用圖。
- `outro`：只填 `keyword`、`next`；其餘（`say`、`slogan`、`nextLine`、`dur`、`src`）可覆寫。
- `opts`：版型之外的旗標。autofix 會自動加：`tagAll`（靜止）、`tagAt`（標籤撞標題）、`capDy`（字幕碰撞）、`once`／`noglide`（強調淨空不足、光點閃爍）、`capBal`（字幕斷行）。
- 反向產生：`python3 v9/reverse_spec.py <v8 specs 的名> [輸出資料夾]`；驗證：`python3 v9/verify_equiv.py <名>…`。
- 念稿檢查：`python3 v9/check_narration.py <資料夾>`（`--voice` 與 `voice_batch.sh` 會自動先跑，不過就不送 TTS）。
- 新增插圖主體：放 `v9/illustrations/<id>.js` 後 `python3 v9/build_ill_lib.py` 更新索引。
