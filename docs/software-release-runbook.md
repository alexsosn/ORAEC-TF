# ORAEC-TF 0.1.0rc1: software release operator runbook

This is an **operator procedure**, not a claim that a release exists. As of
2026-11-15, `v0.1.0rc1` is **not tagged or published**. Parent issue [#12](https://github.com/alexsosn/ORAEC-TF/issues/12)
remains open until an independently verified software release exists.
The public consumer check is [#106](https://github.com/alexsosn/ORAEC-TF/issues/106).

The release contains **no ORAEC source data**, generated Text-Fabric corpus, or
compiled Context-Fabric caches. Its only assets are:

- `oraec_tf-0.1.0rc1-py3-none-any.whl`
- `oraec_tf-0.1.0rc1.tar.gz`
- `release-manifest.json` (SHA256 digests, sizes and source commit)

The converter software is MIT licensed; upstream texts retain their own terms
(`LICENSE_SCOPE.md`). Do not publish source JSON, mapping TSVs or generated
`.tf` files under the software release. `CITATION.cff` records how to cite
the software; citing it does not change source-text permissions.

## 1. Freeze an exact main source commit

Run in a **single Bash session** with a GitHub CLI (`gh`) account authorized
to publish in this repository and a clean checkout. Later commands reuse the
`REPO` and `SHA` variables established here. **Do not reuse old PR-head or earlier main
checks after any later commit.** These commands work from the repository root:

```bash
set -euo pipefail
REPO=alexsosn/ORAEC-TF
git fetch origin main
git switch main
git merge --ff-only origin/main
SHA="$(git rev-parse HEAD)"
test "$SHA" = "$(git rev-parse origin/main)"
printf 'Planned immutable software release SHA: %s\n' "$SHA"
```

The current software version must be `0.1.0rc1` in
`pyproject.toml`, and the required release tag will be `v0.1.0rc1`.
If that tag or GitHub Release already exists, **stop**; do not retag,
force-push or overwrite it.

## 2. Run the final full-corpus gates on that SHA

The `ci.yml` **push** run on main must be green at the exact SHA.
After main has stabilized, manually dispatch each independent full-source
gate. The release workflow specifically requires a successful
`workflow_dispatch` event at the final SHA for all three:

```bash
gh workflow run writer-validation.yml --ref main --repo "$REPO"
gh workflow run release-rehearsal.yml --ref main --repo "$REPO"
gh workflow run agora-materializer.yml --ref main --repo "$REPO"
```

These run expensive pinned 13,026-text checks, including source→TF conservation,
a wheel-installed researcher E2E with browser HTTP and the Agora materializer.
They upload only small reports, not the source or generated corpus.
Review the individual run logs and use `gh run view` to inspect each run:

```bash
gh run list --repo "$REPO" --workflow release-rehearsal.yml --event workflow_dispatch --limit 10
# Then inspect a real ID from the listing:
gh run view RUN_ID --repo "$REPO" --json headSha,event,status,conclusion
```

**Require the exact SHA, event, completed state and success for each workflow.**
The following is a machine-checkable equivalent of the gate in
`software-release.yml` (all four checks must print a count of at least one):

```bash
for pair in \
  "ci.yml:push" \
  "writer-validation.yml:workflow_dispatch" \
  "release-rehearsal.yml:workflow_dispatch" \
  "agora-materializer.yml:workflow_dispatch"; do
  workflow="${pair%:*}"
  event="${pair#*:}"
  count="$(gh api "repos/$REPO/actions/workflows/$workflow/runs?head_sha=$SHA&event=$event&per_page=100" |
    jq --arg sha "$SHA" --arg event "$event"       '[.workflow_runs[] | select(.head_sha == $sha and .event == $event and .status == "completed" and .conclusion == "success")] | length')"
  test "$count" -ge 1 || {
    echo "Missing successful exact-head run: $workflow / $event" >&2
    exit 1
  }
done
git fetch origin main
test "$SHA" = "$(git rev-parse origin/main)" || {
  echo "main changed; restart the final SHA acceptance sequence" >&2
  exit 1
}
```

A stale check from a PR merge commit or earlier main head does **not** qualify.
A failed, cancelled, queued or skipped workflow does **not** qualify. If main
moves, repeat all checks at the new SHA rather than making the tag point backward.

## 3. Create one immutable tag and dispatch the guarded release

Only after the exact-SHA checks have passed, create the tag on the same head.
Never silently move a pre-existing tag:

```bash
set -euo pipefail
git fetch origin main
test "$SHA" = "$(git rev-parse HEAD)"
test "$SHA" = "$(git rev-parse origin/main)"
# Local tag must not be overwritten, either.
if git rev-parse --quiet --verify refs/tags/v0.1.0rc1 >/dev/null; then
  echo "Local tag already exists: stop and inspect it" >&2
  exit 1
fi
# A remote/network/auth failure aborts under set -e. Missing tags return empty output.
remote_tag="$(git ls-remote --refs origin refs/tags/v0.1.0rc1)"
test -z "$remote_tag" || {
  echo "Remote tag already exists: stop and inspect it" >&2
  exit 1
}
git tag -a v0.1.0rc1 "$SHA" -m "ORAEC-TF v0.1.0rc1 software-only prerelease"
git push origin refs/tags/v0.1.0rc1
gh workflow run software-release.yml --ref main -f tag=v0.1.0rc1 --repo "$REPO"
```

The `git ls-remote` check must succeed; a network or authentication error
aborts the procedure rather than being interpreted as an absent tag.
The GitHub Actions `release` environment may require an explicit approval.
The publication job checks that the source SHA, current main HEAD and remote tag
still match. It refuses existing releases and uploads only the three files
listed above. It does not create tags, and PR events never publish.

## 4. Independently check the published bytes before calling #12 complete

Do this **only after** the release job succeeds and
`gh release view v0.1.0rc1 --repo "$REPO"` confirms a published prerelease.
Use an empty destination directory:

```bash
mkdir -p build/published-release-check
gh release download v0.1.0rc1 --repo "$REPO" \
  --dir build/published-release-check \
  --pattern 'oraec_tf-0.1.0rc1-py3-none-any.whl' \
  --pattern 'oraec_tf-0.1.0rc1.tar.gz' \
  --pattern 'release-manifest.json'
python scripts/verify_release_assets.py \
  --verify-staged build/published-release-check \
  --manifest build/published-release-check/release-manifest.json \
  --revision "$SHA"
```

The verifier rejects unexpected files, wrong revision and SHA256/size mismatch,
and audits the two archives for non-software members. Those downloaded bytes
must be independently installed in a fresh isolated environment and checked
with `oraec-tf source-info`, `oraec-tf app-path`, native TF and hieroglyphic
smoke per [#106](https://github.com/alexsosn/ORAEC-TF/issues/106).
The published ORAEC package is **not** a published Text-Fabric dataset.
Do not close #12 until this post-publication consumer gate is recorded.
