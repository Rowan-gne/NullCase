# NullCase — Technical Guide for the MVP

*Stack research, setup, testing, deployment, hosting, and GitHub Marketplace distribution. Researched September 22, 2026. Anything marked **[verify]** is a fact likely to change — re-check it against the linked source before relying on it.*

---

## 0. MVP scope (lock this before writing code)

**In v1:**

- GitHub only, GitHub Actions only, Python only, pytest only.
- Repos installable with `pip`/`uv` from `requirements*.txt` or `pyproject.toml`, Python 3.11–3.13. Anything else is marked "unsupported" in the UI rather than half-handled.
- Flaky detection + quarantine + experiment-based diagnosis + AI fix PRs + AI tests for uncovered PR code, all behind one validation battery.
- Dashboard, Stripe billing, deployed service, free GitHub Marketplace listing.

**Explicitly deferred:** bulk test backfill, auto-merge, Slack/Jira, other CI providers, other languages, mutation testing (stretch goal only), self-hosting.

---

## 1. Architecture at a glance

```
                ┌──────────────── Customer's GitHub ────────────────┐
                │                                                   │
  pytest + nullcase plugin ──(JUnit XML via OIDC-authenticated upload)──┐
                │    ▲ fetches quarantine list                      │    │
                │    │                                              │    │
  GitHub App webhooks (workflow_run, pull_request, installation) ───┼──┐ │
                └───────────────────────────────────────────────────┘  │ │
                                                                       ▼ ▼
                                                  ┌──────────────────────────────┐
  Next.js dashboard ◄──── REST/JSON ───────────── │  FastAPI API (Fly.io)         │
  (Fly.io)                                        │  - webhook verify + enqueue   │
                                                  │  - result ingest              │
                                                  │  - auth, billing, dashboard   │
                                                  └──────────────┬───────────────┘
                                                                 │ jobs (Postgres queue)
                                                  ┌──────────────▼───────────────┐
                                                  │  Worker (Fly.io)              │
                                                  │  - backfill                    │
                                                  │  - flake scoring               │
                                                  │  - diagnosis orchestration     │
                                                  │  - LLM fix/generate            │
                                                  │  - PR creation, Stripe meters  │
                                                  └───────┬──────────────┬───────┘
                                                          │              │
                                          Fly Machines API│              │Anthropic API
                                                          ▼              ▼
                                         ┌──────────────────────┐   Claude models
                                         │ Ephemeral sandbox VM  │
                                         │ (Firecracker, no net) │
                                         │ runs experiment battery│
                                         └──────────────────────┘
                              Postgres + pgvector (Neon) ◄── API + worker
                              Sentry ◄── everything
```

Three deployable units — **api**, **worker**, **web** — plus a sandbox image and two small published packages (a pytest plugin and a GitHub Action).

---

## 2. Design review: changes from the original plan

These came out of a pre-build critique pass. Each one is a deliberate decision you should be able to defend in an interview.

| # | Original plan | Change | Why |
|---|---|---|---|
| 1 | Differentiator: "connect flaky diagnosis to AI fixes" | Differentiator: **evidence-first** — diagnose by controlled experiment; the same experiments gate every AI change | Trunk (beta), Datadog, and Bitbucket already ship flaky-to-fix-PR loops. Experiment-based diagnosis exists only as local open-source CLIs (whyflaky, pytest-flakedoctor, iPFlakies). See the justification document. |
| 2 | "Ingest CI run history" | Per-test results require **JUnit XML uploaded by a pytest plugin**; backfill is best-effort | The Actions API exposes runs, jobs, logs, and artifacts — not per-test outcomes. Backfill uses artifacts if present, log parsing otherwise, and the re-run signal (same commit, failed attempt then passed attempt). |
| 3 | Agentic flaky scoring | **Deterministic statistics** for detection; LLM only for explanation, fixes, and new tests | Detection must be reproducible and auditable. Using an LLM where arithmetic works is a thin-wrapper tell. |
| 4 | "Sandbox confirms the test passes" | Passing once is meaningless for flakiness. **Battery**: repeated runs + order, hash-seed, timezone, network-off, and parallel perturbations, plus a coverage check for new tests | A validator that can't detect flakiness would happily approve a new flaky test. |
| 5 | Docker sandbox | Docker (OCI) image run as an **ephemeral Fly Machine** (Firecracker microVM), no network egress, no secrets | Plain containers share a kernel; you are executing untrusted customer code plus AI-written code. |
| 6 | Airflow/Prefect ingestion | **Postgres-backed job queue** (Procrastinate); scheduled jobs via its periodic tasks | The workload is event-driven (webhooks), not batch ETL. One fewer service; transactional enqueue with your writes. |
| 7 | Embedding retrieval for style | **Import-graph retrieval first**, pgvector embeddings as tie-breaker | Tests that import the changed module are the best style examples; embeddings help when none exist. |
| 8 | Stripe "usage-metered" | **Stripe Billing Meters** specifically | Legacy usage records are deprecated. |
| 9 | "Add to GitHub Marketplace" | **Free** App listing + publish the uploader **Action**; charge via Stripe on your own site | Paid Marketplace plans require a verified publisher organization and at least 100 installations. |
| 10 | Quarantine mechanism unspecified | pytest plugin fetches the quarantine list at session start; quarantined failures don't fail the job but are still reported | No code changes in the customer repo, and results keep flowing so fixes can be verified. |
| 11 | Upload auth unspecified | **GitHub Actions OIDC tokens** — zero secrets for customers to configure | The backend verifies the token against GitHub's public keys and reads the `repository` claim. |
| 12 | No accuracy measurement | **Eval harness**: seeded demo repo + a published flaky-test dataset; precision/recall and diagnosis accuracy in the README | The number that makes an interviewer lean in. |

