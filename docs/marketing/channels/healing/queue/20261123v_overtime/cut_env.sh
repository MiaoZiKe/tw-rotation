# 2026-11-22 聲音先定（video_logic.md「聲音先定、畫面跟聲音」）：錄音定稿後只裁頭尾＋片頭淡入。
# 換幕停頓＝錄音自然停頓（GAP_OVERRIDE 填原始錄音的實際間隔＋0.09 補償，等於不插不剪）；句內不壓縮（INNER/COMMA/SENT_MAX=9）、不插停頓（PUNCT_INS 預設關）
# ON0：念稿起點放在「直接說」之後的靜音（38.0 秒，37.85～38.26 為靜音），避免把「說」收進片頭
export PRE_LAST=0
export HOLD=1.05
export SCENE_GAP=0.5
export INNER_MAX=9 COMMA_MAX=9 SENT_MAX=9
export ON0=38.0
export GAP_OVERRIDE="s1=0.68,s2=0.78,s3=0.70,s4=0.78,s5=0.69,s6=0.65,s7=0.53"
