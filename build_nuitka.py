import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "CircuitDesignApp"


def run(cmd):
    print(f"[build] $ {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(ROOT))


def ensure_nuitka():
    try:
        subprocess.check_call([sys.executable, "-m", "nuitka", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    except Exception:
        run([sys.executable, "-m", "pip", "install", "nuitka"])


def main():
    ensure_nuitka()
    DIST.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)

    executable_name = APP_NAME + (".exe" if sys.platform == "win32" else "")

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        "--onefile-no-compression",
        "--output-dir=dist",
        f"--output-filename={executable_name}",
        "--enable-plugin=anti-bloat",
        "--include-data-dir=frontend=frontend",
        "--include-package=app",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=scipy",
        "--jobs=2",
        "--assume-yes-for-downloads",
        "app/main.py",
    ]
    run(cmd)

    print("\nBuild complete.")
    print(f"Output: {DIST / executable_name}")


if __name__ == "__main__":
    main()
