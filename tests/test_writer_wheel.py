"""Installed-wheel smoke test: schema must remain available outside Git checkout."""

from __future__ import annotations

import os
import subprocess
import sys
from tarfile import open as open_tar
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


def test_sdist_can_rebuild_a_wheel_with_identical_frozen_schema(
    tmp_path: Path,
) -> None:
    source_dist = tmp_path / "sdist"
    source_dist.mkdir()
    subprocess.run(
        [sys.executable, "setup.py", "sdist", "--dist-dir", str(source_dist)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )
    archives = list(source_dist.glob("oraec_tf-*.tar.gz"))
    assert len(archives) == 1
    canonical = (ROOT / "schema" / "core.json").read_bytes()
    with open_tar(archives[0], "r:gz") as archive:
        schema_files = [
            member for member in archive.getmembers()
            if member.name.endswith("/schema/core.json")
        ]
        assert len(schema_files) == 1
        payload = archive.extractfile(schema_files[0])
        assert payload is not None
        assert payload.read() == canonical

    wheelhouse = tmp_path / "from_sdist"
    wheelhouse.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(archives[0]),
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheelhouse),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )
    wheels = list(wheelhouse.glob("oraec_tf-*.whl"))
    assert len(wheels) == 1
    with ZipFile(wheels[0]) as archive:
        assert archive.read("oraec_tf/schema_core.json") == canonical
