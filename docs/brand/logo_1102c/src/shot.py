import sys
from playwright.sync_api import sync_playwright
src,out,w,h=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=__import__("glob").glob("/opt/pw-browsers/chromium_headless_shell-1243/*/chrome-headless-shell")[0]); pg=b.new_page(viewport={'width':w,'height':h}); pg.goto('file://'+src); pg.wait_for_timeout(500)
    pg.screenshot(path=out,full_page=True); b.close()
