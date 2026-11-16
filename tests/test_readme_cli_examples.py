"""Exercise the copy-paste Bash example without accessing ORAEC source data."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADING = "### Optional local Karnak crosswalks\n"
SOURCE_REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


def test_readme_local_karnak_example_is_one_valid_bash_command(tmp_path: Path) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.count(HEADING) == 1
    section = readme.split(HEADING, 1)[1]
    command = section.split("```bash\n", 1)[1].split("\n```", 1)[0]
    capture = tmp_path / "argv.txt"

    # Shell function replaces the real CLI, recording arguments only.
    # The documented command must not invoke Git, download, or convert data.
    shell = (
        "set -eu\n"
        'oraec-tf() { printf "%s\\n" "$@" > "$ORAEC_DOC_ARGS"; }\n'
        f"{command}\n"
    )
    run = subprocess.run(
        ["bash", "-c", shell],
        cwd=tmp_path,
        env={**os.environ, "ORAEC_DOC_ARGS": str(capture)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    assert capture.read_text(encoding="utf-8").splitlines() == [
        "convert",
        "upstream/corpus_raw_data",
        "--output",
        "build/oraec-with-karnak",
        "--upstream-commit",
        SOURCE_REVISION,
        "--include-karnak",
    ]
