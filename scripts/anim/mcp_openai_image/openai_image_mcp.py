"""比比動畫用的 OpenAI 產圖 MCP 伺服器（本機 stdio）。

給「本機的 Claude Code」呼叫：產圖、依參考圖改圖、依參考圖批次產生 12 格關鍵影格、合成 GIF／WebP、做接觸表。
⚠ 金鑰只從環境變數 OPENAI_API_KEY 讀，不寫進任何檔案、不印出來、不進 repo。
⚠ stdio 伺服器的標準輸出是通訊管道，所以這支程式絕不 print 到 stdout，記錄一律寫 stderr。

環境變數：
  OPENAI_API_KEY            必填
  OPENAI_IMAGE_MODEL        選填，預設 gpt-image-1
  OPENAI_IMAGE_OUTPUT_DIR   選填，預設 ~/openai-image-outputs
"""
from __future__ import annotations

import base64
import io
import math
import os
import sys
import time
from pathlib import Path
from typing import Optional

try:                                   # mcp 1.x
    from mcp.server.fastmcp import FastMCP
except ImportError:                    # mcp 2.x 把 FastMCP 改名成 MCPServer
    from mcp.server.mcpserver import MCPServer as FastMCP
from PIL import Image

mcp = FastMCP("openai-image")

DEFAULT_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
VALID_SIZES = {"1024x1024", "1536x1024", "1024x1536", "auto"}
VALID_QUALITY = {"low", "medium", "high", "auto"}


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _client():
    from openai import OpenAI
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("沒有讀到 OPENAI_API_KEY。請在 claude mcp add 時用 --env OPENAI_API_KEY=... 傳入。")
    return OpenAI(api_key=key)


def _out_dir(output_dir: Optional[str]) -> Path:
    base = output_dir or os.environ.get("OPENAI_IMAGE_OUTPUT_DIR") or str(Path.home() / "openai-image-outputs")
    p = Path(base).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _check(size: str, quality: str) -> None:
    if size not in VALID_SIZES:
        raise ValueError(f"size 只能是 {sorted(VALID_SIZES)}，收到 {size!r}（gpt-image 系列不支援 2048x2048）")
    if quality not in VALID_QUALITY:
        raise ValueError(f"quality 只能是 {sorted(VALID_QUALITY)}，收到 {quality!r}")


def _retry(fn, tries: int = 3):
    """網路或限流錯誤重試（2、4 秒）；其他錯誤（額度、參數）直接丟出去讓使用者看到。"""
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            name = type(e).__name__
            if "insufficient_quota" in str(e) or "credit_balance" in str(e):
                raise RuntimeError("OpenAI 帳號沒有可用額度（insufficient_quota）。請到 platform.openai.com 的 Billing 儲值後再試。") from e
            if name in ("RateLimitError", "APIConnectionError", "APITimeoutError", "InternalServerError") and i < tries - 1:
                last = e
                _log(f"{name}，{2 ** (i + 1)} 秒後重試")
                time.sleep(2 ** (i + 1))
                continue
            raise
    raise last  # pragma: no cover


def _save_b64(b64: str, path: Path) -> str:
    path.write_bytes(base64.b64decode(b64))
    return str(path)


def _fmt_ext(name: str) -> str:
    ext = Path(name).suffix.lower().lstrip(".")
    return ext if ext in ("png", "webp", "jpeg") else "png"


def _generate(prompt, path: Path, size, quality, transparent, model) -> str:
    _check(size, quality)
    kw = dict(model=model, prompt=prompt, size=size, quality=quality, n=1, output_format=_fmt_ext(path.name))
    if transparent:
        kw["background"] = "transparent"
    r = _retry(lambda: _client().images.generate(**kw))
    return _save_b64(r.data[0].b64_json, path)


def _edit(ref_paths, prompt, path: Path, size, quality, transparent, model, input_fidelity) -> str:
    _check(size, quality)
    for rp in ref_paths:
        if not Path(rp).is_file():
            raise FileNotFoundError(f"找不到參考圖：{rp}")

    def call(with_fidelity: bool):
        files = [open(rp, "rb") for rp in ref_paths]
        try:
            kw = dict(model=model, image=files if len(files) > 1 else files[0], prompt=prompt,
                      size=size, quality=quality, n=1, output_format=_fmt_ext(path.name))
            if transparent:
                kw["background"] = "transparent"
            if with_fidelity and input_fidelity and "mini" not in model:
                kw["input_fidelity"] = input_fidelity
            return _client().images.edit(**kw)
        finally:
            for f in files:
                f.close()

    try:
        r = _retry(lambda: call(True))
    except Exception as e:  # noqa: BLE001
        if "input_fidelity" in str(e):
            r = _retry(lambda: call(False))
        else:
            raise
    return _save_b64(r.data[0].b64_json, path)


@mcp.tool()
def generate_image(prompt: str, filename: str = "generated_image.png", output_dir: str = "",
                   size: str = "1024x1024", quality: str = "medium", transparent: bool = False,
                   model: str = "") -> str:
    """用文字產生一張圖並存到本機，回傳檔案路徑。size：1024x1024、1536x1024、1024x1536、auto。
    transparent=True 會要求透明背景（輸出 png 或 webp）。"""
    path = _out_dir(output_dir or None) / filename
    return _generate(prompt, path, size, quality, transparent, model or DEFAULT_MODEL)


