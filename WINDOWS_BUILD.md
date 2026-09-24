# Windows EXE build

This project builds a native Windows executable with Nuitka. Build it on a
Windows 10/11 machine; a macOS build cannot produce a Windows `.exe`.

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer installed from python.org with the Python Launcher (`py`)
- Internet access for Python packages and Nuitka's compiler downloads
- At least 1 GB of free disk space

## One-click build

Open Command Prompt in the project folder and run:

```bat
build_windows.bat
```

The script creates `.venv`, installs `requirements.txt`, installs Nuitka when
needed, and runs `build_nuitka.py`. The final executable is:

```text
dist\CircuitDesignApp.exe
```

Copy only `dist\CircuitDesignApp.exe` to an end user's Windows machine. Python
is not required to run the finished executable.

## Manual build

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python build_nuitka.py
```

The executable listens on `127.0.0.1:8000` by default and opens the browser.
Set `OPEN_BROWSER=false` to prevent automatic browser launching. Keep the
backend local unless you configure a strong `BACKEND_API_KEY`; non-local
binding without an API key is rejected.

## Troubleshooting

- If `py` is not recognized, reinstall Python and enable **Add Python to PATH**.
- If Windows Defender warns about the unsigned file, verify that it came from
  the trusted project release before allowing it.
- If port 8000 is busy, set `API_PORT=8001` in `.env` before launching.
- Build artifacts can be removed with `rmdir /s /q build dist`.
