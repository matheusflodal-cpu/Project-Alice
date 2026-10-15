"""Preserve UWP restrictions; normalize only the CRT in generated projects."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def prepare(directory):
    projects = list(Path(directory).rglob("*.vcxproj"))
    if not projects:
        raise RuntimeError("No generated Visual Studio projects found")
    for project in projects:
        text = project.read_text(encoding="utf-8-sig")
        text = text.replace("<RuntimeLibrary>MultiThreaded</RuntimeLibrary>",
                            "<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>")
        text = text.replace("<RuntimeLibrary>MultiThreadedDebug</RuntimeLibrary>",
                            "<RuntimeLibrary>MultiThreadedDebugDLL</RuntimeLibrary>")
        ET.fromstring(text)
        project.write_text(text, encoding="utf-8")
    print(f"Dynamic CRT selected in {len(projects)} projects; UWP restrictions retained")


if __name__ == "__main__":
    prepare(sys.argv[1])
