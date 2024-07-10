@echo off
setlocal enabledelayedexpansion

REM Set yenpath variable to the user's .yen\bin directory
SET "yenpath=%userprofile%\.yen\bin"

REM Create the .yen\bin directory if it doesn't exist
mkdir "%yenpath%" 2>nul

REM Function to download using curl or wget
:download
if exist "%SystemRoot%\System32\curl.exe" (
    curl -SL --progress-bar "%1" --output "%2"
) else if exist "%SystemRoot%\System32\wget.exe" (
    wget "%1" -O "%2"
) else (
    echo Neither curl nor wget is installed. Please install one of them and try again.
    exit /b 1
)
REM Return to the caller
exit /b 0

REM Download yen executable and save it to the .yen\bin directory
SET "download_url=https://github.com/tusharsadhwani/yen/releases/latest/download/yen-rs-x86_64-pc-windows-msvc.exe"
call :download "%download_url%" "%yenpath%\yen.exe"

REM Download userpath and microvenv too
call :download "https://yen.tushar.lol/userpath.pyz" "%yenpath%\userpath.pyz"
call :download "https://yen.tushar.lol/microvenv.py" "%yenpath%\microvenv.py"

REM Get the user's PATH without the system-wide PATH
for /f "skip=2 tokens=2,*" %%A in ('reg query HKCU\Environment /v PATH') do (
    set "UserPath=%%B"
    goto :Continue
)
:Continue

REM Check if the directory .yen\bin exists in the user's PATH
echo !UserPath! | findstr /i /c:".yen\bin" >nul
if errorlevel 1 (
    REM If it doesn't exist, append !yenpath! to the user's PATH
    setx PATH "!UserPath!;!yenpath!"
)

endlocal

echo Successfully installed yen! Restart the shell to start using the 'yen' command.
