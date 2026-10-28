"""Cross-platform offline installed-wheel smoke for ORAEC-TF release issue #59.

Wheel acquisition happens first, separately for each platform. The published
tf-build wheel is checked against its release digest. Pip resolves ordinary
version requirements using only the captured local wheels and their hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import venv
import zipfile
from email.parser import Parser
from pathlib import Path

TF_BUILD_VERSION = "0.1.0rc1"
TF_BUILD_SHA256 = "dff2a14c0299422b4716217d04e6d43b47e714f4dacdb21d9939292051e82c9a"


def _wheel_metadata(path: Path) -> tuple[str, str, tuple[str, ...]]:
    """Inspect the actual artifact rather than inferring dependencies from a repo."""
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise ValueError(f"wheel must have exactly one METADATA file: {path.name}")
        record = Parser().parsestr(archive.read(names[0]).decode("utf-8"))
        name = record.get("Name")
        version = record.get("Version")
        if not name or not version:
            raise ValueError(f"wheel has no package name/version: {path.name}")
        return name.lower().replace("_", "-"), version, tuple(
            record.get_all("Requires-Dist", ())
        )


def write_hash_manifest(wheelhouse: Path, manifest: Path) -> dict[str, str]:
    """Generate portable version requirements paired with wheel SHA256 digests."""
    wheels = sorted(wheelhouse.glob("*.whl"))
    if not wheels:
        raise ValueError("wheelhouse must contain at least one wheel")
    packages: dict[str, tuple[str, tuple[str, ...]]] = {}
    rows = []
    checksums: dict[str, str] = {}
    for wheel in wheels:
        if not wheel.is_file() or wheel.is_symlink():
            raise ValueError(f"unexpected wheel artifact: {wheel}")
        name, version, requirements = _wheel_metadata(wheel)
        if name in packages:
            raise ValueError(f"duplicate wheel distribution: {name}")
        packages[name] = (version, requirements)
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        if name == "tf-build" and digest != TF_BUILD_SHA256:
            raise ValueError("tf-build wheel SHA256 differs from published release")
        checksums[wheel.name] = digest
        rows.append(f"{name}=={version} --hash=sha256:{digest}")
    if "oraec-tf" not in packages or "tf-build" not in packages:
        raise ValueError("source wheelhouse missing ORAEC-TF or tf-build")
    if packages["oraec-tf"][0] != "0.1.0.dev0":
        raise ValueError("unexpected ORAEC-TF prerelease wheel version")
    if packages["tf-build"][0] != TF_BUILD_VERSION:
        raise ValueError("unexpected tf-build prerelease wheel version")
    dependencies = packages["oraec-tf"][1]
    if not any(
        item.replace(" ", "") == f"tf-build=={TF_BUILD_VERSION}"
        for item in dependencies
    ):
        raise ValueError("wheel METADATA does not pin the released tf-build version")
    if any("@" in item for _, requirements in packages.values() for item in requirements):
        raise ValueError("offline wheel dependencies must not contain direct URLs")
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return checksums


def verify_installed_wheels(
    source_tree: Path, manifest: Path, environment: Path, *, wheelhouse: Path,
) -> None:
    """Install exactly hash-verified local wheel files into a fresh venv."""
    source_tree = source_tree.resolve()
    manifest = manifest.resolve()
    environment = environment.resolve()
    wheelhouse = wheelhouse.resolve()
    if environment.exists():
        raise ValueError("offline installed wheel environment must not preexist")
    venv.EnvBuilder(with_pip=True).create(environment)
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    interpreter = scripts / ("python.exe" if os.name == "nt" else "python")
    if not interpreter.is_file():
        raise ValueError("venv Python was not created")
    env = os.environ.copy()
    # Inherited pip find-links/requirements must not add remote candidates.
    for key in tuple(env):
        if key.startswith("PIP_"):
            del env[key]
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.update({
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_CONFIG_FILE": os.devnull,
        "PYTHONNOUSERSITE": "1",
        "ORAEC_SOURCE_TREE": str(source_tree.resolve()),
        "PATH": str(scripts),
    })
    subprocess.run([
        str(interpreter), "-m", "pip", "install",
        "--no-index", "--no-cache-dir", "--only-binary=:all:", "--require-hashes",
        "--find-links", str(wheelhouse.resolve()),
        "-r", str(manifest.resolve()),
    ], cwd=environment.parent, env=env, check=True)
    subprocess.run(
        [str(interpreter), "-m", "pip", "check"],
        cwd=environment.parent, env=env, check=True,
    )
    smoke = source_tree / "scripts" / "smoke_installed_distribution.py"
    if not smoke.is_file():
        raise ValueError(f"installed-package smoke missing: {smoke}")
    subprocess.run(
        [str(interpreter), str(smoke)],
        cwd=environment.parent, env=env, check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify released wheel bytes and smoke offline dependency resolution"
    )
    parser.add_argument("--wheelhouse", required=True, type=Path)
    parser.add_argument("--source-tree", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    manifest: Path = args.manifest
    hashes = write_hash_manifest(args.wheelhouse, manifest)
    print(f"Verified {len(hashes)} real local wheel SHA256 digests", flush=True)
    verify_installed_wheels(
        args.source_tree, manifest, manifest.parent / "offline-venv",
        wheelhouse=args.wheelhouse,
    )
    print("Installed ORAEC-TF and tf-build wheel smoke succeeded offline", flush=True)


if __name__ == "__main__":
    main()
