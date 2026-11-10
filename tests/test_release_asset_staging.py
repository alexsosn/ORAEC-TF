"""RED-first contracts for release-asset staging (#104): synthetic untrusted archives."""

from __future__ import annotations

import io
import json
import tarfile
import zipfile
from pathlib import Path
from runpy import run_path
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0rc1"
REVISION = "a" * 40


def _wheel(directory: Path, *, modified: bool = False, extra: str | None = None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    wheel = directory / f"oraec_tf-{VERSION}-py3-none-any.whl"
    members = {
        "oraec_tf/__init__.py": b"__version__ = '0.1.0rc1'",
        "oraec_tf/schema_core.json": b"{}" if not modified else b'{"changed":1}',
        "oraec_tf/tf_app/config.yaml": b"apiVersion: 3",
        f"oraec_tf-{VERSION}.dist-info/METADATA": (
            b"Metadata-Version: 2.1\nName: oraec-tf\nVersion: 0.1.0rc1\n"
        ),
        f"oraec_tf-{VERSION}.dist-info/WHEEL": b"Wheel-Version: 1.0\n",
        f"oraec_tf-{VERSION}.dist-info/RECORD": b"",
    }
    if extra:
        members[extra] = b"raw corpus"
    with zipfile.ZipFile(wheel, "w") as archive:
        for path, value in members.items():
            archive.writestr(path, value)
    return wheel


def _sdist(directory: Path, *, extra: str | None = None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / f"oraec_tf-{VERSION}.tar.gz"
    members = [
        "pyproject.toml",
        "schema/core.json",
        "src/oraec_tf/__init__.py",
        "src/oraec_tf/tf_app/config.yaml",
    ]
    if extra:
        members.append(extra)
    with tarfile.open(source, "w:gz") as archive:
        for path in members:
            payload = b"software"
            item = tarfile.TarInfo(f"oraec_tf-{VERSION}/{path}")
            item.size = len(payload)
            archive.addfile(item, io.BytesIO(payload))
    return source


def _verify(
    wheel: Path, source: Path, rebuilt: Path, out: Path,
    revision: str = REVISION,
) -> dict[str, object]:
    module = run_path(str(ROOT / "scripts/verify_release_assets.py"))
    return cast(dict[str, object], module["verify_release_assets"](
        wheel, source, rebuilt, revision=revision, manifest=out,
    ))


def test_release_manifest_matches_real_archive_bytes(tmp_path: Path) -> None:
    direct = _wheel(tmp_path / "direct")
    rebuilt = _wheel(tmp_path / "rebuilt")
    source = _sdist(tmp_path / "sdist")
    out = tmp_path / "release-manifest.json"
    report = _verify(direct, source, rebuilt, out)
    assert report == json.loads(out.read_text(encoding="utf-8"))
    assert report["version"] == VERSION
    assert report["source_revision"] == REVISION
    assert report["format"] == "oraec-software-release-assets-v1"
    artifacts = cast(list[dict[str, Any]], report["artifacts"])
    assert {a["name"] for a in artifacts} == {direct.name, source.name}
    assert all(len(a["sha256"]) == 64 for a in artifacts)
    assert all(a["size"] > 0 for a in artifacts)


def test_release_rejects_sdist_rebuilt_wheel_with_changed_schema(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="payload"):
        _verify(
            _wheel(tmp_path / "direct"),
            _sdist(tmp_path / "sdist"),
            _wheel(tmp_path / "rebuilt", modified=True),
            tmp_path / "manifest.json",
        )
    assert not (tmp_path / "manifest.json").exists()


@pytest.mark.parametrize("archive_kind", ["wheel", "sdist"])
def test_release_rejects_hidden_raw_corpus(
    tmp_path: Path, archive_kind: str,
) -> None:
    wheel = _wheel(
        tmp_path / "direct", extra="oraec_tf/oraec1.json" if archive_kind == "wheel" else None,
    )
    sdist = _sdist(
        tmp_path / "sdist", extra="oraec1.json" if archive_kind == "sdist" else None,
    )
    with pytest.raises(ValueError):
        _verify(wheel, sdist, _wheel(tmp_path / "rebuilt"), tmp_path / "manifest.json")


def test_release_rejects_wrong_revision_and_version(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path / "direct")
    source = _sdist(tmp_path / "sdist")
    rebuilt = _wheel(tmp_path / "rebuilt")
    with pytest.raises(ValueError):
        _verify(wheel, source, rebuilt, tmp_path / "manifest.json", revision="main")
    bad = wheel.rename(wheel.with_name("oraec_tf-0.1.0.dev0-py3-none-any.whl"))
    with pytest.raises(ValueError, match="version|name"):
        _verify(bad, source, rebuilt, tmp_path / "manifest.json")


def test_release_workflow_never_publishes_on_pull_request() -> None:
    workflow = (ROOT / ".github/workflows/software-release.yml").read_text(
        encoding="utf-8"
    )
    assert "workflow_dispatch:" in workflow
    assert "pull_request:" in workflow
    assert "audit_software_release.py" in workflow or "verify_release_assets.py" in workflow
    assert "verify_release_assets.py" in workflow
    assert "wheel-manifest.json" in workflow or "release-manifest.json" in workflow
    assert "--verify-tag" in workflow
    assert "gh release create" in workflow
    assert "contents: write" in workflow
    assert "event_name == 'workflow_dispatch'" in workflow
    assert "tf-build" not in workflow.split("gh release create", 1)[1].split("\n", 1)[0]
    assert "git tag" not in workflow
    assert "git push" not in workflow
