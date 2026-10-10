"""Installed-wheel smoke test: schema must remain available outside Git checkout."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tarfile import open as open_tar
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def _run_checked(command: list[str], **kwargs: object) -> None:
    """Report captured build stdout/stderr on failure instead of hiding diagnostics."""
    result = subprocess.run(command, check=False, **kwargs)  # type: ignore[arg-type]
    assert result.returncode == 0, (
        f"command failed ({result.returncode}): {command!r}\\n"
        f"stdout:\\n{result.stdout}\\nstderr:\\n{result.stderr}"
    )


def _checked_build(
    command: list[str], *,
    cwd: Path,
    check: bool,
    capture_output: bool,
    text: bool,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    """Preserve actionable stderr when wheel/sdist construction fails in CI."""
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=check,
            capture_output=capture_output,
            text=text,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        raise AssertionError(
            f"package build failed ({exc.returncode}):\\n"
            f"stdout:\\n{exc.stdout}\\nstderr:\\n{exc.stderr}"
        ) from exc


def test_installed_wheel_can_load_frozen_schema(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    _checked_build(
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
    _checked_build(
        [sys.executable, "-c", code],
        cwd=tmp_path,
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
    _checked_build(
        [sys.executable, "setup.py", "sdist", "--dist-dir", str(source_dist)],
        cwd=ROOT,
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
    _checked_build(
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
        capture_output=True,
        text=True,
        timeout=180,
    )
    wheels = list(wheelhouse.glob("oraec_tf-*.whl"))
    assert len(wheels) == 1
    with ZipFile(wheels[0]) as archive:
        assert archive.read("oraec_tf/schema_core.json") == canonical
