# 共用函式：設定檔、狀態檔、通知（桌面／Gmail／ntfy）。由 monitor.ps1、backup.ps1、test-notify.ps1 載入。
# 規矩：這裡不放任何密碼或金鑰。Gmail 應用程式密碼只存在 Windows 憑證管理員（目標名稱 tw-ops-gmail）。
$ErrorActionPreference = 'Stop'
$script:OpsDir = Join-Path $env:LOCALAPPDATA 'tw-ops'
$script:ConfigPath = Join-Path $script:OpsDir 'config.json'
$script:StatePath = Join-Path $script:OpsDir 'state.json'
$script:LogPath = Join-Path $script:OpsDir 'ops.log'
$script:CredTarget = 'tw-ops-gmail'

function Write-OpsLog([string]$msg) {
    $line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $msg
    Add-Content -Path $script:LogPath -Value $line -Encoding UTF8
    # 紀錄檔超過 2 MB 就留後半
    if ((Get-Item $script:LogPath).Length -gt 2MB) {
        $keep = Get-Content $script:LogPath -Encoding UTF8 | Select-Object -Last 5000
        Set-Content -Path $script:LogPath -Value $keep -Encoding UTF8
    }
}

function Get-OpsConfig {
    if (-not (Test-Path $script:ConfigPath)) { throw ('找不到設定檔 ' + $script:ConfigPath + '，請先執行 install.ps1') }
    return Get-Content $script:ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-OpsState {
    if (Test-Path $script:StatePath) {
        try { return Get-Content $script:StatePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }
    }
    return [pscustomobject]@{}
}

function Save-OpsState($state) {
    $state | ConvertTo-Json -Depth 5 | Set-Content -Path $script:StatePath -Encoding UTF8
}

# ---------------------------------------------------------------- 讀憑證管理員（Windows 內建 API，不需要裝模組）
$credSrc = @'
using System;
using System.Runtime.InteropServices;
public static class TwCred {
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  struct CREDENTIAL { public int Flags; public int Type; public string TargetName; public string Comment;
    public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten; public int CredentialBlobSize; public IntPtr CredentialBlob;
    public int Persist; public int AttributeCount; public IntPtr Attributes; public string TargetAlias; public string UserName; }
  [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
  static extern bool CredRead(string target, int type, int flags, out IntPtr cred);
  [DllImport("advapi32.dll")] static extern void CredFree(IntPtr cred);
  public static string[] Read(string target) {
    IntPtr p; if (!CredRead(target, 1, 0, out p)) return null;
    try { var c = (CREDENTIAL)Marshal.PtrToStructure(p, typeof(CREDENTIAL));
      string pw = c.CredentialBlobSize > 0 ? Marshal.PtrToStringUni(c.CredentialBlob, c.CredentialBlobSize / 2) : "";
      return new string[] { c.UserName, pw }; }
    finally { CredFree(p); }
  }
}
'@
if (-not ('TwCred' -as [type])) { Add-Type -TypeDefinition $credSrc -Language CSharp }

function Get-GmailCredential {
    $r = [TwCred]::Read($script:CredTarget)
    if ($null -eq $r) { return $null }
    $sec = ConvertTo-SecureString $r[1] -AsPlainText -Force
    return New-Object System.Management.Automation.PSCredential($r[0], $sec)
}

# ---------------------------------------------------------------- 通知
function Send-DesktopNotice([string]$title, [string]$body) {
    try {
        Add-Type -AssemblyName System.Windows.Forms, System.Drawing
        $n = New-Object System.Windows.Forms.NotifyIcon
        $n.Icon = [System.Drawing.SystemIcons]::Warning
        $n.Visible = $true
        $n.ShowBalloonTip(15000, $title, $body, [System.Windows.Forms.ToolTipIcon]::Warning)
        Start-Sleep -Seconds 16
        $n.Dispose()
        return $true
    } catch { Write-OpsLog ('桌面通知失敗：' + $_.Exception.Message); return $false }
}

function Send-GmailNotice([string]$title, [string]$body) {
    $cfg = Get-OpsConfig
    if (-not $cfg.gmail_to) { return $false }
    $cred = Get-GmailCredential
    if ($null -eq $cred) { Write-OpsLog 'Gmail：憑證管理員裡沒有 tw-ops-gmail，略過'; return $false }
    try {
        $mail = New-Object System.Net.Mail.MailMessage
        $mail.From = $cred.UserName
        $mail.To.Add([string]$cfg.gmail_to)
        $mail.Subject = '[台股儀表板監控] ' + $title
        $mail.Body = $body + "`r`n`r`n" + '（這封信由筆電上的 tw-ops 監控寄出）'
        $mail.SubjectEncoding = [System.Text.Encoding]::UTF8
        $mail.BodyEncoding = [System.Text.Encoding]::UTF8
        $smtp = New-Object System.Net.Mail.SmtpClient('smtp.gmail.com', 587)
        $smtp.EnableSsl = $true
        $smtp.Credentials = $cred.GetNetworkCredential()
        $smtp.Send($mail)
        $mail.Dispose(); $smtp.Dispose()
        return $true
    } catch { Write-OpsLog ('Gmail 寄信失敗：' + $_.Exception.Message); return $false }
}

function Send-NtfyNotice([string]$title, [string]$body) {
    $cfg = Get-OpsConfig
    if (-not $cfg.ntfy_topic) { return $false }
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
        # 標題放在 header，中文要用 RFC 2047 編碼，ntfy 才吃得到
        $t = '=?UTF-8?B?' + [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($title)) + '?='
        Invoke-RestMethod -Method Post -Uri ('https://ntfy.sh/' + $cfg.ntfy_topic) -Body $bytes -Headers @{ Title = $t; Tags = 'warning' } -TimeoutSec 20 | Out-Null
        return $true
    } catch { Write-OpsLog ('ntfy 推播失敗：' + $_.Exception.Message); return $false }
}

function Send-OpsNotice([string]$title, [string]$body) {
    $cfg = Get-OpsConfig
    $done = @()
    if ($cfg.notify_desktop) { if (Send-DesktopNotice $title $body) { $done += '桌面' } }
    if ($cfg.gmail_to) { if (Send-GmailNotice $title $body) { $done += 'Gmail' } }
    if ($cfg.ntfy_topic) { if (Send-NtfyNotice $title $body) { $done += 'ntfy' } }
    Write-OpsLog ('通知 [' + ($done -join ',') + ']：' + $title)
    return $done
}
