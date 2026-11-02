# 哩股哩股 LOGO 第二輪（2026-11-02，美編）

Andy：「LOGO 部分有夠醜，完全沒有美感，幫我改成專業一點」「比比以後不會出現在貼文上」＋CEO：頻道一要明亮親切、不要深海軍藍。

看 `overview.png`。四個候選（皆不用吉祥物）：

| 代號 | 名稱 | 品牌色 | 性格 |
|---|---|---|---|
| A | Li 上揚 | 珊瑚紅底、白 L、陽光黃圓點 | 明亮親切（推薦） |
| B | 輪動圓餅 | 天藍底、白／黃／淡藍＋珊瑚紅抽離塊 | 明亮親切、最直接表達「資金輪動」 |
| C | K 棒上升 | 陽光黃底、白／墨／珊瑚紅棒 | 明亮親切、最直白但最通用 |
| D | 「哩」字標 | 暖墨底、白字、珊瑚紅口字旁 | 穩重企業 |

## 檔案
- `{id}_icon_{brand|cream}.svg/.png`：方形圖示（品牌色底／奶油底），1024px，圓角透明
- `{id}_ig_{brand|cream}_{110|40|400}.png`：IG 圓形大頭貼實際像素
- `{id}_horizontal.png`：橫式 LOGO（圖示＋哩股哩股＋LIGULIGU）
- `src/marks.py` 符號定義（座標格＋shapely 圓角）；`src/build.py` 一鍵重出；`src/glyph.py` 取字形輪廓
- `fonts/`：Noto Sans TC 500／700／900 woff2（取自 npm `@fontsource/noto-sans-tc@5.3.1`，SIL OFL 1.1，可商用；授權全文 `NotoSansTC_OFL_LICENSE.txt`）
- `ai_review.md`：AI 圖審查紀錄（本輪 AI 額度用盡，沒有 AI 圖）

## 色票
珊瑚紅 #FF5B4A（台灣紅漲）｜陽光黃 #FFC83D｜天藍 #3FA9FF｜薄荷 #19C6A7｜奶油 #FFF6E6｜墨 #232733

## 限制
- 橫式 LOGO 為 PNG（字用字型排版）；若要字轉外框的 SVG，定案後再出。
- 尚未做商標檢索，正式註冊前請另做。
