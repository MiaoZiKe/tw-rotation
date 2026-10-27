"""三類事件封面 v2：台股（台積電法說）／總經（FOMC）／ETF（0050）。用法：python render_covers_v2.py <輸出資料夾>"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "event_v2_lib"))
from lib import *
pages = [
 page_cover("台股", "semi", '台積電 Q3<br>每股賺 <span class="yy num">29.43</span> 元', '毛利率回落、第四季財測怎麼說？', '2026/10/15 法說會・公司公布數字整理', "10/15", -520),
 page_cover("總經", "fomc", '聯準會明天凌晨<br><span class="yy num">02:00</span> 公布利率', '9 月升息 1 碼後，這次會怎麼走？', '台灣 10/29（四）02:00 公布・02:30 記者會', "10/28", -250),
 page_cover("ETF", "etf", '買在 0050 最高點<br>含息 <span class="yy num">6.6</span> 年才回本', '最慘賠多少？撐到今天又剩多少？', '2007/10 一次投入 100 萬・歷史回測，非預測', "10/28", -430),
]
if __name__ == "__main__":
    render(pages, sys.argv[1], ["tw.jpg", "macro.jpg", "etf.jpg"])
    sheet(sys.argv[1], ["tw.jpg", "macro.jpg", "etf.jpg"], sys.argv[1] + "/covers_v2.jpg", 3, 480)
