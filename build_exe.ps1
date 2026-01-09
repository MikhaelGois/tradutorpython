# Build script: empacota o app em um único .exe usando PyInstaller
param(
    [string]$Entry = "translator_launcher.py",
    [string]$Name = "TradutorReal"
)

$venvPy = "C:\Users\MBalieroDG\Desktop\dev\tradutor em tempo real\.venv\Scripts\python.exe"
Write-Output "Instalando PyInstaller no venv..."
& $venvPy -m pip install pyinstaller

Write-Output "Rodando PyInstaller... isso pode demorar alguns minutos."
& $venvPy -m PyInstaller --onefile --windowed --name $Name $Entry

Write-Output "Build finalizado. Verifique a pasta 'dist' para o executável $Name.exe"