@mcp.tool()
def edit_image_from_reference(reference_paths: list[str], prompt: str, filename: str = "edited_image.png",
                              output_dir: str = "", size: str = "1024x1024", quality: str = "high",
                              transparent: bool = False, input_fidelity: str = "high", model: str = "") -> str:
    """依一張或多張參考圖改圖或延伸創作（角色造型要維持一致時用這個），回傳檔案路徑。
    input_fidelity=high 會盡量保留參考圖的臉、造型與細節。"""
    path = _out_dir(output_dir or None) / filename
    return _edit(reference_paths, prompt, path, size, quality, transparent, model or DEFAULT_MODEL, input_fidelity)


@mcp.tool()
def generate_frames_from_reference(reference_path: str, frame_prompts: list[str], base_prompt: str = "",
                                   output_dir: str = "", prefix: str = "frame", size: str = "1024x1024",
                                   quality: str = "high", transparent: bool = True,
                                   extra_reference_paths: list[str] | None = None, skip_existing: bool = True,
                                   model: str = "") -> list[str]:
    """依同一張角色參考圖，一格一格產生關鍵影格（例如 12 格分鏡），回傳每格路徑。
    frame_prompts 每個元素描述一格的姿勢與表情；base_prompt 放所有格共用的規則（角色造型不可改、同一個視角與比例…）。
    檔名是 prefix_01.png、prefix_02.png…；skip_existing=True 時已存在的格會跳過，所以中斷後再叫一次就能接著做。"""
    if not frame_prompts:
        raise ValueError("frame_prompts 不能是空的")
    mdl = model or DEFAULT_MODEL
    out = _out_dir(output_dir or None)
    refs = [reference_path] + list(extra_reference_paths or [])
    paths: list[str] = []
    for i, fp in enumerate(frame_prompts, 1):
        p = out / f"{prefix}_{i:02d}.png"
        if skip_existing and p.is_file() and p.stat().st_size > 0:
            _log(f"第 {i} 格已存在，跳過")
            paths.append(str(p))
            continue
        full = (base_prompt.strip() + "\n" if base_prompt.strip() else "") + f"第 {i}/{len(frame_prompts)} 格：{fp}"
        _log(f"產生第 {i}/{len(frame_prompts)} 格")
        paths.append(_edit(refs, full, p, size, quality, transparent, mdl, "high"))
    return paths


def _load_frames(frame_paths: list[str], size: int | None) -> list[Image.Image]:
    frames = []
    for fp in frame_paths:
        if not Path(fp).is_file():
            raise FileNotFoundError(f"找不到影格：{fp}")
        im = Image.open(fp).convert("RGBA")
        if size:
            im = im.resize((size, size), Image.LANCZOS) if im.width == im.height else im.resize(
                (size, max(1, round(im.height * size / im.width))), Image.LANCZOS)
        frames.append(im)
    if not frames:
        raise ValueError("frame_paths 不能是空的")
    return frames


@mcp.tool()
def make_gif_from_frames(frame_paths: list[str], output_path: str, duration_ms: int = 80, loop: int = 0,
                         size: int = 0, also_webp: bool = True) -> list[str]:
    """把影格（依清單順序）合成動態 GIF，並可同時輸出動態 WebP（保留完整半透明，網頁用 WebP 較好）。
    size>0 會把寬縮到該值（LANCZOS）；duration_ms 每格毫秒；loop=0 無限循環。回傳輸出檔案路徑清單。"""
    frames = _load_frames(frame_paths, size or None)
    out = Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    gif_path = out if out.suffix.lower() == ".gif" else out.with_suffix(".gif")
    pal = []
    for im in frames:
        a = im.getchannel("A")
        p = im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
        mask = a.point(lambda v: 255 if v < 128 else 0)
        p.paste(255, mask)           # 索引 255 保留給透明
        p.info["transparency"] = 255
        pal.append(p)
    pal[0].save(gif_path, save_all=True, append_images=pal[1:], duration=duration_ms, loop=loop,
                disposal=2, transparency=255, optimize=False)
    results = [str(gif_path)]
    if also_webp:
        wp = gif_path.with_suffix(".webp")
        frames[0].save(wp, save_all=True, append_images=frames[1:], duration=duration_ms, loop=loop,
                       lossless=False, quality=90, method=6)
        results.append(str(wp))
    return results


@mcp.tool()
def make_contact_sheet(frame_paths: list[str], output_path: str, columns: int = 6, cell: int = 256,
                       background: str = "#fdf6ec") -> str:
    """把影格排成一張總覽圖（含格號），給人逐格檢查用。background 可填 #rrggbb。回傳路徑。"""
    from PIL import ImageColor, ImageDraw
    frames = _load_frames(frame_paths, None)
    cols = max(1, min(columns, len(frames)))
    rows = math.ceil(len(frames) / cols)
    bg = ImageColor.getrgb(background)
    sheet = Image.new("RGB", (cols * cell, rows * cell), bg)
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(frames):
        s = min(cell / im.width, cell / im.height)
        t = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
        x, y = (i % cols) * cell, (i // cols) * cell
        sheet.paste(t, (x + (cell - t.width) // 2, y + (cell - t.height) // 2), t)
        d.text((x + 6, y + 4), f"{i + 1:02d}", fill=(90, 90, 100))
    out = Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return str(out)


if __name__ == "__main__":
    mcp.run()
