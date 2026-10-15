"""Build a genuine AppContainer diagnostic and unsigned MSIX; stdlib only."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[2]


def verify_package(path):
    with zipfile.ZipFile(path) as archive:
        executable = archive.read("AliceUwpProbe.exe")
        pe = struct.unpack_from("<I", executable, 0x3c)[0]
        if executable[pe:pe + 4] != b"PE\0\0":
            raise RuntimeError("Package executable is not a PE image")
        machine = struct.unpack_from("<H", executable, pe + 4)[0]
        flags = struct.unpack_from("<H", executable, pe + 24 + 70)[0]
        if machine != 0x8664 or not flags & 0x1000:
            raise RuntimeError("Package must contain an x64 AppContainer executable")
        if b"Windows.FullTrustApplication" in archive.read("AppxManifest.xml"):
            raise RuntimeError("A full-trust desktop manifest is not a UWP package")


def png(path, size):
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
    pixels = (b"\0" + bytes((10, 41, 77, 255)) * size) * size
    path.write_bytes(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", struct.pack(">2I5B", size, size, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


def main():
    vswhere = Path(os.environ["ProgramFiles(x86)"]) / "Microsoft Visual Studio/Installer/vswhere.exe"
    install = subprocess.check_output([
        str(vswhere), "-latest", "-products", "*", "-requires",
        "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"
    ], text=True).strip()
    if not install:
        raise SystemExit("Visual Studio C++ x64 build tools are required.")
    out = ROOT / "build_uwp_probe"
    package = out / "package"
    assets = package / "Assets"
    assets.mkdir(parents=True, exist_ok=True)
    # A failed rebuild must not leave a previous package looking successful.
    (out / "AliceUwpProbe.msix").unlink(missing_ok=True)
    for name, size in (("StoreLogo", 50), ("Logo", 150), ("SmallLogo", 44)):
        png(assets / (name + ".png"), size)
    shutil.copyfile(ROOT / "tools/uwp/AppxManifest.xml", package / "AppxManifest.xml")
    batch = out / "build.cmd"
    batch.write_text(f'''@echo off
call "{install}\\VC\\Auxiliary\\Build\\vcvarsall.bat" x64 uwp
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /DUNICODE /D_UNICODE /DWINAPI_FAMILY=WINAPI_FAMILY_APP "{ROOT / 'tools/uwp/probe.cpp'}" /Fo"{out / 'probe.obj'}" /Fe"{package / 'AliceUwpProbe.exe'}" /link /APPCONTAINER /SUBSYSTEM:WINDOWS windowsapp.lib d3d11.lib dxgi.lib xaudio2.lib
if errorlevel 1 exit /b %errorlevel%
"%WindowsSdkVerBinPath%x64\\makeappx.exe" pack /d "{package}" /p "{out / 'AliceUwpProbe.msix'}" /o
exit /b %errorlevel%
''', encoding="utf-8")
    with (out / "build.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(["cmd.exe", "/d", "/c", str(batch)],
                                   cwd=out, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, errors="replace")
        for line in process.stdout:
            print(line, end="", flush=True)
            log.write(line)
        code = process.wait()
    if code:
        raise SystemExit(code)
    verify_package(out / "AliceUwpProbe.msix")
    print("Unsigned diagnostic package:", out / "AliceUwpProbe.msix")


if __name__ == "__main__":
    main()
