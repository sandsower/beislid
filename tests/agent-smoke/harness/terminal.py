from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def open_terminal(command: Path) -> tuple[bool, str]:
    terminal = os.environ.get("TERMINAL")
    candidates: list[list[str]] = []
    if terminal:
        candidates.append([terminal, "-e", str(command)])
    candidates.extend([
        ["kitty", str(command)],
        ["alacritty", "-e", str(command)],
        ["gnome-terminal", "--", str(command)],
        ["konsole", "-e", str(command)],
        ["xterm", "-e", str(command)],
    ])

    for argv in candidates:
        exe = argv[0]
        if not shutil.which(exe):
            continue
        try:
            subprocess.Popen(argv)
            return True, " ".join(argv)
        except Exception as exc:
            last = f"{exe}: {exc}"
            continue
    return False, locals().get("last", "no supported terminal found")
