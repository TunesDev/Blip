# Builds dist\Blip\Blip.exe   Run from the Blip folder:  .\build_exe.ps1
# Developed by Tunes
.\.venv\Scripts\python.exe -m pip install -q pyinstaller
.\.venv\Scripts\python.exe make_icon.py
# pre-generate the Windows UI Automation wrapper (used read-only by the desktop climber)
.\.venv\Scripts\python.exe -c "import comtypes.client; comtypes.client.GetModule('UIAutomationCore.dll')"
# PyInstaller's scratch files go to %TEMP% (not a "build" folder here): the Blip.exe in there
# is not a working app, and people kept double-clicking it by mistake.
$work = Join-Path $env:TEMP "BlipBuild"
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name Blip --workpath $work `
    --icon assets\blip.ico --collect-submodules winrt --collect-binaries winrt `
    --exclude-module tkinter --exclude-module unittest --exclude-module pydoc `
    --exclude-module PyQt6.QtQml --exclude-module PyQt6.QtQuick --exclude-module PyQt6.QtWebEngineCore `
    --exclude-module PyQt6.QtPdf --exclude-module PyQt6.QtSql --exclude-module PyQt6.QtTest main.py
# Software OpenGL (20 MB) is never used: Blip draws with plain 2D painting.
Remove-Item dist\Blip\_internal\PyQt6\Qt6\bin\opengl32sw.dll -ErrorAction SilentlyContinue
# Things Blip never uses: Qt's UI translations, extra image formats, SVG icons, network-status plugin
$qt = "dist\Blip\_internal\PyQt6\Qt6"
Remove-Item "$qt\translations" -Recurse -ErrorAction SilentlyContinue
Remove-Item "$qt\plugins\iconengines", "$qt\plugins\networkinformation", "$qt\plugins\generic" -Recurse -ErrorAction SilentlyContinue
Get-ChildItem "$qt\plugins\imageformats" -Exclude "qico.dll" -ErrorAction SilentlyContinue | Remove-Item -ErrorAction SilentlyContinue
Write-Host "Done: dist\Blip\Blip.exe"
