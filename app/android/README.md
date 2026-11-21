# Android App（TWA）打包設定

> 2026-10-22 新增。整體計畫、費用、時程與風險見 `docs/app_store_plan.md`。

這個資料夾只放**不含任何秘密**的設定：

| 檔案 | 用途 |
|---|---|
| `twa-manifest.json` | Bubblewrap 的設定：套件名稱 `com.liguligu.app`、網域 `liguligu-puipui.com`、圖示、顏色、版號 |
| `.gitignore` | 擋住 `*.keystore`／`*.jks`／`build/`，避免金鑰被誤 commit |

建置由 `.github/workflows/android-twa.yml`（手動觸發）在 GitHub Actions 裡做，Andy 不需要裝任何東西。

## ⚠ 上架前一定要先定的一件事：套件名稱

`com.liguligu.app` 是提案。**第一次上傳到 Play Console 之後就永遠不能改**（App 名稱可以改）。
要改就在第一次跑工作流之前，同時改這三個地方：`twa-manifest.json` 的 `packageId`、
`site/.well-known/assetlinks.json` 的 `package_name`、以及本檔。

## 一、產生上傳金鑰（只做一次，Andy 做或在 Actions 裡做）

金鑰是「證明這個 App 是你發的」的那把鑰匙。**遺失就無法再更新同一個 App**（Play App Signing 可以申請重設上傳金鑰，但很麻煩），
所以產生後要**另外備份到安全的地方**（例如密碼管理器的附件），不要只放在 GitHub Secrets。

有 Java 的電腦上執行（Windows 裝了 Android Studio 就有 `keytool`）：

```
keytool -genkeypair -v -keystore liguligu-upload.keystore -alias liguligu -keyalg RSA -keysize 2048 -validity 10000
```

它會問兩次密碼（keystore 密碼、金鑰密碼，可以設成一樣，至少 6 碼）以及姓名等資料（可以填英文名與 TW）。

## 二、放進 GitHub Secrets

1. 把金鑰轉成 base64（PowerShell）：
   `[Convert]::ToBase64String([IO.File]::ReadAllBytes("liguligu-upload.keystore")) | Set-Clipboard`
2. GitHub repo → Settings → Secrets and variables → Actions → **New repository secret**，新增三個：
   - `ANDROID_KEYSTORE_BASE64`：剛剛複製的那一長串
   - `ANDROID_KEYSTORE_PASSWORD`：keystore 密碼
   - `ANDROID_KEY_PASSWORD`：金鑰密碼
3. 同一頁切到 **Variables** 分頁 → New repository variable：`ANDROID_TWA_ENABLED` ＝ `true`（打開工作流）。

## 三、建置

Actions → 「Android App 打包（TWA，手動）」→ Run workflow → 填 versionCode（第一次 1，之後每次 +1）與 versionName。
跑完在那次 run 的 Artifacts 下載 `app-release-bundle.aab`，上傳到 Play Console 的封閉測試。
log 最後一步會印出**上傳金鑰的 SHA-256**。

## 四、Digital Asset Links（拿掉網址列的關鍵）

TWA 要證明「App 跟網站是同一個人的」，否則 App 頂端會一直顯示網址列（像瀏覽器）。

1. Play Console → 測試與發布 → 設定 → **應用程式完整性** → 複製「應用程式簽署金鑰憑證」的 **SHA-256**。
2. 把它和上一步 log 印出的上傳金鑰 SHA-256，填進 `site/.well-known/assetlinks.json` 取代兩個 `REPLACE_WITH_...`。
3. 推上 main 部署後，確認 <https://liguligu-puipui.com/.well-known/assetlinks.json> 回 200 且是 JSON（不能被轉址）。
   - 部署用的是 `actions/upload-pages-artifact@v3`，**v3 會帶上 `.well-known` 這種點開頭的資料夾**（已讀過該版的 action.yml 確認）。
     ⚠ **將來升到 v4 要加 `include-hidden-files: true`**，否則 `.well-known` 會被丟掉、App 會突然冒出網址列。
   - Actions 部署不跑 Jekyll，`site/.nojekyll` 只是保險。
   - Cloudflare 若開了 Bot Fight Mode／挑戰頁，要對 `/.well-known/*` 放行，否則 Google 的驗證爬蟲會被擋。
