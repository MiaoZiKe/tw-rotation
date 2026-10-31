// Cloudflare Pages「進階模式」Worker：把 liguligu-puipui.com/preview/* 轉到預覽專用的 Pages 專案。
// 2026-10-31 Andy：「給人看的一律是 liguligu-puipui.com」。主站專案 tw-rotation 已逼近 2 萬檔上限，
// 預覽另外放在 tw-rotation-preview 專案，這支只負責轉送（不需要 Zone 的 Workers Routes 權限）。
// 搭配 _routes.json 只攔 /preview/*，其餘網址仍由 Pages 直接吐靜態檔，不經過這支。
const UPSTREAM = 'https://tw-rotation-preview.pages.dev';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/preview')) return env.ASSETS.fetch(request);
    // /preview 與 /preview/<名稱> 補斜線，相對路徑的資源才找得到
    const rest = url.pathname.slice('/preview'.length);
    if (rest === '' || (/^\/[^/]+$/.test(rest) && !rest.includes('.'))) {
      return Response.redirect(url.origin + '/preview' + (rest || '/') + (rest ? '/' : '') + url.search, 308);
    }
    const target = UPSTREAM + rest + url.search;
    const init = { method: request.method, headers: request.headers, redirect: 'manual' };
    const res = await fetch(new Request(target, init));
    const h = new Headers(res.headers);
    const loc = h.get('Location');
    if (loc) {
      const u = new URL(loc, target);
      if (u.origin === UPSTREAM) h.set('Location', url.origin + '/preview' + u.pathname + u.search);
    }
    return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
  },
};
