@echo off
setlocal enabledelayedexpansion

REM Set yenpath variable to the user's .yen\bin directory
SET "yenpath=%userprofile%\.yen\bin"

REM Create the .yen\bin directory if it doesn't exist
mkdir "%yenpath%" 2>nul

REM Download yen executable and save it to the .yen\bin directory
SET "download_url=https://github.com/tusharsadhwani/yen/releases/latest/download/yen-rs-x86_64-pc-windows-msvc.exe"
curl -SL --progress-bar "%download_url%" --output "%yenpath%\yen.exe"
REM Download userpath too
curl -SL --progress-bar "https://yen.tushar.lol/userpath.pyz" --output "%yenpath%\userpath.pyz"

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
