from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

from oraec_tf.cli import main
from oraec_tf.source import DEFAULT_SOURCE_REVISION, SOURCE_REPOSITORY


def test_source_info_reports_reproducible_default() -> None:
    output = StringIO()
    with patch("sys.stdout", output):
        assert main(["source-info"]) == 0

    payload = json.loads(output.getvalue())
    assert payload == {
        "repository": SOURCE_REPOSITORY,
        "revision": DEFAULT_SOURCE_REVISION,
    }
