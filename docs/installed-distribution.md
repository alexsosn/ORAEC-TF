# Source-built wheelhouse installation gate (ORAEC issue #59)

**Status: developer smoke only, not a distributed offline release.**
The current immutable `tf-build` dependency is the Git commit
`da7ff9618259f1669bdb89b134970399919accc0`, package version
`0.1.0.dev0`. There is currently no verified public tf-build release
wheel/tag/asset that can be downloaded independently of Git; upstream
[tf-build issue #60](https://github.com/alexsosn/tf-build/issues/60)
tracks a source-matched published distribution, stable version, and SHA-256.

The exact working boundary is:

1. **Online source preparation** — Git and network *are available*. The
   immutable VCS dependency and PyPI runtime dependencies are acquired.
   `python -m pip wheel --wheel-dir "$RUNNER_TEMP/wheelhouse" .`
   creates local runtime wheels including ORAEC-TF and tf-build. Their actual
   bytes are hashed with SHA-256 and listed in `wheel-manifest.txt`.
2. **Offline wheelhouse installation** — an isolated, previously empty venv
   installs **only the captured local wheel files** using
   `pip --no-index --no-deps --require-hashes`. `--no-deps` prevents
   re-resolution of ORAEC's embedded direct-VCS dependency while the complete
   prior wheelhouse contains its runtime dependency distribution and all
   transitive requirements. `pip check` verifies the resulting environment's
   declared dependency compatibility. Neither an editable package nor a Git
   source checkout is used for imports.
3. **Installed-package functionality** — from a working directory outside
   the repository, with PATH restricted to the venv bin directory, the smoke
   validates installed `oraec_tf` and `tf_build` import paths and versions,
   the public `oraec-tf source-info` CLI, a *newly generated synthetic*
   Egyptian native TF graph, original Unicode reconstruction using
   `NativeCRIndex`, and the genuine cross-platform no-clobber publisher.

The wheelhouse manifest is a record of **this particular CI job**, not an
immutable cross-machine dependency lock. Wheels are *not uploaded* as CI
artifacts or silently treated as an official release. Every offline install
must first acquire its wheels in another trusted step. `--no-index` and
`--require-hashes` prevent pip from fetching package indexes in the offline
phase, and the smoke PATH excludes system Git. This is not a kernel-enforced
network sandbox; the downstream Agora host must independently enforce
`execution.network: deny` during converter execution.

The standard Text-Fabric advanced app under `app/` is repository-managed and
is **not** part of the Python wheel smoke. App/browser offline discovery and
the full 13,026-text source conservation remain separate release checks.

**Release blockers remain:** a published, immutable, hash-verified compatible
`tf-build` software wheel (upstream tf-build #60); reproducible wheelhouse
locking/availability for each supported platform; a truly independent cold
install without a VCS resolver; and ORAEC-TF's full #12 release and downstream
Agora #224 gates. Keep #59 open until those are verified, even when this
developer CI job succeeds.
