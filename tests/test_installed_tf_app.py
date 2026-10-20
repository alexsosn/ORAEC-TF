"""RED-first: a noneditable ORAEC wheel must include its standard TF app (#95)."""

from __future__ import annotations

from pathlib import Path

from oraec_tf.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_cli_prints_real_installed_app_directory(capsys: object) -> None:
    from contextlib import redirect_stdout
    from io import StringIO

    out = StringIO()
    with redirect_stdout(out):
        assert main(["app-path"]) == 0
    target = Path(out.getvalue().strip())
    assert target.is_absolute()
    assert (target / "config.yaml").is_file()
    assert target.name == "tf_app"
    assert (target / "config.yaml").read_bytes() == (
        ROOT / "app/config.yaml"
    ).read_bytes()


def test_explicit_resource_in_wheel_and_no_corpus_payload() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '[tool.setuptools.package-data]' in project
    assert '"tf_app/config.yaml"' in project
    package_app = ROOT / "src/oraec_tf/tf_app/config.yaml"
    assert package_app.is_file()
    assert package_app.read_bytes() == (ROOT / "app/config.yaml").read_bytes()
    assert not (package_app.parent / "otype.tf").exists()
    assert not (package_app.parent / "oraec1.json").exists()


def test_installed_wheel_smoke_must_verify_real_app_after_clean_install() -> None:
    script = (ROOT / "scripts/smoke_installed_distribution.py").read_text(
        encoding="utf-8"
    )
    assert "verify_installed_app" in script
    assert '["app-path"]' in script
    assert "findAppConfig" in script
    assert "APP_DIR" not in script
