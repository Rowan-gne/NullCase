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

## Current status

Bootstrapping. No product code yet. See docs/technical-guide.md for the
full six-week plan; this repo currently covers none of it.
