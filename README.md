## Make the portable installer

### Step 1: Install Python 3

1. Download Python 3 from [python.org](https://www.python.org/downloads/) and install it.
2. During installation, make sure to check the option to add Python to `PATH`.
3. After installation, verify that Python is available by opening a command prompt and running:
   ```sh
   python --version
   ```
   It should print a Python version such as `Python 3.12.x`.

### Step 2: Install FFmpeg

1. Install FFmpeg and make sure both `ffmpeg.exe` and `ffprobe.exe` are available on your `PATH`.
2. The easiest option is to use winget:
   ```sh
   winget install Gyan.Dev.FFmpeg
   ```
3. Alternatively, download a FFmpeg build from [FFmpeg's official website](https://www.ffmpeg.org/download.html) and extract it to a folder such as `C:\FFmpeg`.
4. Add the FFmpeg `bin` folder to your `PATH` environment variable, for example `C:\FFmpeg\bin`.
5. Verify the tools are found:
   ```sh
   ffmpeg -version
   ffprobe -version
   ```

### Step 3: Build the executable using `build_windows.bat`

1. Open a command prompt in the project folder that contains `build_windows.bat`.
2. Run:
   ```sh
   build_windows.bat
   ```
3. This script does the following:
   - checks that `py`, `ffmpeg.exe`, and `ffprobe.exe` are available
   - creates a `.venv-build` virtual environment
   - installs the Python dependencies from `requirements.txt`
   - builds the executable with PyInstaller and places it in the `dist` folder

### Step 4: Copy and run the executable

1. Once the build is complete, copy the `dist\YTDown.exe` file to the location where you want to run it.
2. Double-click `YTDown.exe` to start the app.

### Additional Notes

- Ensure the Python and FFmpeg installation paths are correct. Incorrect `PATH` entries can cause the build to fail.
- The script does not install Python or FFmpeg for you; it expects both to already be installed and available on `PATH`.
- If you encounter errors, check the console output for the exact message and fix the missing dependency or path issue.
