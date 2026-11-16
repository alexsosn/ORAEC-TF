"""Behavioral guard for the actual prerelease publication shell step.

The gh and curl executables are replaced by local test shims. Nothing can be
published and no network/API call occurs during these tests.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "software-release.yml"
PUBLISH_STEP = "      - name: Publish exactly three software-only assets under existing tag"


def _publication_shell() -> str:
    source = WORKFLOW.read_text(encoding="utf-8")
    assert source.count(PUBLISH_STEP) == 1
    step = source.split(PUBLISH_STEP, 1)[1]
    script = step.split("        run: |\n", 1)[1]
    lines = script.splitlines()
    # The publication block is deliberately the last step in this workflow.
    assert all(not line.strip() or line.startswith("          ") for line in lines)
    return "\n".join(line[10:] if line else "" for line in lines) + "\n"


@pytest.mark.parametrize(
    ("http_status", "curl_exit", "should_create"),
    [
        ("404", 0, True),  # Only a completed API 404 establishes absence.
        ("200", 0, False),
        ("401", 0, False),
        ("403", 0, False),
        ("429", 0, False),
        ("500", 0, False),
        ("000", 7, False),  # Failed DNS/network/transport with no HTTP result.
    ],
)
def test_release_publication_requires_confirmed_absence(
    tmp_path: Path, http_status: str, curl_exit: int, should_create: bool
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl = bin_dir / "curl"
    curl.write_text(
        '#!/bin/sh\nprintf "%s" "$MOCK_HTTP_STATUS"\nexit "$MOCK_CURL_EXIT"\n',
        encoding="utf-8",
    )
    gh = bin_dir / "gh"
    gh.write_text(
        '#!/bin/sh\n'
        'if [ "$1" = "release" ] && [ "$2" = "create" ]; then\n'
        '  printf "%s\\n" "$*" > "$CREATE_SENTINEL"\n'
        'fi\n'
        'exit 0\n',
        encoding="utf-8",
    )
    curl.chmod(0o755)
    gh.chmod(0o755)
    sentinel = tmp_path / "created.txt"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "MOCK_HTTP_STATUS": http_status,
        "MOCK_CURL_EXIT": str(curl_exit),
        "CREATE_SENTINEL": str(sentinel),
        "RUNNER_TEMP": str(tmp_path),
        "GH_TOKEN": "synthetic-test-token",
        "GITHUB_REPOSITORY": "alexsosn/ORAEC-TF",
        "RELEASE_TAG": "v0.1.0rc1",
        "RELEASE_SOURCE": "a" * 40,
    }
    result = subprocess.run(
        ["bash", "-c", _publication_shell()],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) is should_create, result.stderr
    assert sentinel.exists() is should_create, result.stderr
    if should_create:
        assert "release create v0.1.0rc1" in sentinel.read_text(encoding="utf-8")