---

## 3. Stack selection with rationale

### 3.1 Backend: Python 3.12 + FastAPI

- The target language is Python, so the backend can parse customer code with the standard-library `ast` module (and `libcst` when you need to *rewrite* code preserving formatting).
- FastAPI gives typed request/response models via Pydantic — the same Pydantic models validate LLM structured output.
- Tooling: `uv` for dependency management, `ruff` for lint/format, `pyright` or `mypy` for types.

### 3.2 Database: PostgreSQL 16+ with pgvector, hosted on Neon

- **Why Postgres:** relational data (tenants, repos, runs, results) with strong constraints; `jsonb` for evidence blobs; pgvector for embeddings — one database instead of three.
- **Why Neon:** serverless Postgres with **branching**, which lets CI create a throwaway database branch per pull request. That's a genuine engineering talking point. pgvector is supported. A free plan exists **[verify]**.
- **Alternative:** Fly Managed Postgres, if you prefer everything on one vendor.
- **ORM/migrations:** SQLAlchemy 2.0 (async) + Alembic.

### 3.3 Job queue: Procrastinate

A Postgres-backed task queue for Python. Jobs are rows, so you can enqueue a job *in the same transaction* as the write that triggered it — no "row saved but job lost" bugs, and no Redis to operate. It supports periodic tasks for nightly re-scoring and retention housekeeping.

*Interview framing:* "I chose a Postgres queue because at this scale transactional enqueue matters more than throughput, and it removed a moving part. I'd move to a dedicated broker once job volume or latency needs justified it."

### 3.4 GitHub integration: a GitHub App (not an OAuth App)

- Fine-grained, per-repository permissions; short-lived installation tokens minted from the App's private key; webhooks built in.
- Python client: `githubkit` (typed, async) or `PyGithub`.
- **Permissions (least privilege):**
  - Repository: Actions **read**, Checks **write**, Contents **write** (to push fix branches), Pull requests **write**, Metadata **read**.
  - Account: none in v1.
- **Webhooks:** `installation`, `installation_repositories`, `workflow_run`, `pull_request`, `marketplace_purchase` (later).
- **Rate limits:** installation tokens get a per-hour request budget that scales with repo count **[verify in GitHub REST rate-limit docs]**. Backfill must be throttled and resumable.

### 3.5 Test-result collection: `nullcase-pytest` plugin + `nullcase/upload-action`

- The plugin wraps `pytest --junitxml`, adds metadata (run ID, attempt, SHA, runner OS, per-test duration), fetches the quarantine list, and uploads results.
- **Auth via GitHub Actions OIDC:** the workflow grants `permissions: id-token: write`; the plugin requests an OIDC token with audience `nullcase`; the API verifies signature, issuer, audience, and `repository` claim, then maps it to the installed repo. Customers configure no secrets.
- Pull requests from forks don't receive OIDC tokens; the plugin skips upload silently in that case, and the backfill path covers them later where possible.

### 3.6 Sandbox: ephemeral Fly Machines

