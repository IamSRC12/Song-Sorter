"""
build_installer.py — SongSorter v2.0
=====================================
1. Builds SongSorter.exe with PyInstaller
2. Downloads Inno Setup 6 silently if not installed
3. Compiles setup.iss → installer_output/SongSorter_Setup.exe
"""
import os, sys, subprocess, urllib.request, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_EXE   = os.path.join(SCRIPT_DIR, "dist", "SongSorter.exe")
ISCC_PATHS = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
]
INNO_DL    = "https://jrsoftware.org/download.php/is.exe"
INNO_TMP   = os.path.join(os.environ.get("TEMP", r"C:\Temp"), "innosetup_installer.exe")
ISS_FILE   = os.path.join(SCRIPT_DIR, "setup.iss")
OUT_DIR    = os.path.join(SCRIPT_DIR, "installer_output")
SPEC_FILE  = os.path.join(SCRIPT_DIR, "SongSorter.spec")

def run(cmd, **kw):
    print(f"\n▶  {' '.join(cmd[:6])} …\n")
    result = subprocess.run(cmd, **kw)
    if result.returncode != 0:
        print("ERROR – command failed")
        sys.exit(1)

def step(msg):
    print(f"\n{'─'*60}")
    print(f"  {msg}")
    print(f"{'─'*60}")

# ── Step 1: Build EXE ──────────────────────────────────────────
step("Step 1 / 3 – Building EXE with PyInstaller")
if os.path.exists(DIST_EXE):
    print("  Removing old EXE ...")
    os.remove(DIST_EXE)
run([sys.executable, "-m", "PyInstaller", "--clean", SPEC_FILE],
    cwd=SCRIPT_DIR)
print("  ✅  EXE built:", DIST_EXE)

# ── Step 2: Get Inno Setup ─────────────────────────────────────
step("Step 2 / 3 – Locating / Installing Inno Setup 6")
iscc = next((p for p in ISCC_PATHS if os.path.exists(p)), None)
if iscc:
    print(f"  ✅  Found: {iscc}")
else:
    print(f"  Downloading Inno Setup from {INNO_DL} …")
    try:
        req = urllib.request.Request(INNO_DL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, \
             open(INNO_TMP, "wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            done  = 0
            while chunk := resp.read(65536):
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    print(f"\r  {pct}% ({done/1024/1024:.1f} MB / "
                          f"{total/1024/1024:.1f} MB)", end="", flush=True)
        print(f"\n  Downloaded → {INNO_TMP}")
    except Exception as exc:
        print(f"\n  ⚠  Download failed: {exc}")
        print("  Please download Inno Setup manually from:")
        print("  https://jrsoftware.org/isdl.php")
        print("  Then re-run this script.")
        sys.exit(1)

    print("  Installing Inno Setup silently …")
    run([INNO_TMP, "/VERYSILENT", "/SUPPRESSMSGBOXES",
         "/NORESTART", "/SP-"])
    time.sleep(3)
    iscc = next((p for p in ISCC_PATHS if os.path.exists(p)), None)
    if not iscc:
        print("  ⚠  Installation seems to have succeeded but ISCC.exe not found.")
        print("  Manually run setup.iss with Inno Setup if needed.")
        sys.exit(1)
    print(f"  ✅  Installed: {iscc}")

# ── Step 3: Compile installer ──────────────────────────────────
step("Step 3 / 3 – Compiling installer with Inno Setup")
os.makedirs(OUT_DIR, exist_ok=True)
run([iscc, ISS_FILE])

final = os.path.join(OUT_DIR, "SongSorter_Setup.exe")
if os.path.exists(final):
    size = os.path.getsize(final) / 1024 / 1024
    print(f"\n  🎉  Installer ready!")
    print(f"  📦  {final}")
    print(f"  💾  {size:.1f} MB")
    os.startfile(OUT_DIR)
else:
    print("  ⚠  Installer file not found after compilation.")
    sys.exit(1)
