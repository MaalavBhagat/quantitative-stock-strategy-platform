"""Every script in scripts/ answers --help (one-line purpose + how to run) and then does NOTHING else (Phase 10.5)."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = sorted(
    p
    for p in (Path(__file__).resolve().parents[1] / "scripts").glob("*.py")
    if not p.name.startswith("_")
)


def test_every_script_has_help():
    for path in SCRIPTS:
        text = path.read_text(encoding="utf-8")
        assert text.lstrip().startswith('"""'), f"{path.name}: no docstring"
        assert "argparse" in text or "handle_help(__doc__)" in text, f"{path.name}: no --help"


@pytest.mark.parametrize(
    "name", ["download_initial_dataset.py", "run_final_test.py", "ai_label_sample.py"]
)
def test_help_describes_and_exits_without_doing_anything(name, tmp_path):
    path = next(p for p in SCRIPTS if p.name == name)
    proc = subprocess.run(
        [sys.executable, str(path), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().splitlines()[0]  # one-line purpose
    assert "uv run" in proc.stdout or "usage" in proc.stdout  # how to run it
    assert list(tmp_path.iterdir()) == []  # nothing was written
