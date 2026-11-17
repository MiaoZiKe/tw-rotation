# 初婚：重切 narration_take.wav 的環境變數（不重送 TTS）。make_video.sh --voice 會 source 本檔。
# TRIM：s4 只取到 69.2 秒（之後是 0.9 秒靜音＋雜訊）；CUTS：s1「結婚？」後 40.95–42.16 的 1.21 秒靜音壓成 0.35 秒。
export TRIM="s4=69.2"
export CUTS="40.95-42.16>0.35"
