#!/usr/bin/env bash
# 臨時稽核（2026-11-06，不合併 main）：抓線上 JSON ＋ 官方 openapi，打包成 raw.tgz 帶回分析
set -u
OUT=raw; mkdir -p $OUT/site_gh $OUT/site_cf $OUT/official $OUT/hdr
TZ=Asia/Taipei date '+%F %T %Z' > $OUT/fetched_at.txt
UA="Mozilla/5.0 tw-rotation-audit"
NAMES="meta index_ohlc index_lastday index_intraday updown market_heat groups_today relative_strength rotation sankey_daily themes sparks flow_v3 rrg_lite rrg_members concentration inst_market inst_today inst_streak trust_streak market_fut fut_oi retail_ratio futures industry_map groups_detail group_valuation fundamental stocks candidates etf etf_series etf_holdings etf_freq earnings seasonality seasonality_v3 ma_breadth news_head intl explore tape_codes digest datagw_index broker_views delivery stock/2330 stock/2317 stock/2454 stock/3231 stock/6669"
get() { # $1=url $2=out
  code=$(curl -sS -L -A "$UA" --compressed --max-time 90 -D "$OUT/hdr/$(echo $2 | tr '/' '_').hdr" -o "$2" -w '%{http_code}' "$1" 2>>$OUT/curl_err.txt)
  echo "$code $1" >> $OUT/status.txt
}
for n in $NAMES; do
  f=$(echo $n | tr '/' '_')
  get "https://miaozike.github.io/tw-rotation/data/$n.json?t=$(date +%s)" "$OUT/site_gh/$f.json"
  get "https://liguligu-puipui.com/data/$n.json?t=$(date +%s)" "$OUT/site_cf/$f.json"
done
get "https://miaozike.github.io/tw-rotation/tw_holidays.json" "$OUT/site_gh/tw_holidays.json"
get "https://miaozike.github.io/tw-rotation/earnings_seed.json" "$OUT/site_gh/earnings_seed.json"
get "https://liguligu-puipui.com/" "$OUT/site_cf/index.html"
# 官方：證交所 openapi（白名單內）
get "https://openapi.twse.com.tw/v1/swagger.json" "$OUT/official/twse_swagger.json"
for p in exchangeReport/STOCK_DAY_ALL exchangeReport/MI_INDEX exchangeReport/FMTQIK exchangeReport/MI_MARGN exchangeReport/BWIBBU_ALL fund/BFI82U fund/T86 fund/TWT38U fund/TWT43U fund/TWT44U exchangeReport/MI_INDEX20 exchangeReport/TWTASU exchangeReport/MI_5MINS_HIST; do
  get "https://openapi.twse.com.tw/v1/$p" "$OUT/official/twse_$(echo $p | tr '/' '_').json"
done
# 櫃買 openapi
get "https://www.tpex.org.tw/openapi/swagger.json" "$OUT/official/tpex_swagger.json"
for p in tpex_mainboard_daily_close_quotes tpex_mainboard_margin_balance tpex_3insti_daily_trading tpex_index tpex_mainboard_highlight tpex_3insti_trading_summary tpex_daily_market_value; do
  get "https://www.tpex.org.tw/openapi/v1/$p" "$OUT/official/tpex_$p.json"
done
# 期交所 openapi
get "https://openapi.taifex.com.tw/swagger.json" "$OUT/official/taifex_swagger.json"
for p in MarketDataOfMajorInstitutionalTradersDetailsOfFuturesContractsBytheDate MarketDataOfMajorInstitutionalTradersGeneralBytheDate DailyMarketReportFut; do
  get "https://openapi.taifex.com.tw/v1/$p" "$OUT/official/taifex_$p.json"
done
