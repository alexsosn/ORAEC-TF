# Research: fail-closed GitHub release lookup (#111)

Date: 2026-11-16. Parent #12. Inspected `.github/workflows/software-release.yml` on main `adfb9bbab0003fd80984cf09e73f3c5d55af3c38`.

The publish job first verifies exact source/tag/main SHA, requires successful exact-head CI and manual full E2E events, and uploads precisely wheel/sdist/manifest. The final existence guard is currently:

```bash
if gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
  echo "Release already exists: refusing to overwrite" >&2
  exit 1
fi
```

Every error path is interpreted as absence, including authentication failure, API rate limiting, HTTP 5xx, network/transport failures. The later create call may fail anyway, but may not be attempted after an ambiguous lookup.

GitHub REST API docs: `GET /repos/{owner}/{repo}/releases/tags/{tag}` specifies `200 OK` and `404 Resource not found` for an authenticated release-by-tag read. Source: https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name (checked 2026-11-16). For this repository, the only acceptable outcome permitting publication is **HTTP 404 from a successfully completed HTTP request**. HTTP 200 means already released; other statuses are errors, not evidence of absence.

Design choice: a short, bounded `curl` call using existing `GH_TOKEN` and GitHub Actions' Ubuntu runner, with `--write-out '%{http_code}'`. `set -e` must abort on curl transport errors. Classify exact status with `case`; do not parse locale-dependent gh CLI diagnostic text. Test the real shell step with fake curl/gh executables so no network or release mutation is possible. No new runtime dependency or Python API helper needed.
