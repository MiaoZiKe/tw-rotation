"""CPI 貼文逐張產圖（gpt-image）。用法：python3 gen.py <編號> [model] [quality]。金鑰由代理附上。"""
import os, sys, json
os.environ.setdefault("OPENAI_API_KEY", "proxy-injected")
sys.path.insert(0, "/home/user/tw-rotation/scripts/anim/mcp_openai_image")
import openai_image_mcp as m

HERE = "/home/user/tw-rotation/docs/marketing/post_cpi_1014"
STYLE = """IG 貼文輪播圖，正方形。風格：手繪可愛插畫資訊圖，奶油米色底、粗圓潤深咖啡描邊、粉橘黃綠藍的柔和色塊、圓角卡片、星星與小閃光點綴，繁體中文大標題用粗圓體，版面滿而整齊，跟第二張參考圖（產業小教室）同一種風格。
吉祥物「比比」：白色毛茸茸圓滾滾的天竺鼠，粉橘耳朵、黑色圓點眼睛、粉色舌頭、桃粉腮紅，造型必須跟第一張參考圖（bibi_default）一模一樣。比比是四腳動物：沒有手臂、不要舉手、不要拿東西、不要站立；可以用「從卡片邊緣探出頭」「四腳坐在地上」「用身體和表情表達」，想指東西就用對話泡泡或箭頭。
所有文字都必須是正確的繁體中文，不能有亂碼或錯字，不要出現任何網址、Email、浮水印。畫面所有元素不可互相重疊遮住文字。"""

SLIDES = json.load(open(f"{HERE}/slides.json", encoding="utf-8"))

if __name__ == "__main__":
    import time; T0 = time.time()
    i = int(sys.argv[1]); model = sys.argv[2] if len(sys.argv) > 2 else "gpt-image-2"
    quality = sys.argv[3] if len(sys.argv) > 3 else "medium"
    s = SLIDES[i - 1]
    prompt = STYLE + "\n\n【這一張的內容，文字照抄，不要改字】\n" + s["prompt"] + "\n\n【比比主持規則】比比要夠大（佔畫面約五分之一），是這張圖的主持人，要有清楚的表情、情境、動作、道具與互動，並有一個第一人稱對話泡泡跟觀眾說話。\n" + s["bibi"]
    nref = int(os.environ.get("NREF", "3")); fid = os.environ.get("FID", "high")
    refs = [f"{HERE}/refs/bibi_default.png", f"{HERE}/refs/style_infographic.png", f"{HERE}/refs/style_cover.png"][:nref]
    out = m._edit(refs,
                  prompt, __import__("pathlib").Path(f"{HERE}/raw/slide_{i:02d}_{model}.png"), "1024x1024", quality, False, model, fid)
    print(out)
    import time; print("耗時", round(time.time()-T0,1), "秒")