- Fly runs every workload as a Firecracker microVM; `fly machine run --rm` (or the Machines API equivalent) destroys the machine when it stops, and boot is sub-second **[verify]**.
- Each validation job: create a machine from the sandbox image with the repo checked out at a specific SHA, dependencies installed, **no network egress after dependency install**, no secrets, CPU/memory/time limits. Run the battery; stream JUnit results back; destroy.
- **Dependency caching:** build a per-repo image layer keyed by a hash of the lockfile/requirements; rebuild only when that hash changes. This is the difference between 20-second and 3-minute validations.
- **Alternative:** E2B (purpose-built AI sandbox, very fast cold starts). Fly keeps you on one vendor; E2B is faster. Either is defensible; pick one and don't build an abstraction for both in v1.

### 3.7 Experiment battery (inside the sandbox)

| Perturbation | Tool / mechanism | Detects |
|---|---|---|
| Baseline repeats (isolated) | loop `pytest <nodeid>` N times | Pure nondeterminism, timing |
| Test order shuffle | `pytest-randomly` with varied seeds, run with its file/module | Order dependence / shared state |
| Hash randomization | vary `PYTHONHASHSEED` | Dict/set iteration order assumptions |
| Network blocked | `pytest-socket` (`--disable-socket`) | Hidden external calls |
| Timezone / clock | vary `TZ` (and `time-machine` for date edges, stretch) | Date/time assumptions |
| Parallel execution | `pytest-xdist -n 4` with siblings | Concurrency, shared files/ports |
| Coverage (new tests only) | `coverage.py` restricted to changed lines | Tests that don't actually exercise the new code |

**Diagnosis rule:** compare each perturbation's failure rate with the isolated baseline using an interval method (Wilson score intervals) or Fisher's exact test. The perturbation that moves the rate significantly is the category; produce a **deterministic repro command** when one exists. If nothing reproduces, label it "CI-environment only" and fall back to history features (runner OS, duration, time of day). Say so honestly in the UI — don't pretend.

**Acceptance rule for any AI-written test or fix:** zero failures across the whole battery (tune N in the eval phase; start with 20 baseline runs and 5 per perturbation), plus the coverage check for new tests.

### 3.8 LLM layer: Anthropic API

- **Fix and generation:** `claude-sonnet-5`. **Cheap summarization/classification of log text:** `claude-haiku-4-5-20251001`. **[verify current models and pricing at docs.claude.com]**
- **Structured output:** use tool definitions whose input schema mirrors a Pydantic model (e.g., `ProposedPatch { files: [{path, unified_diff}], rationale, expected_effect }`). Validate; on schema failure retry once with the validation error; then give up gracefully.
- **Repair loop:** max 3 attempts. Each retry includes the battery's evidence table from the previous attempt. If all fail, post the diagnosis and repro command without a patch — still useful.
- **Prompt injection:** repository contents are untrusted input. The model has **no tools that write anything**; its output is only a proposed diff, which is applied inside the sandbox and must pass the battery before a human sees it.
- **Cost guardrails:** per-tenant monthly token budget recorded in `usage_events`; cache per (test, SHA, evidence hash) so the same failure isn't re-fixed twice.

### 3.9 Retrieval

1. Build an import graph of the repo with `ast` (which test files import which modules).
2. For a target function, candidate examples = tests importing its module, ranked by name/path similarity.
3. If fewer than k candidates, fall back to pgvector nearest neighbors over embedded test functions.
4. **Embeddings:** run a small local model through `fastembed` (for example a 384-dimension BGE-small variant) inside the worker — no extra vendor, near-zero cost. Store in a `vector(384)` column with an HNSW index.

### 3.10 Frontend: Next.js (App Router) + TypeScript

- Tailwind + shadcn/ui components, Recharts for charts, TanStack Query for data fetching.
- Hosted on Fly alongside the backend. Note: Vercel's free Hobby plan is for non-commercial use **[verify]**; since you'll take payments, either use Fly or pay for Vercel Pro.
- **Pages:** Login → Installations/Repos → Repo overview (flaky rate trend, blocked-PR count, hours lost to re-runs, category breakdown) → Test detail (history sparkline, evidence table, repro command, linked PRs) → Proposals (open/merged/rejected) → Billing.

### 3.11 Auth

