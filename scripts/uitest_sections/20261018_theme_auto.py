# 驗收段落「主題自動切換1018」—— 預設淺色、00:00～04:59 深色、手動只算到下一個切換點（DECISIONS #360）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、CONSENT_PRESET… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# Andy 10-18 原話：「幫我將頁面Default 為 亮色 晚上12:00-05:00 為黑色 網頁手機版都是」。
# 其他段落一律被 THEME_PIN 釘在舊行為（_uitest.py），這一段刻意用 Browser._tw_orig_new_context（完全沒包過的原版）＋
# Playwright 假時鐘（時區 Asia/Taipei），1440 桌機與 390 手機各走一遍：
#   ① 10:00 淺、00:30 深、04:59 深、05:00 淺；每一次都在 DOMContentLoaded 量 data-theme，
#      而且從頁面第一行開始記錄 data-theme 的每一次變化 —— 只准出現一個值（＝沒有先閃另一個顏色）
#   ② 23:59 開著不動 → 時間走到 00:00 → 不重新整理就變深色（window 上的記號還在＝沒 reload）
#   ③ 01:00 手指按 ☀／🌙 換淺色 → 重新整理仍是淺色（tw.themeOv.until＝05:00）→ 走到 05:00 → 手動到期、回自動（淺）
#   ④ 14:00 按成深色 → 走到 00:00 → 仍深（已是自動，tw.themeOv 清掉）→ 走到 05:00 → 淺
#   ⑤ 舊版存過 tw.theme=dark（沒有 tw.themeMig）→ 10:00 開頁是淺色、tw.theme 被清、只遷移一次
# 設 TW_THEMEAUTO_SHOTS=<資料夾> 時存 10:00 與 01:00 的截圖（themeauto_<寬>_<時>.png）。

import datetime as _dt1018
import os as _os1018

T1018 = "主題自動切換1018"
_TZ1018 = _dt1018.timezone(_dt1018.timedelta(hours=8))

# 從頁面第一行開始記 data-theme 的每一次變化：MutationObserver 掛在 <html> 上（init script 比 <head> 裡的任何 script 都早跑）
_TH_REC = """(() => { window.__thSeq = []; window.__thDCL = null;
  // init script 跑的時候 <html> 還沒建出來 → 觀察整份 document（subtree）；還沒設屬性的那一刻（null）頁面還沒畫任何東西，不算
  const push = () => { const d = document.documentElement; const v = d && d.getAttribute('data-theme'); if (v && window.__thSeq[window.__thSeq.length - 1] !== v) window.__thSeq.push(v); };
  new MutationObserver(push).observe(document, { attributes: true, attributeFilter: ['data-theme'], subtree: true, childList: true });
  document.addEventListener('DOMContentLoaded', () => { window.__thDCL = document.documentElement.getAttribute('data-theme'); }); })();"""


def _t1018_open(b, base, mob, hh, mm, ls=None):
    """開一個全新的乾淨瀏覽器（只預寫同意條款），假時鐘停在台北時間今天 hh:mm，開總覽。"""
    raw = getattr(type(b), "_tw_orig_new_context", None) or type(b).new_context
    kw = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True) if mob \
        else dict(viewport={"width": 1440, "height": 1000})
    ctx = raw(b, timezone_id="Asia/Taipei", **kw)
    ctx.add_init_script(CONSENT_PRESET + "try{localStorage.setItem('tw.live.on','0')}catch(e){}")
    if ls:
        ctx.add_init_script("(o => { try { if (!sessionStorage.getItem('__t1018')) { sessionStorage.setItem('__t1018','1');"
                            " for (const k in o) localStorage.setItem(k, o[k]); } } catch (e) {} })(" + __import__("json").dumps(ls) + ")")
    ctx.add_init_script(_TH_REC)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.clock.install(time=_dt1018.datetime(2026, 10, 18, hh, mm, 0, tzinfo=_TZ1018))
    pg.goto(base + "#overview", wait_until="domcontentloaded")
    wait_until(pg, "() => !!(window.App && window.App.theme)", 15000)
    pg.wait_for_timeout(600)
    return ctx, pg, errs


def _t1018_th(pg):
    return pg.evaluate("() => document.documentElement.getAttribute('data-theme')")


