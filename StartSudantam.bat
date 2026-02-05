@echo off
cd /d "%~dp0"

:: 1. CHECK FOR ADMIN RIGHTS (Required to open Firewall)
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Admin rights confirmed. Opening Firewall Port...
) else (
    echo Requesting Admin rights to fix mobile connection...
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit /b
)

:: 2. OPEN FIREWALL PORT 8501 (Allow Mobile Access)
netsh advfirewall firewall delete rule name="SudantamMobile" >nul 2>&1
netsh advfirewall firewall add rule name="SudantamMobile" dir=in action=allow protocol=TCP localport=8501 profile=any >nul
echo Firewall configured successfully!

:: 3. KILL OLD PROCESSES
taskkill /F /IM "pythonw.exe" >nul 2>&1

:: 4. START ENGINE (Mobile Mode)
start "" pythonw -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true

:: 5. LAUNCH ON PC
timeout /t 5 >nul
start msedge --app=http://localhost:8501

exit