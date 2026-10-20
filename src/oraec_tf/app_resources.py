"""Discover the standard Text-Fabric app installed with the ORAEC-TF wheel."""

from __future__ import annotations

from pathlib import Path


def installed_app_dir() -> Path:
    """Return the wheel-owned Text-Fabric app directory, not a clone checkout."""
    directory = (Path(__file__).resolve().parent / "tf_app").resolve()
    if not (directory / "config.yaml").is_file():
        raise FileNotFoundError(
            "standard ORAEC-TF Text-Fabric app resource is missing from installation"
        )
    return directory
