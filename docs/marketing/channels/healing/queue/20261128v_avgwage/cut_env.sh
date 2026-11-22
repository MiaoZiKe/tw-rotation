# 2026-11-22 四道驗證：句中不插停頓（PUNCT_INS 預設關）；換幕停頓 0.75 秒；8 鏡有 7 個換幕，補停頓限 6 處 → s4 之後語意連續只留 0.4 秒
export PRE_LAST=0
export HOLD=1.05
export SCENE_GAP=0.75
export GAP_OVERRIDE="s4=0.4"
