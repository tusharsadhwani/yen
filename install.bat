@echo off

SET yenpath=%userprofile%\.yen\bin
mkdir %yenpath%

SET download_url="https://github.com/tusharsadhwani/yen/releases/download/yen-x86_64-pc-windows-msvc.exe"
curl -SL --progress-bar %download_url% --output %yenpath%\yen.exe

:: Set PATH if not present
if "%PATH:.yen\bin=repl%"=="%PATH%" setx PATH "%PATH%;%yenpath%"

echo Successfully installed yen! Restart the shell to start using the 'yen' command.
