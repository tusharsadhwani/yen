# Set yenpath variable to the user's .yen\bin directory
$yenpath = "$env:userprofile\.yen\bin"

# Create the .yen\bin directory if it doesn't exist
if (-not (Test-Path $yenpath)) {
    New-Item -Path $yenpath -ItemType Directory | Out-Null
}

# Download yen executable and save it to the .yen\bin directory
$downloadUrl = "https://github.com/tusharsadhwani/yen/releases/latest/download/yen-rs-x86_64-pc-windows-msvc.exe"
Invoke-WebRequest -Uri $downloadUrl -OutFile "$yenpath\yen.exe"
# Download userpath and microvenv too
Invoke-WebRequest -Uri "https://yen.tushar.lol/userpath.pyz" -OutFile "$yenpath\userpath.pyz"
Invoke-WebRequest -Uri "https://yen.tushar.lol/microvenv.py" -OutFile "$yenpath\microvenv.py"

# Get the user's PATH without the system-wide PATH
$userPath = (Get-ItemProperty -Path 'HKCU:\Environment' -Name 'Path').Path

# Check if the directory .yen\bin exists in the user's PATH
if (-not ($userPath -like "*$yenpath*")) {
    # If it doesn't exist, append $yenpath to the user's PATH
    $newPath = "$userPath;$yenpath"
    Set-ItemProperty -Path 'HKCU:\Environment' -Name 'Path' -Value $newPath
}

Write-Host "Successfully installed yen! Restart the shell to start using the 'yen' command."
