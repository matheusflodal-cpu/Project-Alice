"""Collect native generator executables for the subsequent cross build."""
from pathlib import Path
import shutil
import sys

source, destination = map(Path, sys.argv[1:3])
destination.mkdir(parents=True, exist_ok=True)
for name in ("ParserGenerator", "DCONGENERATOR", "DCONINTERFACEGEN",
             "DataContainer-Lua", "DataContainer_OOS_Reporter"):
    matches = list(source.rglob(name + ".exe"))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one native {name}.exe, found {matches}")
    shutil.copy2(matches[0], destination / matches[0].name)
