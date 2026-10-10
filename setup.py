"""Copy the canonical frozen schema into built wheels; no tracked duplicate.

Editable checkouts continue to read schema/core.json directly.  Normal wheels
contain its build-time copy as oraec_tf/schema_core.json, keeping one canonical
schema source in version control.
"""

from pathlib import Path
from shutil import copyfile

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithSchema(build_py):
    def run(self) -> None:
        super().run()
        source = Path(__file__).resolve().parent / "schema" / "core.json"
        destination = Path(self.build_lib) / "oraec_tf" / "schema_core.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        copyfile(source, destination)


setup(cmdclass={"build_py": BuildWithSchema})
