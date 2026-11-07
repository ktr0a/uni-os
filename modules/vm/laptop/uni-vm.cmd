@echo off
rem uni-vm.cmd: run "uni-vm <args>" on the always-on host from any Windows terminal (experimental).
rem Install: copy to %USERPROFILE%\.local\bin (a folder on PATH), or run install-laptop.ps1 -UniVmCmd.
rem Settings: %USERPROFILE%\.config\uni-os\laptop.env (HOST_ALIAS, HOST_TRANSPORT, WSL_DISTRO, WSL_USER).
rem Examples:  uni-vm status   ^|   uni-vm jobs   ^|   uni-vm jobs on daily-study-prep   ^|   uni-vm doctor
rem stderr is dropped (gcloud's IAP tunnel prints harmless tracebacks on Windows).
setlocal
set "HOST_ALIAS=uni-vm"
set "HOST_TRANSPORT=ssh"
set "WSL_DISTRO=Ubuntu-24.04"
set "WSL_USER="
set "ENVF=%USERPROFILE%\.config\uni-os\laptop.env"
if exist "%ENVF%" for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%ENVF%") do set "%%a=%%~b"
if /i "%HOST_TRANSPORT%"=="wsl" (
  "%SystemRoot%\System32\OpenSSH\ssh.exe" -o BatchMode=yes %HOST_ALIAS% "wsl.exe -d %WSL_DISTRO% -u %WSL_USER% --exec /home/%WSL_USER%/.local/bin/uni-vm %*" 2>nul
) else (
  "%SystemRoot%\System32\OpenSSH\ssh.exe" -o BatchMode=yes %HOST_ALIAS% "export PATH=$HOME/.local/bin:$PATH; uni-vm %*" 2>nul
)
endlocal
