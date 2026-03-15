$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = "$DesktopPath\YouTube Uploader.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "g:\My Drive\Youtube_Auto\start_app.bat"
$Shortcut.WorkingDirectory = "g:\My Drive\Youtube_Auto"
$Shortcut.Description = "Launch YouTube Auto Uploader"
$Shortcut.Save()
Write-Host "Shortcut created at: $ShortcutPath"
