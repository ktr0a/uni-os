' Starts laptop-ping.ps1 (same folder) without a console window flashing up.
' Used by the Task Scheduler task "Uni OS laptop ping" (install-laptop.ps1 -LaptopPing). Windows, experimental.
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & dir & "\laptop-ping.ps1""", 0, False
