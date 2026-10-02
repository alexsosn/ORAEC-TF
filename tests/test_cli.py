from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from oraec_tf.cli import main
from oraec_tf.source import (
    DEFAULT_SOURCE_REVISION,
    SOURCE_REPOSITORY,
    SourceSnapshot,
)


def test_source_info_reports_reproducible_default() -> None:
    output = StringIO()
    with patch("sys.stdout", output):
        assert main(["source-info"]) == 0

    payload = json.loads(output.getvalue())
    assert payload == {
        "repository": SOURCE_REPOSITORY,
        "revision": DEFAULT_SOURCE_REVISION,
    }


def test_verify_source_cli_uses_same_identity_contract() -> None:
    output = StringIO()
    snapshot = SourceSnapshot(
        path=Path("/verified/source"),
        revision=DEFAULT_SOURCE_REVISION,
    )

    with (
        patch("oraec_tf.cli.verify_source", return_value=snapshot) as verify,
        patch("sys.stdout", output),
    ):
        assert (
            main(
                [
                    "verify-source",
                    "/candidate/source",
                    "--revision",
                    DEFAULT_SOURCE_REVISION,
                ]
            )
            == 0
        )

    verify.assert_called_once_with(
        "/candidate/source",
        expected_revision=DEFAULT_SOURCE_REVISION,
    )
    assert json.loads(output.getvalue()) == {
        "path": "/verified/source",
        "revision": DEFAULT_SOURCE_REVISION,
    }