def _t1018_jump(pg, hh, mm, ss=20):
    """把假時鐘往前推到今天（或明天，若已過）hh:mm:ss；fast_forward 會觸發這段時間內到期的計時器。"""
    now = pg.evaluate("() => Date.now()")
    t = _dt1018.datetime.fromtimestamp(now / 1000, _TZ1018)
    tgt = t.replace(hour=hh, minute=mm, second=ss, microsecond=0)
    if tgt <= t:
        tgt += _dt1018.timedelta(days=1)
    pg.clock.fast_forward(int((tgt - t).total_seconds() * 1000))
    pg.wait_for_timeout(500)


def _t1018_toggle(pg, mob):
    """手指／滑鼠真的按頁首那顆 ☀／🌙（#themeBtn）；看不到就改按外觀面板裡的「深色｜淺色」（同一條路）。"""
    want = "dark" if _t1018_th(pg) == "light" else "light"
    btn = pg.locator("#themeBtn")
    if btn.count() and btn.is_visible():
        btn.tap() if mob else btn.click()
    else:
        pg.locator("#t4Btn").click()
        pg.locator(f".t4mode button[data-mode='{want}']").click()
    wait_until(pg, f"() => document.documentElement.getAttribute('data-theme') === '{want}'", 5000)
    pg.wait_for_timeout(400)
    return want


