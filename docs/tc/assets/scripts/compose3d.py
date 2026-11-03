from PIL import Image, ImageDraw, ImageFont
B = "/tmp/claude-0/-home-user-tw-rotation/1662701f-8abb-57a6-b66d-4e0b4e90dd73/scratchpad"
F = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 28)
T = {'ic_substrate': 'IC 載板 ABF 增層（3D 視角）', 'air_cooling': '氣冷散熱模組（3D 視角）', 'hbm': 'HBM 堆疊記憶體（3D 視角）'}
for k, t in T.items():
    im = Image.open(f'{B}/raw3d/{k}_3d.png').convert('RGB'); w = 1000; h = round(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    cv = Image.new('RGB', (1080, 1350), '#FFFFFF'); cv.paste(im, (40, (1286 - h) // 2))
    d = ImageDraw.Draw(cv); d.line([(40, 1286), (1040, 1286)], fill='#CFCFCF', width=2)
    d.text((40, 1296), f'{t}　｜　示意圖，非實物比例', font=F, fill='#595959')
    cv.save(f'{B}/tc_assets/diagrams/{k}_3d.png', optimize=True)
