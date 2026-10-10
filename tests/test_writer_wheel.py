"""Installed-wheel smoke test: schema must remain available outside Git checkout."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def test_installed_wheel_can_load_frozen_schema(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-build-isolation",
            "--no-deps",
            "--wheel-dir",
            str(wheelhouse),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )
    wheels = list(wheelhouse.glob("oraec_tf-*.whl"))
    assert len(wheels) == 1

    installed = tmp_path / "isolated"
    installed.mkdir()
    with ZipFile(wheels[0]) as archive:
        assert "oraec_tf/schema_core.json" in archive.namelist()
        archive.extractall(installed)

    # Import the extracted wheel without ever exposing repository paths.
    code = (
        "from oraec_tf.writer import _feature_metadata; "
        "m = _feature_metadata({'written_form'}); "
        "assert m['written_form']['sourceField'] == 'token.written_form'"
    )
    env = {**os.environ, "PYTHONPATH": str(installed)}
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