- "Sign in with GitHub" through the GitHub App's user authorization flow, handled by the **backend**; the backend sets an HTTP-only session cookie.
- On login, call the "installations for the authenticated user" endpoint and store memberships. Every API query filters by tenant.
- **Multi-tenancy:** shared schema with `account_id` on every tenant-owned table, **plus Postgres Row-Level Security** policies keyed on a per-request `SET LOCAL app.account_id`. Application bugs then fail closed rather than leaking data.

### 3.12 Billing: Stripe

- **Stripe Checkout** for subscribing, **Customer Portal** for managing, **Billing Meters** for usage. Legacy usage records are deprecated; meters report usage against the *customer*, not a subscription item.
- **Suggested early-access plan (placeholder):** public repos free; private repos a flat monthly base per repo plus a metered charge per *validated* proposal delivered. The meter event name is something like `validated_proposal`.
- **Webhooks:** `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`. Store every Stripe `event.id` in a `stripe_events` table with a unique constraint; skip duplicates (idempotency).
- **Meter events:** send with an `identifier` equal to your internal `usage_events.id`, so retries never double-bill.

### 3.13 Observability

- **Sentry** SDKs in api, worker, and web; tag every event with `account_id` and `repo_id` (never with code contents).
- **structlog** JSON logs with a `request_id`/`job_id` correlation ID propagated from webhook → job → sandbox.
- A `/healthz` endpoint for Fly health checks; a tiny internal admin page showing queue depth and job failure rates.

---

## 4. Data model (v1)

```sql
-- Tenancy
accounts(id, github_account_id UNIQUE, login, type, plan, stripe_customer_id, created_at)
users(id, github_user_id UNIQUE, login, created_at)
memberships(user_id, account_id, role, PRIMARY KEY(user_id, account_id))
installations(id, account_id, github_installation_id UNIQUE, suspended_at)
repos(id, account_id, github_repo_id UNIQUE, full_name, private, default_branch,
      enabled, support_status, backfill_status, backfill_cursor, created_at)

-- CI history
ci_runs(id, account_id, repo_id, github_run_id, run_attempt, head_sha, branch, event,
        conclusion, runner_os, started_at, completed_at,
        UNIQUE(repo_id, github_run_id, run_attempt))
test_cases(id, account_id, repo_id, nodeid, file_path, status, first_seen_at, last_seen_at,
           UNIQUE(repo_id, nodeid))
test_results(id, account_id, test_case_id, ci_run_id, outcome, duration_ms,
             failure_fingerprint, message_excerpt, source)   -- source: plugin|artifact|log
  -- index (test_case_id, ci_run_id); partition by month later if it grows

-- Analysis
flake_scores(test_case_id, window_runs, flip_count, same_sha_flips, fail_rate,
             ci_low, ci_high, classification, computed_at)
diagnoses(id, account_id, test_case_id, category, confidence, repro_command, evidence jsonb, created_at)
experiments(id, diagnosis_id, perturbation, params jsonb, runs, failures, duration_ms)
test_embeddings(test_case_id PRIMARY KEY, embedding vector(384))

-- Output + billing
proposals(id, account_id, repo_id, kind, test_case_id NULL, pr_number, branch, status,
          attempts, validation jsonb, input_tokens, output_tokens, created_at)
usage_events(id, account_id, kind, quantity, stripe_reported_at, created_at)
webhook_deliveries(delivery_id PRIMARY KEY, event, received_at, processed_at)
stripe_events(event_id PRIMARY KEY, type, received_at, processed_at)
```

**Why it's shaped this way (for interviews):**

- `account_id` is denormalized onto history tables so RLS policies are a single-column check and tenant-scoped indexes stay tight.
- `UNIQUE(repo_id, github_run_id, run_attempt)` makes both webhook replays and backfill naturally idempotent (`INSERT … ON CONFLICT DO NOTHING`).
- `source` on `test_results` lets you weight evidence by quality: plugin uploads are complete; log-parsed backfill only sees failures.
- `webhook_deliveries` keyed on GitHub's `X-GitHub-Delivery` header deduplicates redeliveries.

---

## 5. Flake scoring (deterministic)

For each test over a sliding window (e.g., last 50 runs on the default branch + all PR runs):

