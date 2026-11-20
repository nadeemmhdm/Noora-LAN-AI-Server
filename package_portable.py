import os
import sys
import zipfile
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
OUTPUT_ZIP = APP_ROOT / "Nila-LAN-AI-Portable.zip"

INCLUDE_DIRS = [
    "backend",
    "engine",
    "frontend/dist",
    "src-tauri"
]

INCLUDE_FILES = [
    "run_desktop.bat",
    "run_headless.bat",
    "Nila-LAN-AI-Setup.bat",
    "requirements.txt",
    "README.md"
]

def make_portable_zip():
    print(f"Creating portable distribution: {OUTPUT_ZIP.name}...")
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for file_name in INCLUDE_FILES:
            fpath = APP_ROOT / file_name
            if fpath.exists():
                print(f"  Adding file: {file_name}")
                z.write(fpath, arcname=f"NooraAI/{file_name}")

        for dir_name in INCLUDE_DIRS:
            dpath = APP_ROOT / dir_name
            if dpath.exists():
                print(f"  Adding directory: {dir_name}")
                for root, _, files in os.walk(dpath):
                    for file in files:
                        full_path = Path(root) / file
                        # Skip pycache and temporary files
                        if "__pycache__" in str(full_path) or full_path.suffix == ".pyc":
                            continue
                        rel_path = full_path.relative_to(APP_ROOT)
                        z.write(full_path, arcname=f"NooraAI/{rel_path}")

    size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print(f"\n[+] Successfully created {OUTPUT_ZIP.name} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    make_portable_zip()