def t_theme_auto_1018(b, base):
    shots = _os1018.environ.get("TW_THEMEAUTO_SHOTS")
    for mob in (False, True):
        W = 390 if mob else 1440
        tag = f"[{T1018} {W}]"
        # ① 四個時間點
        for hh, mm, want in ((10, 0, "light"), (0, 30, "dark"), (4, 59, "dark"), (5, 0, "light"), (1, 0, "dark")):
            ctx, pg, errs = _t1018_open(b, base, mob, hh, mm)
            st = pg.evaluate("() => ({ dcl: window.__thDCL, seq: window.__thSeq.slice(), bg: getComputedStyle(document.body).backgroundColor })")
            ok(f"{tag} {hh:02d}:{mm:02d} 開頁＝{want}", _t1018_th(pg) == want, st)
            ok(f"{tag} {hh:02d}:{mm:02d} DOMContentLoaded 時 data-theme 已經是 {want}（不閃）", st["dcl"] == want, st)
            ok(f"{tag} {hh:02d}:{mm:02d} 載入過程 data-theme 只出現過一個值", st["seq"] == [want], st["seq"])
            ok(f"{tag} {hh:02d}:{mm:02d} 沒有 pageerror", not errs, errs[:3])
            if shots and (hh, mm) in ((10, 0), (1, 0)):
                pg.wait_for_timeout(1500)
                pg.screenshot(path=_os1018.path.join(shots, f"themeauto_{W}_{hh:02d}00.png"))
            ctx.close()

        # ② 開著不動跨過午夜
        ctx, pg, errs = _t1018_open(b, base, mob, 23, 59)
        ok(f"{tag} 23:59 淺色", _t1018_th(pg) == "light", _t1018_th(pg))
        pg.evaluate("() => { window.__noReload1018 = 1; }")
        _t1018_jump(pg, 0, 0, 5)
        wait_until(pg, "() => document.documentElement.getAttribute('data-theme') === 'dark'", 4000)
        ok(f"{tag} 走到 00:00 不重新整理就變深色", _t1018_th(pg) == "dark", _t1018_th(pg))
        ok(f"{tag} 跨午夜沒有重新整理（記號還在）", pg.evaluate("() => window.__noReload1018 === 1"))
        ok(f"{tag} 換色後按鈕字跟著換（深色顯示 ☀）", pg.evaluate("() => (document.getElementById('themeBtn')||{}).textContent") == "☀")
        ctx.close()

        # ③ 01:00 手動換淺色 → 撐到 05:00
        ctx, pg, errs = _t1018_open(b, base, mob, 1, 0)
        ok(f"{tag} 01:00 先是深色", _t1018_th(pg) == "dark")
        _t1018_toggle(pg, mob)
        ok(f"{tag} 01:00 按了變淺色", _t1018_th(pg) == "light", _t1018_th(pg))
        ov = pg.evaluate("() => { try { return JSON.parse(localStorage.getItem('tw.themeOv')); } catch (e) { return null; } }")
        exp5 = int(_dt1018.datetime(2026, 10, 18, 5, 0, 0, tzinfo=_TZ1018).timestamp() * 1000)
        ok(f"{tag} 手動選擇存成 {{mode:light, until:05:00}}", bool(ov) and ov.get("mode") == "light" and ov.get("until") == exp5, ov)
        ok(f"{tag} 不再寫舊的永久鍵 tw.theme", pg.evaluate("() => localStorage.getItem('tw.theme')") is None)
        pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => !!(window.App && window.App.theme)", 15000); pg.wait_for_timeout(500)
        ok(f"{tag} 01:00 重新整理後手動淺色仍有效", _t1018_th(pg) == "light", _t1018_th(pg))
        _t1018_jump(pg, 4, 58)
        ok(f"{tag} 04:58 手動淺色還在（深夜也不被自動蓋掉）", _t1018_th(pg) == "light", _t1018_th(pg))
        _t1018_jump(pg, 5, 0, 30)
        ok(f"{tag} 05:00 手動到期 → 回自動（淺）、tw.themeOv 清掉", _t1018_th(pg) == "light"
           and pg.evaluate("() => localStorage.getItem('tw.themeOv')") is None, pg.evaluate("() => localStorage.getItem('tw.themeOv')"))
        ctx.close()

        # ④ 14:00 手動深色 → 00:00 還是深（已是自動）→ 05:00 淺
        ctx, pg, errs = _t1018_open(b, base, mob, 14, 0)
        _t1018_toggle(pg, mob)
        ok(f"{tag} 14:00 按了變深色", _t1018_th(pg) == "dark", _t1018_th(pg))
        _t1018_jump(pg, 23, 50)
        ok(f"{tag} 23:50 手動深色還在", _t1018_th(pg) == "dark", _t1018_th(pg))
        _t1018_jump(pg, 0, 0, 30)
        ok(f"{tag} 00:00 之後仍深色、手動已到期（tw.themeOv 清掉）", _t1018_th(pg) == "dark"
           and pg.evaluate("() => localStorage.getItem('tw.themeOv')") is None, pg.evaluate("() => localStorage.getItem('tw.themeOv')"))
        _t1018_jump(pg, 5, 0, 30)
        ok(f"{tag} 05:00 自動換回淺色", _t1018_th(pg) == "light", _t1018_th(pg))
        # 手動選了跟自動一樣的值＝回到自動（不留一筆沒有意義的覆寫）
        _t1018_toggle(pg, mob); _t1018_toggle(pg, mob)
        ok(f"{tag} 換深再換回淺（＝自動值）→ 不留覆寫", _t1018_th(pg) == "light"
           and pg.evaluate("() => localStorage.getItem('tw.themeOv')") is None)
        ctx.close()

        # ⑤ 舊版永久偏好遷移一次
        ctx, pg, errs = _t1018_open(b, base, mob, 10, 0, ls={"tw.theme": "dark"})
        st = pg.evaluate("() => ({ t: localStorage.getItem('tw.theme'), mig: localStorage.getItem('tw.themeMig'), dcl: window.__thDCL, seq: window.__thSeq.slice() })")
        ok(f"{tag} 舊版存 tw.theme=dark → 10:00 開頁是淺色（新預設生效）", _t1018_th(pg) == "light" and st["dcl"] == "light" and st["seq"] == ["light"], st)
        ok(f"{tag} 舊鍵 tw.theme 清掉、遷移記號 tw.themeMig=1", st["t"] is None and st["mig"] == "1", st)
        _t1018_toggle(pg, mob)
        pg.evaluate("() => localStorage.setItem('tw.theme', 'light')")   # 遷移過後就算又出現舊鍵也不再理它
        pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => !!(window.App && window.App.theme)", 15000); pg.wait_for_timeout(500)
        ok(f"{tag} 遷移只做一次：之後手動選的深色照樣有效", _t1018_th(pg) == "dark", _t1018_th(pg))
        ctx.close()


register(T1018, lambda pg, b, base, code: t_theme_auto_1018(b, base))
