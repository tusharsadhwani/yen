mkdir %userprofile%\.yen\bin
SET download_url="https://github.com/tusharsadhwani/yen/releases/download/yen-x86_64-pc-windows-msvc"
curl -SL --progress-bar %download_url% --output %userprofile%\.yen\bin\yen.exe
setx PATH "%PATH%;%uerprofile\.yen\bin"
echo Successfully installed yen! Restart the shell to start using the 'yen' command.
