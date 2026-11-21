import os, sys, time
os.environ.setdefault("OPENAI_API_KEY","proxy-injected")
sys.path.insert(0,"/home/user/tw-rotation/scripts/anim/mcp_openai_image")
import openai_image_mcp as m
from pathlib import Path
T=time.time()
H="/home/user/tw-rotation/docs/marketing/post_cpi_1014"
p="""手繪可愛 IG 資訊圖封面，正方形，奶油底、粗圓潤深咖啡描邊。吉祥物比比（參考圖那隻白色毛茸茸天竺鼠，四腳、沒有手）從一個藍色購物籃邊緣探出頭，籃子裡有牛奶、雞蛋、蘋果。
大標題用粗圓體繁體中文，只寫這兩行：
「CPI 是什麼？」
「為什麼大家都在等它？」
右上角小字「1 / 9」。左側一個對話泡泡寫「物價漲了嗎？」。"""
out=m._edit([f"{H}/refs/bibi_default.png"],p,Path(f"{H}/raw/short_test.png"),"1024x1024","medium",False,"gpt-image-2","")
print(out,"耗時",round(time.time()-T,1))
