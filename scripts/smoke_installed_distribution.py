"""Noneditable installed-wheel smoke for release packaging issue #59.

Run this script with a *fresh offline-installed virtualenv* whose packages came
only from a pre-acquired wheelhouse. It needs no Git, network, ORAEC source
checkout, or generated corpus files; it tests a small synthetic native graph.

This does NOT establish a published hash-locked tf-build wheel release.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

PINNED_SOURCE = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


def verify_installed_modules() -> dict[str, str]:
    """Reject a source-checkout import masquerading as a wheel install."""
    import tf_build
    from tf_build.publication import publish_path_no_clobber

    import oraec_tf

    assert callable(publish_path_no_clobber)
    if shutil.which("git") is not None:
        raise AssertionError("Git executable is visible during offline installed smoke")
    source_tree = Path(os.environ["ORAEC_SOURCE_TREE"]).resolve()
    environment = Path(sys.prefix).resolve()
    versions: dict[str, str] = {}
    for distribution, package in (("oraec-tf", oraec_tf), ("tf-build", tf_build)):
        installed_file = package.__file__
        if installed_file is None:
            raise AssertionError(f"{distribution} has no concrete installed module")
        path = Path(installed_file).resolve()
        if path.is_relative_to(source_tree):
            raise AssertionError(f"{distribution} imported from editable checkout: {path}")
        if not path.is_relative_to(environment):
            raise AssertionError(f"{distribution} imported outside wheel venv: {path}")
        versions[distribution] = version(distribution)
    assert versions["oraec-tf"] == "0.1.0.dev0"
    assert versions["tf-build"] == "0.1.0.dev0"
    entrypoint = shutil.which("oraec-tf")
    if not entrypoint:
        raise AssertionError("oraec-tf console entrypoint missing from installed wheel")
    cli = subprocess.run(
        [entrypoint, "source-info"], capture_output=True, text=True, check=True
    )
    assert json.loads(cli.stdout)["revision"] == PINNED_SOURCE
    return versions


def verify_native_tf() -> dict[str, int]:
    """Actually write, read and reconstruct native Text-Fabric schema v3."""
    from tf.fabric import Fabric

    from oraec_tf.ir import CreditsIR, SentenceIR, TextIR, TokenIR
    from oraec_tf.text_codec import NativeCRIndex
    from oraec_tf.writer import write_tf

    record = TextIR(
        oraec_id="oraec1",
        title="Wheel-only Egyptian corpus",
        bibliography="Original\r\nsource\rstring",
        credits=CreditsIR(
            license="cc-by-sa-4.0",
            author="Offline tester",
            sources=("https://example.invalid/provenance",),
        ),
        sentences=(
            SentenceIR(
                index=1,
                translation="test",
                tokens=(
                    TokenIR(
                        token_id="oraec1-1-1",
                        written_form="nṯr",
                        hiero="𓀀[⯑]�",
                        pos="substantive",
                    ),
                ),
            ),
        ),
    )
    with tempfile.TemporaryDirectory(prefix="oraec-installed-wheel-") as d:
        tf_dir = Path(d) / "tf"
        write_tf((record,), tf_dir, source_revision=PINNED_SOURCE)
        api = Fabric(locations=str(tf_dir), silent="deep").loadAll(silent="deep")
        if not api:
            raise AssertionError("installed distribution could not reload TF")
        assert len(api.F.otype.s("word")) == 1
        assert len(api.F.otype.s("text")) == 1
        assert len(api.F.otype.s("cr_occurrence")) == 2
        text = api.F.otype.s("text")[0]
        word = api.F.otype.s("word")[0]
        assert NativeCRIndex(api).restore(text, "bibliography") == record.bibliography
        assert api.F.bibliography.v(text) == "Original\nsourcestring"
        assert api.F.hiero.v(word) == "𓀀[⯑]�"
        assert api.T.nodeFromSection(("oraec1", 1)) in api.F.otype.s("sentence")
        return {"texts": 1, "source_tokens": 1, "cr_occurrences": 2}


def verify_no_clobber() -> None:
    """Exercise tf-build's public atomic primitive on real filesystem inodes."""
    from tf_build.publication import publish_path_no_clobber

    with tempfile.TemporaryDirectory(prefix="oraec-publish-contract-") as d:
        root = Path(d)
        staged = root / "staged"
        staged.mkdir()
        (staged / "marker").write_text("candidate", encoding="utf-8")
        rival = root / "published"
        rival.mkdir()
        initial = (rival.stat().st_dev, rival.stat().st_ino)
        try:
            publish_path_no_clobber(staged, rival)
        except FileExistsError:
            pass
        else:
            raise AssertionError("published wheel overwrote an empty rival directory")
        assert (rival.stat().st_dev, rival.stat().st_ino) == initial
        assert staged.joinpath("marker").is_file()


def main() -> None:
    versions = verify_installed_modules()
    graph = verify_native_tf()
    verify_no_clobber()
    print(json.dumps({"ok": True, "installed_versions": versions, "graph": graph}))


if __name__ == "__main__":
    main()
