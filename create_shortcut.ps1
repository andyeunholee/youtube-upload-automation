$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = "$DesktopPath\YouTube Uploader.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "h:\My Drive\Automation-H\AntiGravity\Youtube_Auto\start_app.bat"
$Shortcut.WorkingDirectory = "h:\My Drive\Automation-H\AntiGravity\Youtube_Auto"
$Shortcut.Description = "Launch YouTube Auto Uploader"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,14"
$Shortcut.Save()
Write-Host "✅ 바탕화면에 'YouTube Uploader' 아이콘이 생성되었습니다."