1. **Same-SHA flip (strongest signal):** a test that both passed and failed on the same commit — across jobs, re-run attempts, or matrix entries — is flaky by definition.
2. **Re-run signal (strong, backfill-friendly):** workflow run attempt 1 failed, attempt 2 passed, same SHA. Available from run metadata even without per-test data, so it can flag *which runs* were flaky during backfill.
3. **Flip rate:** count pass↔fail transitions on the default branch where neither the test file nor its imported modules changed between the two commits.
4. **Broken vs. flaky:** a test that fails consistently from commit X onward is *broken*, not flaky — don't quarantine it; surface it as a real failure.
5. **Classification:** healthy / suspect (1 weak signal) / flaky (same-SHA flip, or flip rate with Wilson lower bound above threshold) / broken. Thresholds are tuned in the eval harness.

---

## 6. Local setup guide

### 6.1 Prerequisites

- Python 3.12, `uv`, Node 20+ with `pnpm`, Docker Desktop, `flyctl`, Stripe CLI, the `gh` CLI, and a free Sentry account.
- A Neon project (or a local Postgres via Docker), an Anthropic API key, a Stripe account in **test mode**.

### 6.2 Repository layout (monorepo)

```
nullcase/
  apps/
    api/          FastAPI app (routes, webhook handlers, auth, billing)
    worker/       Procrastinate tasks (backfill, scoring, diagnosis, llm, pr)
    web/          Next.js dashboard
  packages/
    core/         shared domain logic: models, scoring, ast utils, github client
    pytest-plugin/  nullcase-pytest (published to PyPI)
    upload-action/  GitHub Action wrapper (published to Marketplace)
  sandbox/        Dockerfile + runner script (the battery)
  eval/           benchmark harness + datasets
  infra/          fly.toml files, scripts
  .github/workflows/
```

### 6.3 Create the GitHub App (development instance)

