# Published-wheel offline installation (ORAEC issue #59)

ORAEC package metadata requires `tf-build==0.1.0rc1`. The independently published
[tf-build prerelease](https://github.com/alexsosn/tf-build/releases/tag/v0.1.0rc1)
is built from `65a3bbb42a238f2cd59931cca79ee01560fdd887`.
Its pure-Python wheel SHA-256 is
`dff2a14c0299422b4716217d04e6d43b47e714f4dacdb21d9939292051e82c9a`.
See upstream [tf-build #60](https://github.com/alexsosn/tf-build/issues/60) and
ORAEC-TF issue #59. This is a release candidate, with experimental upstream APIs.

## Prepare on the target platform, with network access

Use Python 3.11–3.13. From the reviewed ORAEC software checkout:

```bash
python -m pip download --no-deps --dest build/wheelhouse -r requirements/tf-build.txt
python -m pip download --only-binary=:all: --require-hashes --find-links build/wheelhouse --dest build/wheelhouse -r requirements/runtime.lock
python -m pip wheel --no-deps --wheel-dir build/wheelhouse .
python scripts/validate_wheelhouse_install.py --wheelhouse build/wheelhouse --source-tree . --manifest build/wheel-manifest.txt
```

The first command retrieves the real release wheel and verifies its hash fragment.
The second resolves the checked-in exact runtime versions and allowed hashes for
this interpreter/OS. The third builds only ORAEC software; PEP 517 build tools may
be acquired online. No tf-build source checkout or replacement build is used.
Use a fresh wheelhouse and manifest directory for each run. The verifier refuses
an existing `offline-venv` directory rather than silently reusing an environment.

`requirements/runtime.lock` fixes versions and allowed distribution hashes,
including platform-dependent wheels and conditional requirements. It does not
make one platform's wheelhouse suitable for another. Linux and Windows CI run
these commands independently on Python 3.12. Other interpreter/platform variants
need their own acquisition and installation check before claiming support for a
particular offline wheelhouse. ORAEC's normal Python 3.11–3.13 CI remains separate.

The runtime lock was generated with `uv pip compile --python-version 3.11
--universal --generate-hashes --no-annotate --no-header requirements/runtime.in`,
with the verified release wheel supplied as a local `--find-links` directory.
Review version and hash changes before regenerating it.

## What the offline phase proves

The verifier checks the downloaded tf-build bytes against the published digest,
checks ORAEC's wheel METADATA for the exact version requirement, and emits a
portable complete installation manifest of `name==version --hash=sha256:...`.
It creates a new venv outside package source imports, removes Git from PATH,
disables indexes and pip's cache, and runs **normal dependency resolution**:

```bash
python -m pip install --no-index --no-cache-dir --only-binary=:all: --require-hashes --find-links build/wheelhouse -r build/wheel-manifest.txt
```

This command is illustrative: the verifier invokes the new venv's absolute
interpreter with resolved manifest/wheelhouse paths. There is no `--no-deps`
bypass. A missing transitive dependency fails; pip checks installed compatibility.
The manifest and wheels can be relocated together because the manifest contains
no machine-specific absolute file URLs.

The installed smoke exercises the public `oraec-tf source-info` and `app-path`
CLI, verifies imports/resources inside the wheel venv, writes and reloads a small
synthetic native TF graph, reconstructs original CR and Unicode values, renders
hieroglyphs through the installed standard app, and checks no-clobber publication.
No ORAEC source corpus or generated TF is bundled or uploaded. CI uploads only
the portable version/hash manifest for each platform, not wheel payloads.

`--no-index` is pip configuration, not a kernel network sandbox. It and the
local-only wheel requirements prevent dependency fetching in this phase;
Agora's execution network enforcement remains a separate host responsibility.

## Remaining release scope

A prepared wheelhouse is not a published ORAEC software release. Full pinned
13,026-text source conservation, standard browser checks, independent final-head
review and the software-only release remain gated by #12. Downstream Agora #224
is separate. Karnak-bearing source/TF data are never distributed by this process.
