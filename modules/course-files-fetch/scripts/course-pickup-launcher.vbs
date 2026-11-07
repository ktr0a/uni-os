' Uni OS course pick-up: hidden launcher for course-pickup.ps1 (EXPERIMENTAL, Windows only).
' Window style 0 = hidden, so no console window flashes every minute.
' Task Scheduler runs:  wscript.exe //B //Nologo "<install folder>\course-pickup-launcher.vbs"
' The script path is taken from this file's own folder, so the folder may contain spaces or "&".
Set sh = CreateObject("WScript.Shell")
dir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
cmd = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & dir & "course-pickup.ps1"""
sh.Run cmd, 0, True
