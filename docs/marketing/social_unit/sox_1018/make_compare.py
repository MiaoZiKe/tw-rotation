"""並排對照圖：左＝參考圖第 1、2 頁（裁自 Andy 提供的圖組），右＝成品。"""
from PIL import Image, ImageDraw, ImageFont
REF = '/tmp/claude-0/-home-user-tw-rotation/62e04d48-96f5-50bd-bb79-37e8d5cec8ee/images/29.jpg'
D = '/home/user/tw-rotation/docs/marketing/social_unit/sox_1018/'
ref = Image.open(REF)
crops = [ref.crop((0, 0, 238, 300)), ref.crop((243, 0, 481, 300))]
mine = [Image.open(D + 'p01_cover.png'), Image.open(D + 'p02_reasons.png')]
h = 900
f = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 28)
cv = Image.new('RGB', (4 * 720 + 5 * 20, h + 80), (235, 235, 235))
d = ImageDraw.Draw(cv)
x = 20
for i in range(2):
    for lab, im in (('參考圖 %d' % (i + 1), crops[i]), ('成品 %d' % (i + 1), mine[i])):
        w = int(im.width * h / im.height)
        cv.paste(im.resize((w, h), Image.LANCZOS), (x, 60))
        d.text((x, 14), lab, font=f, fill=(30, 30, 30))
        x += w + 20
cv = cv.crop((0, 0, x, h + 80))
cv.save(D + 'compare.png')
print(cv.size)
