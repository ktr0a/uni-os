' Uni OS vault watch: hidden launcher for vault-watch.ps1 (EXPERIMENTAL, Windows only).
' Window style 0 = hidden, so no console window flashes when Task Scheduler starts it.
' Task Scheduler runs:  wscript.exe //B //Nologo "<install folder>\vault-watch-launcher.vbs"
' The script path is taken from this file's own folder, so the folder may contain spaces or "&".
Set sh = CreateObject("WScript.Shell")
dir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
cmd = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & dir & "vault-watch.ps1"""
sh.Run cmd, 0, True
