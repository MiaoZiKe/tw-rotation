"""談晴說礙（頻道④）貼文 → 精選文章「談晴說礙」隱藏分頁（site/articles/healing/）。

2026-11-15 Andy：「所有頻道都需要這樣」——每篇貼文的內容也要存成網站精選文章裡自己頻道的隱藏分頁（對外不顯示、只有站主看得到，直接連結打得開）。
每篇佇列資料夾 docs/marketing/channels/healing/queue/<資料夾>/ 要有：
  caption.txt（文案全文；第一行＝標題、最後 # 開頭那行＝標籤、「資料來源：」以下＝文案末段出處）
  meta.json（publish_at）、1.jpg～3.jpg（貼文圖）、article.json（slug、date、summary、alts、sources、confidence）
IG／Threads 網址從 state/posted.json 取；還沒發出的寫「排程於…發出後補上公開網址」，發出後再跑一次就會補上。
用法：python -m scripts.healing_article <資料夾名> [<資料夾名>…]     （--all＝佇列裡有 article.json 的全部）
寫入：site/articles/healing/<id>.json、site/articles/healing/index.json、site/articles/healing/img/<id>-<n>.jpg
影片貼文（meta.json "format": "video"，2026-11-15）：放封面（cover.jpg → img/<id>-cover.jpg）＋影片連結
  （正式站 https://liguligu-puipui.com/media/healing/<資料夾>/video.mp4，由 healing_post.py --prepare 同步）＋文案全文；
  沒有 cover.jpg 就只放影片連結與文案。alts 只要一個（封面的替代文字）。
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from scripts.article_publish import publish_channel

ROOT = Path(__file__).resolve().parent.parent
CH = ROOT / "docs/marketing/channels/healing"
IMG = ROOT / "site/articles/healing/img"


def build(folder, cfg):
    q = CH / "queue" / folder
    cap = (q / "caption.txt").read_text(encoding="utf-8").strip()
    meta = json.loads((q / "meta.json").read_text(encoding="utf-8"))
    lines = [l.strip() for l in cap.splitlines()]
    tags = []
    body = []
    for l in lines:
        if l.startswith("#"):
            tags = [t.lstrip("#") for t in l.split() if t.startswith("#")]
            continue
        body.append(l)
    title = body[0]
    rest = body[1:]
    # 切出「資料來源：」段（來源另放 sources，這裡也保留原文一段，對照用）
    src_txt = []
    if "資料來源：" in rest:
        i = rest.index("資料來源：")
        src_txt = [x for x in rest[i + 1:] if x]
        rest = rest[:i]
    paras = [x for x in rest if x]
    pid = f"{cfg['date']}-healing-{cfg['slug']}"
    if meta.get("format") == "video":
        return build_video(folder, cfg, q, meta, title, paras, tags, pid)
    items = []
    for n in (1, 2, 3):
        src = q / f"{n}.jpg"
        if not src.exists():
            continue
        dst = IMG / f"{pid}-{n}.jpg"
        shutil.copyfile(src, dst)
        items.append({"src": f"articles/healing/img/{dst.name}", "alt": cfg["alts"][n - 1], "cap": f"{n}／3"})
    p = posted.get(folder) or {}
    ig, th = (p.get("ig") or {}).get("link"), (p.get("threads") or {}).get("link")
    # 摘要已在標題下的導讀顯示，這裡不再重複；文案末段的「資料來源：」不重貼，完整出處（含口徑與樣本數）在文末「資料來源」
    blocks = [{"t": "h", "text": "貼文圖（3 張）"}]
    blocks.append({"t": "img", "items": items, "note": "點圖看原尺寸（1080×1350）。圖上每個數字下方有一行出處。"})
    blocks.append({"t": "h", "text": "文案全文"})
    for x in paras:
        blocks.append({"t": "p", "text": x})
    blocks.append({"t": "h", "text": "發布紀錄"})
    if ig or th:
        when = (p.get("at") or "")[:16].replace("T", " ")
        blocks.append({"t": "p", "text": f"已於台北時間 {when} 發布到 Instagram 與 Threads。"})
        blocks.append({"t": "links", "title": "公開網址", "items": [x for x in (
            {"label": "Instagram", "url": ig} if ig else None, {"label": "Threads", "url": th} if th else None) if x]})
    else:
        when = (meta.get("publish_at") or "").replace("T", " ").replace("+08:00", "")
        blocks.append({"t": "p", "text": f"排程於台北時間 {when} 發布到 Instagram 與 Threads；發出後補上公開網址。"})
    post = {"id": pid, "cat": "healing", "title": title, "subtitle": "談晴說礙・IG／Threads 貼文存檔（圖、文案全文、出處）",
            "date": cfg["date"], "updated": cfg["date"], "tags": tags, "summary": cfg["summary"], "reading_min": 2,
            "blocks": blocks, "sources": cfg["sources"], "confidence": cfg["confidence"], "status": "published",
            "social": {"ig": ig, "threads": th, "queue": folder}}
    return post


def _publish_record(folder, meta):
    p = posted.get(folder) or {}
    ig, th = (p.get("ig") or {}).get("link"), (p.get("threads") or {}).get("link")
    blocks = [{"t": "h", "text": "發布紀錄"}]
    if ig or th:
        when = (p.get("at") or "")[:16].replace("T", " ")
        blocks.append({"t": "p", "text": f"已於台北時間 {when} 發布到 Instagram 與 Threads。"})
        blocks.append({"t": "links", "title": "公開網址", "items": [x for x in (
            {"label": "Instagram", "url": ig} if ig else None, {"label": "Threads", "url": th} if th else None) if x]})
    else:
        when = (meta.get("publish_at") or "").replace("T", " ").replace("+08:00", "")
        blocks.append({"t": "p", "text": (f"排程於台北時間 {when} 發布到 Instagram 與 Threads；發出後補上公開網址。" if when
                                          else "還沒排程發布；發出後補上公開網址。")})
    return blocks, ig, th


def build_video(folder, cfg, q, meta, title, paras, tags, pid):
    """影片貼文：影片（文章內直接播放＋下載鈕，mp4 區塊）＋文案全文＋發布紀錄。
    2026-11-16（Andy 11-15「做好的影片都需要放在網站上對應的文章內，並且都具備下載功能」，docs/marketing/channels/video_in_articles.md）：
    site/media/healing/<資料夾>/video.mp4 存在（healing_post.py --prepare 同步）就放 mp4 區塊（poster＝同資料夾 cover.jpg）；
    還沒同步時才退回舊做法（封面圖＋影片連結）。"""
    blocks = [{"t": "h", "text": "影片"}]
    alts = cfg.get("alts") or [title]
    cov = q / "cover.jpg"
    media = ROOT / "site/media/healing" / folder / "video.mp4"
    vurl = f"https://liguligu-puipui.com/media/healing/{folder}/video.mp4" if media.exists() else \
        f"https://raw.githubusercontent.com/MiaoZiKe/tw-rotation/main/docs/marketing/channels/healing/queue/{folder}/video.mp4"
    if media.exists():
        b = {"t": "mp4", "src": f"media/healing/{folder}/video.mp4", "title": title,
             "note": cfg.get("video_note") or "影片 1080×1920（IG Reels／Threads 同一支）；可下載。"}
        if (media.parent / "cover.jpg").exists():
            b["poster"] = f"media/healing/{folder}/cover.jpg"
        blocks.append(b)
    else:
        if cov.exists():
            dst = IMG / f"{pid}-cover.jpg"
            shutil.copyfile(cov, dst)
            blocks.append({"t": "img", "items": [{"src": f"articles/healing/img/{dst.name}", "alt": alts[0], "cap": "影片封面"}],
                           "note": "影片封面（1080×1920）。影片本身請點下面的連結觀看。"})
        if (q / "video.mp4").exists():
            blocks.append({"t": "links", "title": "影片檔", "items": [{"label": "觀看影片（MP4）", "url": vurl}]})
    blocks.append({"t": "h", "text": "文案全文"})
    for x in paras:
        blocks.append({"t": "p", "text": x})
    rec, ig, th = _publish_record(folder, meta)
    blocks += rec
    return {"id": pid, "cat": "healing", "title": title, "subtitle": "談晴說礙・IG Reels／Threads 影片存檔（封面、影片、文案全文、出處）",
            "date": cfg["date"], "updated": cfg["date"], "tags": tags, "summary": cfg["summary"], "reading_min": 2,
            "blocks": blocks, "sources": cfg["sources"], "confidence": cfg["confidence"], "status": "published",
            "social": {"ig": ig, "threads": th, "queue": folder, "format": "video", "video": vurl}}


def main(argv=None) -> int:
    global posted
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("用法：python -m scripts.healing_article <佇列資料夾名>…｜--all")
        return 2
    posted = json.loads((CH / "state/posted.json").read_text(encoding="utf-8"))
    IMG.mkdir(parents=True, exist_ok=True)
    folders = sorted(p.parent.name for p in (CH / "queue").glob("*/article.json")) if args == ["--all"] else sorted(args)
    for folder in folders:      # 舊的先、新的後，index.json 最新的在最前面
        af = CH / "queue" / folder / "article.json"
        if not af.exists():
            print(f"✗ {folder}：沒有 article.json（slug、date、summary、alts、sources、confidence）")
            return 2
        post = build(folder, json.loads(af.read_text(encoding="utf-8")))
        publish_channel(post, "healing")
        print(f"✓ {post['id']}（{'有' if post['social']['ig'] else '還沒有'} IG／Threads 網址）→ https://liguligu-puipui.com/#article/{post['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
