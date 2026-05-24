"""
Oracle v2 - Build Script
Compiles the project into distributable executables using PyInstaller.

Usage:
    python build.py          # Build both Setup GUI and Bot
    python build.py --gui    # Build only the Setup GUI
    python build.py --bot    # Build only the Bot
"""
import subprocess
import sys
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def ensure_pyinstaller():
    """Make sure PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("📦 Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller installed")


def build_gui():
    """Build the Setup Wizard as a standalone exe."""
    print("\n🔨 Building Setup GUI...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",                     # No console window
        "--name", "Oracle-v2-Setup",
        "--add-data", f"options_example.ini{os.pathsep}.",
        "--distpath", os.path.join(SCRIPT_DIR, "dist"),
        "--workpath", os.path.join(SCRIPT_DIR, "build_tmp"),
        "--specpath", os.path.join(SCRIPT_DIR, "build_tmp"),
        os.path.join(SCRIPT_DIR, "setup_gui.py"),
    ]
    subprocess.check_call(cmd, cwd=SCRIPT_DIR)
    print("✅ Setup GUI built → dist/Oracle-v2-Setup")


def build_bot():
    """Build the Bot as a standalone exe (console mode)."""
    print("\n🔨 Building Bot...")

    # Collect data files
    data_files = [
        f"options_example.ini{os.pathsep}.",
        f"classes.txt{os.pathsep}.",
    ]

    # Include .h5 models if they exist
    for model in ["oracle_v2_color.h5", "oracle_v2_gray.h5"]:
        model_path = os.path.join(SCRIPT_DIR, model)
        if os.path.exists(model_path):
            data_files.append(f"{model}{os.pathsep}.")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",                      # Keep console for bot logs
        "--name", "Oracle-v2-Bot",
        "--distpath", os.path.join(SCRIPT_DIR, "dist"),
        "--workpath", os.path.join(SCRIPT_DIR, "build_tmp"),
        "--specpath", os.path.join(SCRIPT_DIR, "build_tmp"),
    ]
    for df in data_files:
        cmd.extend(["--add-data", df])

    # Hidden imports for dynamic modules
    cmd.extend([
        "--hidden-import", "tensorflow",
        "--hidden-import", "numpy",
        "--hidden-import", "PIL",
        "--hidden-import", "colorama",
    ])

    cmd.append(os.path.join(SCRIPT_DIR, "main.py"))
    subprocess.check_call(cmd, cwd=SCRIPT_DIR)
    print("✅ Bot built → dist/Oracle-v2-Bot")


def cleanup():
    """Remove build artifacts."""
    build_tmp = os.path.join(SCRIPT_DIR, "build_tmp")
    if os.path.exists(build_tmp):
        shutil.rmtree(build_tmp)
        print("🧹 Cleaned up build_tmp/")


def main():
    args = sys.argv[1:]
    build_gui_flag = "--gui" in args or not args
    build_bot_flag = "--bot" in args or not args

    print("🔮 Oracle v2 — Build System")
    print("=" * 40)

    ensure_pyinstaller()

    if build_gui_flag:
        build_gui()
    if build_bot_flag:
        build_bot()

    cleanup()

    print("\n" + "=" * 40)
    print("🎉 Build complete! Check the dist/ folder.")
    print("\nDistribution files:")
    dist_dir = os.path.join(SCRIPT_DIR, "dist")
    if os.path.exists(dist_dir):
        for f in os.listdir(dist_dir):
            size = os.path.getsize(os.path.join(dist_dir, f))
            print(f"  📦 {f} ({size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
