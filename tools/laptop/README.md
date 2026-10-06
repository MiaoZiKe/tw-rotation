# 筆電輔助：監控＋每日備份（Windows）

用一台空著的 Windows 筆電做兩件事，**不對外提供任何服務**（不開埠、不當伺服器）：

| 排程 | 多久一次 | 做什麼 |
|---|---|---|
| `tw-ops 監控` | 每 5 分鐘 | 檢查正式站首頁、網站版號、會員 Worker 的 `/health`、每日資料管線有沒有超過 26 小時沒更新 |
| `tw-ops 每日備份` | 每天 22:00 | 把整個 repo（含 `data/` 資料湖的完整歷史）拉到筆電，保留最近 14 天的快照 |

通知規則：同一項**連續失敗 2 次**（約 10 分鐘）才通知；通知過之後不會每 5 分鐘一直寄，6 小時還沒好才再提醒一次；**恢復時通知一次**。

全程約 15 分鐘。只用 Windows 內建的 PowerShell 與 git，不裝 Python。**沒有任何密碼會寫進檔案**：Gmail 密碼存在 Windows 的「憑證管理員」。

---

## 第 1 步：下載這個資料夾（3 分鐘）

1. 筆電要先有 git。開「開始」選單 → 輸入 `PowerShell` → 打開，輸入 `git --version`。
   出現版號就有；出現「無法辨識」就到 <https://git-scm.com/download/win> 下載安裝（一路按「下一步」），裝完**關掉再重開** PowerShell。
2. 在 PowerShell 輸入（一行一行貼）：
   ```powershell
   cd $env:USERPROFILE
   git clone --depth 1 --filter=blob:none --sparse https://github.com/MiaoZiKe/tw-rotation.git tw-tools
   cd tw-tools
   git sparse-checkout set tools/laptop
   cd tools\laptop
   ```
   這樣只會下載 `tools/laptop` 這個資料夾，不會把幾百 MB 的資料湖一起抓下來。

## 第 2 步：安裝（2 分鐘）

