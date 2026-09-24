# NullCase — Project Instructions for Claude Code

Read this file at the start of every session before doing anything else.
Full architecture and design rationale: docs/technical-guide.md — read
the relevant section before implementing anything it covers. This file
is rules and current status only; it does not repeat that document.

## Non-negotiable rules

1. Check `git config user.name` and `git config user.email` before making
   any commit. If either is empty, stop and ask — never commit under a
   placeholder identity.
2. Never write AI/Claude/Anthropic attribution anywhere: not in commit
   messages, PR descriptions, code comments, or file headers. No
   "Generated with Claude Code," no "Co-Authored-By: Claude," no
   "Claude-Session" links. .claude/settings.json enforces this at the
   tool level — do not override or work around it.
3. Commit early and often: one logical unit of work per commit, plain
   conventional messages (feat:, fix:, test:, docs:, chore:). Never one
   giant commit for a multi-part change.
4. Never invent numbers, users, claims, or "done" status in the README,
   comments, or commit messages. If something isn't built or tested,
   say so.
5. Never commit secrets, tokens, or a real .env file — only .env.example
   with placeholder values.
6. This repo is the public, open-core portion of NullCase only. Do not
   start the FastAPI backend, Postgres schema, GitHub App, Stripe
   integration, Fly deployment, or Next.js dashboard here — those live
   in a separate private repo.

> **Note on docs/technical-guide.md:** §6.2 describes a single monorepo
> containing apps/api, apps/worker, apps/web, packages/core, and infra/
> alongside the public pieces. That reflects an earlier plan. This
> repository holds only the public, open-core subset: packages/pytest-
> plugin, sandbox/, eval/, and (later) packages/upload-action. Everywhere
> else in the document, treat the architecture, data model, and design
> rationale as authoritative — only §6.2's *file layout* has been
> superseded by this split.

## Current status

The public, open-core components exist and run locally. packages/pytest-plugin
records per-test results to local JSON Lines. sandbox/ holds the experiment
battery (baseline, order, hash-seed, network-off, timezone and parallel
perturbations, a Wilson-interval diagnosis, confirmed repro commands, and a
Dockerfile) plus a single-test coverage check for target lines. The eval
harness in eval/ scores the battery against six seeded demo tests: 6 of 6
now, 5 of 6 originally. The hash-order miss (the pinned PYTHONHASHSEED=0
baseline failed every run and the Wilson intervals overlapped) was fixed on
the user's explicit instruction by adding a deterministic-flip check. Because
that fix came after seeing the miss, the README says 6/6 isn't independent
evidence; keep that caveat, and don't tune the method or eval/ further to
move the score. packages/retrieval
builds a local `ast` import graph and ranks tests that import a target module.
packages/upload-action wraps the plugin as a composite GitHub Action, but it
hasn't run on a real Actions runner. Stubbed until a backend exists:
remote upload (RemoteUploadSink and the action's upload step), the quarantine
list (always empty), retrieval's pgvector embedding fallback, and any
AI-generated fixes or tests (there is no LLM layer here). Release prep for 0.1.0
is in place (release.yml with PyPI Trusted Publishing, a stand-alone
upload-action export, RELEASING.md), but nothing has been tagged or
published, and PyPI/Marketplace setup is still the user's to do. This is the last
public-repo work before the wall; the backend, GitHub App, billing,
deployment and dashboard belong in the private repo (rule 6).
