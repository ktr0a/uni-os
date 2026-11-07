@echo off
rem Double-click this on the home-server laptop (keep setup-home-server.ps1 and your main laptop's
rem public key file uni-home.pub in the same folder). It asks for admin rights once (UAC: Yes), then
rem runs the setup script and leaves the window open so the result can be read. Windows, experimental.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-File','\"%~dp0setup-home-server.ps1\"','-PublicKey','\"%~dp0uni-home.pub\"'"
