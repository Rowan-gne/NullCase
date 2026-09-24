# Releasing

Covers the three PyPI packages (`nullcase-pytest`, `nullcase-retrieval`,
`nullcase-sandbox`) and the stand-alone upload-action repository. None of
this has been done yet; the one-time setup steps need your PyPI and GitHub
accounts.

## One-time setup

1. **PyPI Trusted Publishing.** On pypi.org, add a *pending publisher* for
   each of the three project names with:
   owner `Rowan-gne`, repository `NullCase`, workflow `release.yml`,
   environment `pypi`. (Trusted Publishing needs no API token in the repo.)
2. **GitHub environment.** In this repo's settings, create an environment
   named `pypi`. Adding yourself as a required reviewer gives every publish a
   manual approval step.
3. **Account security.** 2FA on PyPI and GitHub (Marketplace publishing
   requires it on GitHub).
4. **Branch protection.** Protect `main` and require the CI checks to pass:
   `lint`, `test (3.11)` through `test (3.14)`, `test (lowest direct
   dependencies)`, `package`, `upload-action on a real runner` and `docker`.
5. **Private vulnerability reporting.** Turn it on under Settings → Code
   security. [SECURITY.md](SECURITY.md) points reporters there.
6. **Dependabot.** It's configured in `.github/dependabot.yml`. Review its
   weekly PRs; CI runs on each one.

## Releasing the packages

1. Update the version in all three `pyproject.toml` files and in
   `plugin-source`'s default in `packages/upload-action/action.yml`, then run
   `python3 scripts/check_versions.py`.
2. Move the `CHANGELOG.md` entry from "unreleased" to the release date.
3. Optional dry run: run the **Release** workflow manually from the Actions
   tab. It checks versions, runs the tests, builds, runs `twine check
   --strict` and smoke-tests the wheels, but doesn't publish. Locally:
   `uv build --package <name> --out-dir dist` for each package, then
   `python3 scripts/smoke_test_dist.py dist`.
4. Tag and push: `git tag v0.1.0 && git push origin v0.1.0`. The workflow
   checks that the tag matches every version, repeats the build job, then
   publishes from the `pypi` environment.
5. Check the three project pages on PyPI, then `pip install nullcase-sandbox`
   in a clean virtualenv.

## Releasing the upload action

Do this after `nullcase-pytest` is on PyPI: the action installs
`nullcase-pytest==<version>` by default, and its self-test depends on that.

1. Create an empty public repository for it (the name is your choice; the
   technical guide suggests `nullcase/upload-action` once a GitHub
   organisation exists).
2. `python3 scripts/export_upload_action.py ../upload-action-repo OWNER/REPO`
3. In the new directory: `git init`, commit, push. Its `self-test` workflow
   is the first run of the action from its own repository with the plugin
   installed from PyPI. This repo's CI already runs the action on a real
   runner, but with the plugin installed from the checkout. Check that it
   passes.
4. Create a release `v0.1.0` there and tick **Publish this Action to the
   GitHub Marketplace**. The action name ("NullCase test results") must be
   unique on the Marketplace; rename it in `action.yml` if it's taken. Also
   create or move a `v0` tag if you want users to pin a major version.
