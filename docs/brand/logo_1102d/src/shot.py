import sys
sys.path.insert(0,'/home/user/tw-rotation/docs/brand/logo_1102d/src')
from playwright.sync_api import sync_playwright
OUT='/home/user/tw-rotation/docs/brand/logo_1102d'
def main(html,png,w,h,scale=1):
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path=__import__("glob").glob("/opt/pw-browsers/chromium_headless_shell-1243/*/chrome-headless-shell")[0]); pg=b.new_page(viewport={'width':w,'height':h},device_scale_factor=scale)
        pg.goto('file://'+html); pg.wait_for_timeout(500); pg.screenshot(path=png,full_page=True); b.close()
if __name__=='__main__': main(sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),float(sys.argv[5]) if len(sys.argv)>5 else 1)
