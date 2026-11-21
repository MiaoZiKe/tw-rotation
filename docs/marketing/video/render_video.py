"""把 promo.html 逐格算圖 → 合成 MP4（不即時錄影，固定 30fps 時間步進，不掉格）。

用法：
    python docs/marketing/video/render_video.py --fmt v --out promo_9x16_1009.mp4 --audio bgm_1009.wav
    python docs/marketing/video/render_video.py --fmt h --stills 2,7,12,40 --still-dir <資料夾>   # 只抽格看

做法：本機起 HTTP 伺服器（canvas 讀圖要同源才能 toDataURL）→ Playwright 開 promo.html?capture=1 →
每一格呼叫 window.__frame(t) 拿 JPEG → 直接灌進 ffmpeg 的 stdin（image2pipe）→ H.264＋AAC。
"""
from __future__ import annotations

import argparse
import base64
import os
import shutil
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass


def ffmpeg_bin() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg  # type: ignore  # 沒有系統 ffmpeg 時才用

    return imageio_ffmpeg.get_ffmpeg_exe()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fmt", choices=["v", "h"], default="v")
    ap.add_argument("--out", default="")
    ap.add_argument("--audio", default="")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--stills", default="", help="逗號分隔的秒數，只輸出這幾格 PNG")
    ap.add_argument("--still-dir", default=".")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PROMO_PORT", "8899")))
    args = ap.parse_args()

    W, H = (1080, 1920) if args.fmt == "v" else (1920, 1080)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), partial(_Quiet, directory=str(HERE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            br = p.chromium.launch(executable_path=os.environ.get("PW_CHROMIUM") or ("/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").exists() else None))
            pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            pg.goto(f"http://127.0.0.1:{args.port}/promo.html?fmt={args.fmt}&capture=1")
            pg.evaluate("() => window.__ready")
            total = pg.evaluate("() => window.__TOTAL")

            if args.stills:
                out_dir = Path(args.still_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                for s in args.stills.split(","):
                    t = float(s)
                    url = pg.evaluate(f"() => {{ window.__render({t}); return document.getElementById('cv').toDataURL('image/png'); }}")
                    f = out_dir / f"still_{args.fmt}_{t:05.1f}s.png"
                    f.write_bytes(base64.b64decode(url.split(",", 1)[1]))
                    print("抽格", f)
                br.close()
                return

            n = int(round(total * args.fps))
            cmd = [ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
                   "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", str(args.fps), "-i", "-"]
            if args.audio:
                cmd += ["-i", args.audio]
            cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", "3200k", "-bufsize", "6400k",
                    "-pix_fmt", "yuv420p", "-r", str(args.fps), "-movflags", "+faststart"]
            if args.audio:
                cmd += ["-c:a", "aac", "-b:a", "160k", "-shortest"]
            cmd += [args.out]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            for i in range(n):
                t = i / args.fps
                url = pg.evaluate(f"() => window.__frame({t}, 0.93)")
                proc.stdin.write(base64.b64decode(url.split(",", 1)[1]))
                if i % 150 == 0:
                    print(f"第 {i}/{n} 格", flush=True)
            proc.stdin.close()
            proc.wait()
            br.close()
            print("完成", args.out, "退出碼", proc.returncode)
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
