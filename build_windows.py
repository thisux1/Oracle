"""
Oracle v2 - Windows Build Script
Builds the frontend, packages with PyInstaller, and generates the Inno Setup installer.

Usage:
    python build_windows.py              # Full build (frontend + PyInstaller + installer)
    python build_windows.py --frontend   # Build frontend only
    python build_windows.py --package    # PyInstaller only (skip frontend)
    python build_windows.py --installer  # Inno Setup only (skip build)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = SCRIPT_DIR / "dashboard"
DIST_DIR = DASHBOARD_DIR / "dist"
BUILD_DIR = SCRIPT_DIR / "build_windows"
DIST_OUTPUT = BUILD_DIR / "dist"
SPEC_FILE = BUILD_DIR / "OracleOS.spec"

APP_NAME = "OracleOS"
APP_VERSION = "3.0.0"
ENTRY_POINT = SCRIPT_DIR / "launch_dashboard.py"
SETUP_ISS = SCRIPT_DIR / "setup.iss"

# Platform detection
IS_WINDOWS = sys.platform == "win32"
EXE_EXT = ".exe" if IS_WINDOWS else ""


def _has_shared_lib(py: str) -> bool:
    """Check if a Python executable has shared library support (required by PyInstaller).
    
    PyInstaller needs libpython3.X.so or .dylib (not .a static lib).
    """
    try:
        r = subprocess.run(
            [py, "-c", """
import sysconfig
lib = sysconfig.get_config_var('LDLIBRARY') or ''
# Must be .so or .dylib — .a is a static library, PyInstaller rejects it
if lib.endswith('.so') or lib.endswith('.dylib'):
    print('ok')
