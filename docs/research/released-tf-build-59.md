# Published tf-build dependency: issue #59

2026-10-28. The published `tf-build` prerelease `v0.1.0rc1` is built from
`65a3bbb42a238f2cd59931cca79ee01560fdd887`. Its actual wheel is
`tf_build-0.1.0rc1-py3-none-any.whl`, SHA-256
`dff2a14c0299422b4716217d04e6d43b47e714f4dacdb21d9939292051e82c9a`.
The release workflow succeeded, downloaded wheel/sdist hashes match its manifest,
and a clean installed-wheel native TF publication/query test passed.
Release: https://github.com/alexsosn/tf-build/releases/tag/v0.1.0rc1

ORAEC currently embeds a VCS URL in Requires-Dist. Its wheelhouse verifier
intentionally disables dependency resolution with `--no-deps`, validates the old
development source/version, and emits absolute file URLs. This cannot prove an
ordinary offline dependency-resolving installation or support moving the prepared
wheelhouse to another computer. Package metadata must use an exact version;
online acquisition must separately select and hash-check the published wheel.

PR #96 has now merged after independent exact-head review and green full-source,
Linux/Windows installed-app, and Python matrix checks. Its installed app and
synthetic native TF checks can be reused without duplicating graph/browser logic.

Keep runtime versions and allowed hashes in a checked-in lock. Acquire binary
dependencies under that lock for each target interpreter/platform, then build
only ORAEC locally. Generate a portable complete installation manifest containing
exact package versions and actual local wheel hashes. Offline pip must resolve
dependencies normally using only the supplied wheelhouse; missing/incompatible
dependencies and changed published tf-build bytes must fail. A lock can include
multiple platform wheel hashes; it does not mean one wheelhouse works everywhere.