1. GitHub → Settings → Developer settings → GitHub Apps → New.
2. Homepage URL: anything for now. Callback URL: `http://localhost:8000/auth/callback`.
3. Webhook URL: a **smee.io** channel URL (GitHub's recommended way to forward webhooks to localhost). Generate a webhook secret.
4. Set the permissions and events from §3.4. "Where can this app be installed": *Only on this account* while developing.
5. Generate a private key; save the `.pem` outside the repo.
6. Create a **separate production App later** — never point a production app at smee.

### 6.4 Environment variables

```
DATABASE_URL=postgresql+asyncpg://...
GITHUB_APP_ID=...
GITHUB_APP_PRIVATE_KEY_PATH=./secrets/app.pem
GITHUB_WEBHOOK_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
ANTHROPIC_API_KEY=...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
FLY_API_TOKEN=...          # for creating sandbox machines
SENTRY_DSN=...
SESSION_SECRET=...
OIDC_AUDIENCE=nullcase
```

Keep a `.env.example` committed; real values in `.env` (gitignored) locally and in Fly secrets in production.

### 6.5 Run it

```bash
uv sync                                   # Python deps for all packages
pnpm -C apps/web install
uv run alembic upgrade head               # create schema (enable pgvector first: CREATE EXTENSION vector;)
npx smee-client --url https://smee.io/<channel> --target http://localhost:8000/webhooks/github
stripe listen --forward-to localhost:8000/webhooks/stripe
uv run uvicorn apps.api.main:app --reload
uv run procrastinate --app=apps.worker.app worker
pnpm -C apps/web dev
```

### 6.6 The demo repo (build this in week 2)

Create a public repo, e.g. `nullcase-demo`, with a small Python service and **seeded flaky tests, one per category**: order-dependent (shared module-level state), hash-order (asserting on set iteration), network (real HTTP call), timezone (asserting "today" in local time), concurrency (shared temp file under xdist), and plain timing (tight `sleep`-based assertion). Add a workflow that runs the suite on push and on a schedule so history accumulates. This repo is your ground truth, your demo, and your smoke test.

---

## 7. Testing strategy

| Layer | What | How |
|---|---|---|
| Unit | Scoring math, JUnit parsing, AST utilities, import graph, diff parsing, fingerprinting | pytest; property-based tests with Hypothesis for the scoring functions |
| Integration | DB queries, RLS policies, queue enqueue-in-transaction | `testcontainers` Postgres (with pgvector image) per test session |
| Webhook contract | Signature verification, idempotency, handler routing | Recorded real payloads (sanitized) as fixtures; replay each twice and assert one effect |
| GitHub client | Backfill pagination, rate-limit backoff | `respx` to mock HTTP; one scheduled live test against the demo repo |
| Stripe | Checkout → webhook → plan change; meter events idempotency | Stripe test mode + `stripe trigger`; fixture events |
| Sandbox | Battery produces correct categories | Run the sandbox image against the demo repo's seeded tests; assert each category is detected |
| LLM | Schema compliance, repair loop behavior | Mock client for CI; a small, manually-run live suite with fixed inputs and recorded outputs |
| Frontend | Components + key flows | Vitest + Testing Library; one Playwright happy-path (login → repo → test detail) |
| **Eval (the headline)** | Detection precision/recall; diagnosis accuracy; fix acceptance rate | See §8 |

**Security tests worth writing:** a request as tenant A for tenant B's repo returns 404; RLS blocks a raw query without `app.account_id` set; a webhook with a bad signature is rejected; the sandbox cannot reach the internet (attempt a connection from inside, assert failure).

---

## 8. Evaluation harness

1. **Seeded demo repo** — labels known by construction.
2. **A published flaky-test dataset for Python** — FlaPy is a research framework for mining flaky Python tests by rerunning suites in containers; iPFlakies targets Python order-dependent tests. Pick a small, reproducible subset of labeled tests from such work **[verify dataset licensing and availability]**.
3. **Metrics:**
   - Detection precision/recall (flagged vs. labeled flaky).
   - Diagnosis accuracy (predicted category vs. labeled root cause).
   - Fix acceptance rate (proposals that pass the battery ÷ attempts), and median attempts.
   - Validator sensitivity: inject known-flaky tests as fake "AI output" and confirm the battery rejects them. **This proves the gate works.**
4. Publish the numbers in the README with sample sizes and limitations. Small, honest numbers beat impressive vague claims.

---

## 9. CI/CD (GitHub Actions)

`ci.yml` on every PR:

1. `ruff check`, `ruff format --check`, `pyright`, `pnpm lint`, `pnpm typecheck`.
2. Unit + integration tests (testcontainers).
3. Create a **Neon branch** for the PR, run migrations against it, run a smoke test, delete the branch at the end.
4. Build the api/worker/web/sandbox images (no push).
5. **Dogfood:** install `nullcase-pytest` in this workflow so NullCase tracks its own test suite.

`deploy.yml` on push to `main`:

1. Run Alembic migrations against production (migrations must be backward-compatible with the running version: add columns before using them, drop later).
2. `flyctl deploy` for api, worker, web; push the sandbox image to Fly's registry.
3. Create a Sentry release with the commit SHA.

---

## 10. Deployment and hosting

### 10.1 Fly.io apps

- `nullcase-api` — FastAPI (uvicorn), 2 small machines, health check on `/healthz`.
- `nullcase-worker` — Procrastinate worker, 1 machine (scale with queue depth later).
- `nullcase-web` — Next.js, 1–2 small machines.
- `nullcase-sandbox` — no always-on machines; the worker creates ephemeral ones through the Machines API.
- Secrets via `fly secrets set`. Private networking between apps; only api and web are public.

### 10.2 Database

- Neon production branch; enable pgvector; connection pooling on; daily backups per plan **[verify]**.
- Retention job: keep raw `test_results` for a defined window per plan; keep aggregates forever.

### 10.3 Domains and email

- A domain for the dashboard and API; TLS via Fly certificates.
- A support email and a simple privacy policy page — both are **required** for a Marketplace listing.

### 10.4 Rough monthly cost during development

Mostly small: a few tiny Fly machines, Neon's free tier, Sentry's free developer tier, sandbox minutes billed per second, and Anthropic API usage, which will dominate. Budget roughly tens of dollars per month during development **[verify with each provider's current pricing]**, and set hard spending caps on Anthropic and Fly from day one.

---

## 11. GitHub Marketplace distribution

### 11.1 What the rules allow for this MVP

- **Paid plans on Marketplace** require the app to be owned by a **verified publisher organization** and, for GitHub Apps, **at least 100 installations**, plus handling Marketplace purchase events. Not realistic in six weeks.
- **Free listings** have lighter requirements: relevant description, contact info, a pricing plan (free counts), a privacy policy link, and a support link or email; plus logo, feature card, and screenshots.
- **GitHub Actions** can be published to Marketplace by anyone.

### 11.2 Plan

1. **Publish `nullcase/upload-action` to Marketplace** (week 5). Requirements: public repo, `action.yml` at the root, a unique name, a release with "Publish this Action to the GitHub Marketplace" checked, and 2FA on your account **[verify current steps]**.
2. **List the GitHub App for free** (week 5–6): make the production App public ("Any account"), fill in the listing, submit for review.
3. **Take payment via Stripe on your own site** for private repos. Before listing, read the GitHub Marketplace Developer Agreement for any restriction on off-platform paid tiers for a free-listed app **[verify — unresolved in this research]**. If it's ambiguous, launch the listing after the first Stripe transaction and describe the private-repo plan neutrally on your own site only.
4. **Later (post-MVP):** create a GitHub organization for NullCase, complete publisher verification, and once past 100 installs, add a paid Marketplace plan handling `marketplace_purchase` webhooks.

---

## 12. Security checklist

- [ ] Webhook HMAC (`X-Hub-Signature-256`) verified with constant-time comparison before any parsing.
- [ ] Delivery-ID and Stripe event-ID idempotency tables.
- [ ] Installation tokens minted per job, never stored long-term.
- [ ] RLS enabled on every tenant table; a test proves it.
- [ ] Sandbox: no secrets, no egress after dependency install, CPU/memory/time caps, destroyed after each job.
- [ ] LLM has no write tools; all output passes the battery before a PR is opened.
- [ ] No code contents in logs or Sentry events.
- [ ] Private repo code is never used for anything beyond serving that tenant; say so in the privacy policy.
- [ ] Rate-limit public endpoints (result upload, login).

---

## 13. Six-week build plan

| Week | Deliverable | Done when |
|---|---|---|
| 1 | Monorepo, schema + RLS, GitHub App, webhook ingest, deploy skeleton to Fly with CI/CD and Sentry | A push to the demo repo creates a `ci_runs` row in production |
| 2 | pytest plugin + OIDC upload, backfill job, flake scoring, demo repo seeded, eval harness v0 | Dashboard-less API returns correct classifications for the seeded tests |
| 3 | Sandbox image, Machines orchestration, experiment battery, diagnosis + repro commands | Every seeded category is diagnosed correctly with a repro command |
| 4 | LLM fix loop, PR generation for uncovered code, validation gate, PR creation with evidence table | A fix PR for a seeded flaky test opens automatically and passes the battery; a known-flaky "AI" test is rejected |
| 5 | Dashboard, Stripe (Checkout, Portal, Meters), plans + limits, Action published to Marketplace, customer outreach begins | You can sign up, connect a repo, pay in test mode, see charts |
| 6 | Eval numbers, README, one-pager, 60-second demo video, free App listing submitted, first real transaction pursued, buffer | Everything deployed; numbers published; honest traction statement |

**Cut order if behind:** mutation/coverage extras → embeddings (keep import-graph retrieval) → PR-code generation (keep flaky fixes) → Marketplace App listing. Never cut: deployment, the battery, the eval numbers, billing.

---

## Sources

- Trunk Autofix Flaky Tests (beta): https://docs.trunk.io/flaky-tests/agents/autofix-flaky-tests.md
- Datadog Bits AI Dev Agent for flaky tests: https://www.datadoghq.com/blog/bits-ai-test-optimization/
- Datadog Early Flake Detection: https://docs.datadoghq.com/tests/flaky_tests/early_flake_detection/
- Bitbucket AI flaky test remediation: https://support.atlassian.com/bitbucket-cloud/docs/ai-driven-flaky-test-remediation/
- whyflaky: https://pypi.org/project/whyflaky/
- pytest-flakedoctor: https://pypi.org/project/pytest-flakedoctor
- FlaPy (ICSE 2023 companion): https://dl.acm.org/doi/abs/10.1109/ICSE-Companion58688.2023.00039
- GitHub Marketplace listing requirements: https://docs.github.com/en/apps/github-marketplace/creating-apps-for-github-marketplace/requirements-for-listing-an-app
- GitHub Marketplace overview: https://docs.github.com/en/apps/github-marketplace/github-marketplace-overview/about-github-marketplace-for-apps
- GitHub Actions retention change (Oct 1, 2026): https://github.blog/changelog/2026-08-27-actions-retention-will-cover-checks-workflow-runs-and-statuses/
- Stripe billing meters migration: https://docs.stripe.com/billing/subscriptions/usage-based-legacy/migration-guide
- Stripe recording usage: https://docs.stripe.com/docs/billing/subscriptions/usage-based/recording-usage
- Fly.io virtual sandbox overview: https://fly.io/learn/virtual-sandbox/
- Anthropic API docs: https://docs.claude.com/en/api/overview