在同一個 PowerShell 視窗輸入（把信箱換成你要收通知的信箱）：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -GmailTo 你的信箱@gmail.com
```

- 不想收信、只要桌面通知：把 `-GmailTo ...` 拿掉。
- 想推到手機（二選一或都要）：加上 `-NtfyTopic 一串只有你知道的名字`，例如 `-NtfyTopic tw-andy-8f3k2q`，再看第 4 步。
- 備份預設放 `D:\tw-backup`；沒有 D 槽就放 `C:\Users\你\tw-backup`。要指定就加 `-BackupRoot E:\備份`。

看到綠色的「安裝完成」就好了。腳本會被複製到 `%LOCALAPPDATA%\tw-ops`，所以 `tw-tools` 資料夾之後刪掉也沒關係。

## 第 3 步：設定 Gmail 應用程式密碼（5 分鐘，只有要寄信才需要）

Gmail 不讓程式用你的登入密碼寄信，要另外產生一組「應用程式密碼」：

1. 打開 <https://myaccount.google.com/security>，確認「兩步驟驗證」是**開啟**的（沒開的話要先開，否則下一步看不到）。
2. 打開 <https://myaccount.google.com/apppasswords>，名稱輸入 `tw-ops`，按「建立」。
3. 畫面會出現 16 個英文字母（四組四個）。**先不要關掉**。
4. 回到 PowerShell，輸入（把地址換成你的 Gmail）：
   ```powershell
   cmdkey /generic:tw-ops-gmail /user:你的信箱@gmail.com /pass
   ```
   它會問密碼，把那 16 個字母貼上（空格可以不要），按 Enter。
   這組密碼只存在 Windows 憑證管理員（控制台 → 憑證管理員 → Windows 認證 → `tw-ops-gmail`），不會出現在任何檔案裡。
5. 寄件人就是這個 Gmail；收件人是第 2 步的 `-GmailTo`（可以是同一個信箱）。

## 第 4 步（選用）：推播到手機用 ntfy

1. 手機安裝 **ntfy** App（iPhone 在 App Store、Android 在 Play 商店，免費）。
2. 打開 App → 「+」訂閱 → 主題名稱輸入第 2 步的 `-NtfyTopic` 那串名字。
3. ⚠ ntfy.sh 的主題是**公開的**：任何人知道名字都能看到訊息。所以名字要取得像密碼一樣難猜。訊息內容只有「哪一項壞了」，不含任何帳號資料。

沒有在第 2 步加的話，可以之後再跑一次 `install.ps1 -NtfyTopic 名字`（舊的 Gmail 設定會保留）。

## 第 5 步：確認排程有在跑（2 分鐘）

1. 先手動跑一次監控，看四項是不是都 OK：
   ```powershell
   powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\tw-ops\monitor.ps1" -Once
   ```
   應該看到 `site：OK`、`build：OK`、`account：OK`、`pipeline：OK`。
2. 開「開始」→ 輸入 `工作排程器` → 打開 → 左邊點「工作排程器程式庫」，找到 `tw-ops 監控` 和 `tw-ops 每日備份`。
   點一下，下方「上次執行時間」「上次執行結果」應該是「作業已順利完成 (0x0)」。監控每 5 分鐘會更新一次。
3. 想馬上跑一次備份：在 `tw-ops 每日備份` 上按右鍵 → 「執行」。第一次要把整個資料湖抓下來，**會跑比較久**（幾分鐘到幾十分鐘，看網路）。
4. 紀錄檔：`%LOCALAPPDATA%\tw-ops\ops.log`（在檔案總管網址列貼上就能打開），每一次檢查、每一封通知都記在裡面。

## 第 6 步：手動測試一次通知（1 分鐘）

```powershell
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\tw-ops\test-notify.ps1"
```

右下角會跳出桌面通知、信箱會收到一封「[台股儀表板監控] 測試通知」、有設 ntfy 的話手機會響。
畫面最後一行會寫「已送出：桌面、Gmail、ntfy」—— 少了哪一個，就看 `ops.log` 最後幾行寫了什麼原因。

---

## 移除

```powershell
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\tw-ops\uninstall.ps1"
```

只移除兩個排程。加 `-Purge` 會連設定檔、紀錄檔、Gmail 憑證一起刪。**備份資料夾不會被刪**。

## 備份怎麼還原

備份是一份 git 倉庫：`D:\tw-backup\repo.git`。

- 拿最新版：`git clone D:\tw-backup\repo.git 還原資料夾`
- 拿某一天的：先看有哪些天 `git -C D:\tw-backup\repo.git for-each-ref refs/snapshots`，
  再 `git clone D:\tw-backup\repo.git 還原資料夾`，進去後 `git checkout <快照的 commit 編號>`。
- 每天的快照記的是「那天 22:00 GitHub 上每一條分支指到哪裡」。就算之後 GitHub 上的歷史被覆寫或刪掉，筆電這份 14 天內都還在。
  快照共用同一份檔案，14 份不會佔 14 倍空間（大約就是整個 repo 的大小，加上每天新增的資料）。

## 已知限制與缺口

1. **會員資料沒有備份。** 會員帳號、自選清單、權限設定存在 Cloudflare 的 Durable Object 裡，會員 Worker 目前**沒有「管理者匯出」API**。
   這次刻意不為了備份去改 Worker（改 Worker 是會員系統的高風險改動），先列為待辦：要做的話是新增一支 `/v1/admin/export`（管理者權杖才能叫），再讓 `backup.ps1` 每天叫一次存成 JSON。
2. **筆電要開著、而且有人登入**，排程才會跑（為了不需要系統管理員權限，用的是「只有使用者登入時才執行」）。闔上螢幕進入睡眠就不會檢查；醒來後會補跑一次。
3. **國定假日會誤報一次**「每日資料管線」：週末有放寬到 74 小時，但連假（例如春節）沒有交易日資料，會被當成太久沒更新。看到時確認是不是放假即可。
4. 監控從筆電看出去，**筆電自己的網路斷了也會報「首頁打不開」**。連續好幾項同時失敗時，先看筆電有沒有網路。
5. 時區：備份用的是筆電的時間 22:00。筆電時區不是台北時，安裝時會提醒。