"""],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and "ok" in r.stdout
    except Exception:
        return False


def find_build_python() -> str:
    """Find a Python 3.12 executable with shared library support (required by PyInstaller on Linux).
    
    Creates a build venv with Python 3.12 if needed.
    """
    venv_dir = SCRIPT_DIR / ".venv_build"
    python_bin = venv_dir / "bin" / "python"

    # If venv already exists and has shared lib (or is on Windows), reuse it
    if python_bin.exists() and (IS_WINDOWS or _has_shared_lib(str(python_bin))):
        print(f"[OK] Reusing build venv: {python_bin}")
        return str(python_bin)

    # On Windows, just use sys.executable (always has shared lib)
    if IS_WINDOWS:
        print(f"[OK] Using current Python: {sys.executable}")
        return sys.executable

    # On Linux, find Python 3.12 with shared lib
    preferred = ["/usr/bin/python3.12", "/usr/local/bin/python3.12"]
    system_py = None

    for py in preferred:
        if os.path.isfile(py) and _has_shared_lib(py):
            system_py = py
            break

    # Fallback: search for any 3.12
    if not system_py:
        import glob as globmod
        for py in sorted(globmod.glob("/usr/bin/python3.12*"), reverse=True):
            if _has_shared_lib(py):
                system_py = py
                break

    if not system_py:
        print("[ERROR] Python 3.12 not found.")
        print("        On Arch: sudo pacman -S python")
        print("        On Debian/Ubuntu: sudo apt install python3.12")
        sys.exit(1)

    print(f"[OK] Found Python 3.12: {system_py}")

    # Create or recreate venv
    if venv_dir.exists():
        shutil.rmtree(venv_dir)

    print("[INFO] Creating build venv with Python 3.12...")
    subprocess.run([system_py, "-m", "venv", str(venv_dir)], check=True)
    pip = venv_dir / "bin" / "pip"
    subprocess.run([str(pip), "install", "--upgrade", "pip"], check=True,
                   capture_output=True)
    req_file = SCRIPT_DIR / "requirements.txt"
    if req_file.exists():
        subprocess.run([str(pip), "install", "-r", str(req_file)], check=True)
    subprocess.run([str(pip), "install", "pyinstaller"], check=True)
    print("[OK] Build venv created at .venv_build/")

    if not python_bin.exists():
        print("[ERROR] Failed to create build venv")
        sys.exit(1)

    return str(python_bin)


def run(cmd: list[str], cwd: Path | None = None, description: str = "") -> None:
    """Run a command and raise on failure."""
    if description:
        print(f"\n{'='*50}")
        print(f"  {description}")
        print(f"{'='*50}")
        print(f"  > {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or SCRIPT_DIR)
    if result.returncode != 0:
        print(f"\n[ERROR] Command failed with exit code {result.returncode}")
        sys.exit(1)


def step_build_frontend() -> None:
    """Run npm run build inside dashboard/."""
    if not DASHBOARD_DIR.exists():
        print("[ERROR] dashboard/ directory not found")
        sys.exit(1)

    if not (DASHBOARD_DIR / "node_modules").exists():
        print("[INFO] node_modules not found, running npm install first...")
        run(["npm", "install"], cwd=DASHBOARD_DIR, description="Installing dashboard dependencies")

    run(["npm", "run", "build"], cwd=DASHBOARD_DIR, description="Building frontend (vite build)")

    if not DIST_DIR.exists():
        print("[ERROR] dashboard/dist/ not found after build")
        sys.exit(1)

    print(f"[OK] Frontend built successfully at {DIST_DIR}")


def step_pyinstaller() -> None:
    """Package with PyInstaller using --onedir mode."""
    py = find_build_python()

    # Ensure PyInstaller is installed
    try:
        result = subprocess.run([py, "-c", "import PyInstaller; print(PyInstaller.__version__)"],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"[OK] PyInstaller {result.stdout.strip()} found")
        else:
            raise ImportError
    except Exception:
        print("[INFO] Installing PyInstaller...")
        run([py, "-m", "pip", "install", "pyinstaller"], description="Installing PyInstaller")

    # Clean previous build
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        py, "-m", "PyInstaller",
        "--onedir",
        "--windowed",
        "--name", APP_NAME,
        "--distpath", str(DIST_OUTPUT),
        "--workpath", str(BUILD_DIR / "build"),
        "--specpath", str(BUILD_DIR),
    ]

    # Add data files
    data_files = [
        (DASHBOARD_DIR / "dist", "dashboard/dist"),
        (SCRIPT_DIR / "options_example.ini", "."),
        (SCRIPT_DIR / "classes.txt", "."),
    ]

    # Add .h5 models if they exist
    for model_name in ["oracle_v2_color.h5", "oracle_v2_gray.h5"]:
        model_path = SCRIPT_DIR / model_name
        if model_path.exists():
            data_files.append((model_path, "."))

    for src, dst in data_files:
        if src.exists():
            cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

    # Hidden imports — every module that PyInstaller cannot auto-detect
    hidden_imports = [
        # TensorFlow / ML
        "tensorflow",
        "numpy",
        "PIL",
        # Uvicorn / ASGI (auto-detection is unreliable in frozen builds)
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # FastAPI / Starlette
        "fastapi",
        "fastapi.responses",
        "fastapi.staticfiles",
        "starlette",
        "starlette.routing",
        "starlette.responses",
        "starlette.middleware",
        "starlette.middleware.cors",
        "starlette.staticfiles",
        # Pydantic (v2 uses Rust extensions that PyInstaller may miss)
        "pydantic",
        "pydantic.networks",
        "pydantic_core",
        # pywebview — native window
        "webview",
        "webview.platforms.winforms",
        # Multipart / file uploads
        "multipart",
        "multipart.multipart",
        # Networking
        "aiohttp",
        "aiohttp.connector",
        # Discord
        "discord",
        # Terminal / TUI
        "colorama",
        "textual",
        "textual.app",
        "textual.widgets",
        # Standard lib helpers that PyInstaller sometimes strips
        "ctypes",
        "ctypes.wintypes",
        "email.mime",
        "email.mime.multipart",
        "email.mime.text",
        "logging.handlers",
        "concurrent.futures",
    ]

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Collect all subpackages from bot/
    cmd.extend(["--collect-submodules", "bot"])

    # collect-all includes native DLLs and data files (pydantic uses Rust .pyd/.dll)
    for pkg in ["pydantic", "pydantic_core", "webview", "pywinpty"]:
        cmd.extend(["--collect-all", pkg])

    # Entry point
    cmd.append(str(ENTRY_POINT))

    run(cmd, description="Building Windows executable with PyInstaller")

    exe_path = DIST_OUTPUT / APP_NAME / f"{APP_NAME}{EXE_EXT}"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"[OK] Executable created: {exe_path} ({size_mb:.1f} MB)")
        if not IS_WINDOWS:
            print(f"[WARN] This is a Linux binary. To build Windows .exe, run on Windows.")
    else:
        print(f"[ERROR] Expected executable not found at {exe_path}")
        sys.exit(1)


def step_inno_setup() -> None:
    """Run Inno Setup compiler to generate the installer."""
    if not IS_WINDOWS:
        print("[SKIP] Inno Setup requires Windows. Skipping installer generation.")
        print("       To build the installer, run this script on Windows or use GitHub Actions.")
        return

    if not SETUP_ISS.exists():
        print(f"[ERROR] Inno Setup script not found: {SETUP_ISS}")
        sys.exit(1)

    # Try common ISCC locations
    iscc_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        "ISCC.exe",  # In PATH
    ]

    iscc_exe = None
    for p in iscc_paths:
        if os.path.isfile(p):
            iscc_exe = p
            break

    if iscc_exe is None:
        print("[WARN] Inno Setup compiler not found. Skipping installer generation.")
        print("       Install Inno Setup from https://jrsoftware.org/isinfo.php")
        print(f"       Then run: ISCC.exe {SETUP_ISS}")
        return

    run([iscc_exe, str(SETUP_ISS)], description="Building Inno Setup installer")

    # Check for output
    installer_output = SCRIPT_DIR / "Output"
    if installer_output.exists():
        for f in installer_output.iterdir():
            if f.suffix == ".exe":
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"[OK] Installer created: {f} ({size_mb:.1f} MB)")
                # Copy to project root for easy access
                dest = SCRIPT_DIR / f.name
                shutil.copy2(f, dest)
                print(f"[OK] Copied to: {dest}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Oracle v2 Windows Build Pipeline")
    parser.add_argument("--frontend", action="store_true", help="Build frontend only")
    parser.add_argument("--package", action="store_true", help="PyInstaller only (skip frontend)")
    parser.add_argument("--installer", action="store_true", help="Inno Setup only")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_all = not (args.frontend or args.package or args.installer)

    print(f"\n{'#'*50}")
    print(f"  Oracle v2 - Windows Build Pipeline")
    print(f"  Version: {APP_VERSION}")
    print(f"{'#'*50}")

    if run_all or args.frontend:
        step_build_frontend()

    if run_all or args.package:
        step_pyinstaller()

    if run_all or args.installer:
        step_inno_setup()

    print(f"\n{'#'*50}")
    print("  Build pipeline completed!")
    print(f"{'#'*50}\n")


if __name__ == "__main__":
    main()
