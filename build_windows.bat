@echo off
setlocal

where py >nul 2>nul
if errorlevel 1 (
    echo Python 3 was not found. Install Python 3 from https://www.python.org/downloads/
    exit /b 1
)

for /f "delims=" %%F in ('where ffmpeg.exe 2^>nul') do if not defined FFMPEG set "FFMPEG=%%F"
for /f "delims=" %%F in ('where ffprobe.exe 2^>nul') do if not defined FFPROBE set "FFPROBE=%%F"
if not defined FFMPEG (
    echo FFmpeg was not found. Install the FFmpeg essentials build and add ffmpeg.exe to PATH.
    exit /b 1
)
if not defined FFPROBE (
    echo ffprobe.exe was not found. Install the FFmpeg essentials build and add ffprobe.exe to PATH.
    exit /b 1
)

if not exist .venv-build\Scripts\python.exe py -3 -m venv .venv-build
if errorlevel 1 exit /b 1
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name YTDown ^
    --add-binary "%FFMPEG%;ffmpeg" ^
    --add-binary "%FFPROBE%;ffmpeg" ^
    ytdown.py
if errorlevel 1 exit /b 1

echo.
echo Done. Your portable app is dist\YTDown.exe
