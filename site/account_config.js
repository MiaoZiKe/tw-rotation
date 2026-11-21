/* 會員登入／使用統計的設定（DECISIONS #270、docs/login_setup.md）
   ★ repo 裡這個檔永遠是空的（api: ''）＝功能關閉。部署時 .github/workflows/pages.yml 依 repo Secret ACCOUNT_API_URL
     覆寫這個檔（只寫進部署產物，不進版控）。所以不要在這裡手動填網址。
   為什麼是 .js 而不是 data/account.json：沒設定時 JSON 會 404，每一頁的主控台都多一行紅字（_preview 也會抓），
   而且 stamp_assets.py 會給 .js 加版本戳，換設定後重新部署一定換得掉（跟 legal_config.js 同一個理由）。*/
window.TW_ACCOUNT = { api: '' };
