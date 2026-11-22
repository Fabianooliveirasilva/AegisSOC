# Sprint 1 — Security review notes

Author: Security Reviewer agent (independent of the implementers). Format per `docs/SPRINT_01_EXECUTION_PROTOCOL.md` §7 and `.claude/agents/security-reviewer.md`.
Severity scale: Critical / High / Medium / Low / Info. Findings of **High or above block the task** (§9).

---

## Review context: S1-T01 and S1-T02 (PR2)

| Field | Value |
|---|---|
| Branch | `feat/S1-T01-T02-repo-tooling-backend-skeleton` |
| Commits | `cdd5c9f` (S1-T01), `b796214` (S1-T02). Diff reviewed: `git diff bcb8712..b796214` |
| HEAD at scan time | `b79621461818d1d9132a5961ba6b523a945b1d93` |
| Date (UTC) | 2026-11-22T01:52Z – 01:54Z |
| Environment | Linux 6.8.0-149-generic (Ubuntu 22.04 host, `/bin/sh` = dash), Docker 29.1.3, uv 0.13.7, Python 3.12.16 (project venv), pre-commit 4.7.0 |
| Requirements | SR-16, SR-13, SR-25, SR-26, SR-39, SR-40; threats T-20, T-23, T-25, T-26, T-32 |
| Producer | security-reviewer agent |

### Scanner results (both tasks)

| Scanner | Command | Exit | Result | Raw artefact (SHA-256) |
|---|---|---|---|---|
| Bandit 1.9.4 | `cd apps/api && uv run bandit -r src -f json -o <scratch>/bandit.json -q` | 0 | 0 issues (60 LOC, 0 `#nosec`) | `bandit.json` `ea639824f7fbbbd8ec585700a9006a5327b9b61d8351228250d32b0a7cd217ca` |
| pip-audit 2.10.1 (installed env, dev + runtime) | `cd apps/api && uv run pip-audit -f json -o <scratch>/pip-audit-env.json` | 0 | 80 dependencies, 0 known vulnerabilities. The local `aegissoc` 0.0.0 is skipped (not on PyPI), so `--strict` exits 1 for that reason only | `pip-audit-env.json` `d05fd7462f752eee21713e0445c49d41e96c6ad108484def3e8a168a54a41f66` |
| pip-audit (lockfile, hash-checked) | `uv export --frozen --all-groups --no-emit-project --format requirements-txt -o req-locked.txt` then `uv run pip-audit -r req-locked.txt --require-hashes --disable-pip -f json -o pip-audit-lock.json` | 0 | 79 dependencies, 0 known vulnerabilities | `pip-audit-lock.json` `55b68c135ea525a89e5e9f6e7c3e09050c170ceefdfbbe8a4a7f1467891ed0d8` |
| Gitleaks v8.30.1 (working tree) | `sg docker -c 'make scan'` (runs `docker run --rm -v "$(CURDIR):/repo:ro" ghcr.io/gitleaks/gitleaks:v8.30.1 dir /repo --redact --no-banner`) | 0 | `scanned ~794720 bytes (794.72 KB) in 279ms` / `no leaks found` | console output only (quoted here) |
| Gitleaks v8.30.1 (full git history, all refs) | `docker run --rm --network none -v "$PWD:/repo:ro" ghcr.io/gitleaks/gitleaks:v8.30.1 git /repo --log-opts=--all --redact --no-banner -f json -r /dev/stdout` | 0 | `10 commits scanned.` / `scanned ~758760 bytes` / `no leaks found`; JSON report empty | `gitleaks-history.json` `e3b0c442…b855` (empty file) |
| Image digest used | `docker image inspect` | — | `ghcr.io/gitleaks/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f` | — |
| Semgrep | — | — | **Not run.** Arrives with S1-T13 (`.semgrep/aegissoc.yml`, container image) | — |
| Trivy fs / config / image | — | — | **Not run.** Arrives with S1-T13; no images exist yet | — |
| pnpm audit | — | — | **Not applicable.** Root `package.json` declares no dependencies and there is no `pnpm-lock.yaml` yet (S1-T11) | — |

**Artefact retention gap:** the raw JSON/log files are in the session scratchpad only. My attempt to copy them under `docs/security/reviews/evidence/` was refused by the session's permission classifier, and I did not work around it. Per §7 the orchestrator or QA should commit the re-produced artefacts under `qa/reports/sprint-01/evidence/` (the commands above are reproducible at the SHA). The hashes above identify the files I produced.

Manual history checks (no secret file ever committed):

```
$ git log --all --name-only --pretty=format: | sort -u | grep -Ei '(^|/)(\.env($|\.)|secrets/|.*\.(pem|key)$|id_rsa|credentials)'
.env.example
$ git grep -nIiE '(password|passwd|secret|token)\s*[:=]\s*["'\'']?[A-Za-z0-9+/_-]{12,}' b796214 -- . ':!apps/api/uv.lock' ':!apps/api/tests/fixtures/*'
(no output)
```

### File-bounds check (§3, §5.2)

| Task | Paths changed | Within §3 bounds? |
|---|---|---|
| S1-T01 (`cdd5c9f`) | `.editorconfig`, `.env.example`, `.gitignore`, `.pre-commit-config.yaml`, `CHANGELOG.md`, `Makefile`, `package.json`, `pnpm-workspace.yaml`, `scripts/check-prereqs`, `scripts/setup-secrets` | **Yes.** `.gitignore` diff has no `-` lines (additions only). Nothing under `infrastructure/compose/secrets/` is tracked (`git ls-files infrastructure` lists only `README.md` and `.gitkeep` files) |
| S1-T02 (`b796214`) | `apps/api/{.importlinter,alembic.ini,pyproject.toml,uv.lock}`, `apps/api/src/aegissoc/**` (41 files), `apps/api/tests/unit/test_skeleton.py`, `apps/api/tests/fixtures/common_passwords.txt` | **Yes.** `apps/api/README.md` (referenced by `readme =`) was already in the planning baseline `2946f06` and is not modified |

No out-of-bounds path.

---

## S1-T01 — Repository tooling (including secret generation)

**Status (initial review): No blocking findings** (0 Critical, 0 High, 2 Medium, 3 Low, 3 Info). I recommend fixing **S1-T01-SEC-01** before S1-T12a starts using the generated files. *Current status after fix cycle 1: see "Re-verification after fix cycle 1" below.*

### What was verified (no finding)

- **Entropy source:** `head -c 32 /dev/urandom | base64 | tr '+/' '-_' | tr -d '=\n'` gives 32 bytes (256 bits) as 43 base64url characters. Test T1: all 5 files are 43 characters matching `^[A-Za-z0-9_-]{43}$`, and all 5 values are distinct.
- **File modes:** `umask 077` is set before `mkdir` and before file creation, so files are created `0600`. No window exists in which they are wider. The directory is forced to `0700` even if it already existed with `0755` (T4).
- **No overwrite / idempotent:** a second run reports `0 created, 5 already present`, and the SHA-256 of every file is unchanged (T2).
- **Symlink / TOCTOU:** a planted dangling symlink `redis_password -> ../victim` is counted as kept and **not followed**: the victim is not created (T3). The create uses `set -C` (noclobber). For a path that does not exist, dash opens it with `O_CREAT|O_EXCL`, so a symlink planted between the check and the open makes the create fail instead of being followed. A race with a non-regular object is only possible for the same UID inside a `0700` directory. If `AEGIS_SECRETS_DIR` points at a directory owned by another user, `chmod 700` fails and `set -e` aborts.
- **No secret on stdout, in argv or in Makefile output:** values only travel through the pipe into the file. stdout carries only counts and the directory (T1 grep of stdout for each value: no match). The Make recipes are `@`-silenced. `psql` reads the password inside the container (`$$(cat /run/secrets/...)`), so the echoed recipe has no value. `bootstrap-admin` prompts for the password interactively.
- **Argument handling:** an unknown option is rejected (`setup-secrets: unknown option: --bogus`, exit 2). All expansions of `$target` and `$file` are quoted. `$names` is a fixed internal list.
- **`.gitignore` / `.env.example`:** `infrastructure/compose/secrets/*` is added, and the existing `secrets/` already covers it (`git check-ignore -v --no-index infrastructure/compose/secrets/x` → `.gitignore:5:secrets/`). `.env` and `.env.*` are ignored with `!.env.example`. `.env.example` holds only non-secret settings, and AI is off by default.
- **`check-prereqs`:** only parses tool version output. It handles no secrets and executes no external input.
- **`make clean`:** uses `rm -r --` on a fixed list without `-f`. A symlink is removed as a link and not followed.

### Findings

| ID | Severity | Location | Ref | Finding | Fix suggestion |
|---|---|---|---|---|---|
| **S1-T01-SEC-01** | **Medium** | `scripts/setup-secrets` line with `( set -C; head -c 32 /dev/urandom \| base64 \| … > "$file" )` | SR-16, T-20, T-32 | **The script fails open: a failure in the entropy source or the encoder creates empty secrets and exits 0.** The subshell's status is that of the last command in the pipeline (`tr`). If `head`/`/dev/urandom` or `base64` fails, the script creates a 0-byte file, counts it as "created" and exits 0. Because existing files are never overwritten or validated, later runs keep the empty "secret" for good. An empty `redis_password` would mean Redis has no auth (contradicts "No default or fixed credentials"). Evidence below (T7–T9) | Generate into a variable, validate, then write: `v=$(head -c 32 /dev/urandom \| base64 \| tr '+/' '-_' \| tr -d '=\n')`; `case $v in *[!A-Za-z0-9_-]*\|'') fail;; esac; [ ${#v} -eq 43 ] \|\| fail`; then `( set -C; printf '%s' "$v" > "$file" )` (`printf` is a dash builtin, so the value is never in argv). Add a unit or QA test that shims `head` to fail and expects a non-zero exit and no file |
| **S1-T01-SEC-02** | **Medium** | `Makefile` `GITLEAKS_IMG`, `scan` target; `.pre-commit-config.yaml` `gitleaks-docker` entry | T-23, T-25, SR-25 / SR-40 (pinning intent), SR-23 (digest pinning for images) | **The Gitleaks image is pinned by a mutable tag (`:v8.30.1`), not by digest, and runs with network access over the whole repository.** `make scan` mounts the repo read-only but with network enabled. That mount includes the git-ignored `infrastructure/compose/secrets/*` and any `.env`. The pre-commit `docker_image` hook is worse: pre-commit itself mounts the repo **read-write** (`pre_commit/languages/docker.py:154` → `-v {cwd}:/src:rw,Z`), including `.git/`. So a re-tagged or compromised image could exfiltrate the local secrets, or write `.git/hooks/*` and get code execution on the host. The likelihood is low (it needs an upstream registry compromise), but the impact is high and the fix is cheap | Pin by digest in both places: `ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:<digest>`. The digest I observed locally is `sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f`; verify it against the upstream release before adopting it. Add `--network none` to the `scan` recipe. In the pre-commit entry, prefix the docker flags (`entry: --network none ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:… git --pre-commit --redact --staged --verbose`; pre-commit passes leading entry tokens to `docker run`). DevOps owns the change; scanner coverage is unchanged, so HC-5 is not triggered |
| S1-T01-SEC-03 | Low | `.pre-commit-config.yaml` `rev:` values | T-23 | Hook repositories are pinned by git **tags** (`v0.17.6`, `v6.0.0`, `v3.1.0`, `v8.30.1`), and tags can be moved upstream. `pre-commit/mirrors-prettier` has been archived upstream and pins an old Prettier (3.1.0) | `pre-commit autoupdate --freeze` (commit SHA + `# frozen: vX` comment). Consider a maintained Prettier hook or a local hook that uses the pnpm-locked Prettier once S1-T11 adds it |
| S1-T01-SEC-04 | Low | `Makefile` `CLEAN_PATHS` (also `COMPOSE`, `GITLEAKS_IMG`) | T-26, SR-39 | Make variables set on the command line override `:=` assignments, so `make clean` is an arbitrary `rm -r` despite the comment "Fixed, relative cache locations". §5.2 offers `make clean` to agents as the safe alternative to `rm -rf`. Evidence: `make -n clean CLEAN_PATHS=/nonexistent-aegis-probe` expands to `for p in /nonexistent-aegis-probe; do … rm -r -- "$p" …`. The same override can swap the scanner image (`GITLEAKS_IMG=…`) | Use `override CLEAN_PATHS := …`, `override GITLEAKS_IMG := …` and `override COMPOSE := …`, or put the literals in the recipes |
| S1-T01-SEC-05 | Low | `scripts/setup-secrets` "kept" branch | SR-16 | Files that already exist are kept without any check of type, size or mode. A pre-existing `0644` 1-byte `redis_password` stays `0644` with 1 byte (T4). This is how SEC-01's empty files persist, and how a hand-made weak secret would be accepted silently | For each kept file: require a regular file (not a symlink) of 43 characters, and `chmod 600` it. Otherwise print a warning that names the file (never the value) and exit non-zero |
| S1-T01-SEC-06 | Info | `Makefile` `logs` target, `$(SERVICE)` unquoted | — | Shell injection through a make argument: `make -n logs 'SERVICE=x; echo INJECTED'` → `… logs -f x; echo INJECTED`. Only the operator controls the argument, so there is no trust boundary today | Validate the value (`case`/`grep -E '^[a-z0-9_-]*$'`) or quote it |
| S1-T01-SEC-07 | Info | `scripts/setup-secrets` `mkdir -p "$target"`, `chmod 700 "$target"` | — | No `--` separator. `AEGIS_SECRETS_DIR=-p` fails closed (`mkdir: falta operando`, exit 1). `chmod` follows a symlinked target directory | `mkdir -p -- "$target"`, `chmod 700 -- "$target"` |
| S1-T01-SEC-08 | Info | `Makefile` `scan` | SR-26, protocol §10 | `make scan` runs Gitleaks in `dir` mode (working tree only). There is no target for the full-history scan that §10 requires after a local secret commit. I ran it manually: 10 commits, no leaks | When S1-T13 adds `.gitleaks.toml`, add a `git --log-opts=--all` stage to `make scan` (and to CI) |

**Evidence for S1-T01-SEC-01** (run against scratch directories only, never the real secrets directory; the shims are throwaway scripts in the session scratchpad that put a failing `head` / `base64` first on `PATH`):

```
== T7 entropy source failure (shim 'head' exits 1, prints nothing) ==
setup-secrets: 4 created, 0 already present (dir: …/sst/d7)
exit=0
600 size=0 …/d7/postgres_app_password
600 size=0 …/d7/postgres_owner_password
600 size=0 …/d7/postgres_superuser_password
600 size=0 …/d7/redis_password
== T8 second run after failure keeps empty files ==
setup-secrets: 0 created, 4 already present (dir: …/sst/d7)
size=0 …/d7/postgres_app_password
== T9 base64 missing (shim) ==
setup-secrets: 4 created, 0 already present (dir: …/sst/d9)
exit=0
size=0 …/d9/postgres_app_password
```

Evidence for the positive checks (T1–T5):

```
== T1 fresh run (--ci) ==            exit=0; "5 created, 0 already present"
700 …/d1 ; 600 for each of the 5 files ; each len=43 charset_ok=yes ; distinct: 5 of 5
secret in stdout? (none)
== T2 rerun idempotent ==            "0 created, 5 already present" ; sha256 diff: unchanged
== T3 dangling symlink planted ==    "3 created, 1 already present" ; victim: No such file or directory
== T4 pre-existing dir 755, file 644 ==  dir -> 700 ; redis_password stays 644, 1 byte   (SEC-05)
== T5 ==  --bogus -> "unknown option", exit=2 ; AEGIS_SECRETS_DIR=-p -> mkdir: missing operand, exit=1
```

---

## S1-T02 — Backend skeleton (dependency and configuration hygiene)

**Status (initial review): No blocking findings** (0 Critical, 0 High, 0 Medium, 1 Low, 4 Info). *Current status: see the re-verification below.* §3 lists S1-T02 for QA only; this section covers the dependency and configuration hygiene the orchestrator asked for.

### What was verified (no finding)

- **Dependencies vs SPRINT_01 §1:** the direct runtime deps match the approved list exactly (`fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `redis`, `argon2-cffi`, `structlog`, `uuid6`). The dev deps also match exactly (`pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`, `ruff`, `mypy`, `import-linter`, `bandit`, `pip-audit`). No dependency outside §1, so **HC-2 is not required**.
- **Lockfile integrity:** `uv lock --check` → `Resolved 81 packages`, exit 0. All 80 third-party packages come from `registry = "https://pypi.org/simple"` (no git, URL or path sources besides the editable project). Every package carries sha256 hashes (465 hashes, none missing).
- **Licences** (from installed metadata): the 34 runtime packages are all permissive (MIT, BSD-2/3, Apache-2.0, PSF-2.0, MIT-0, `MIT OR Apache-2.0`). The dev-only tree adds MPL-2.0 (`certifi`, `pathspec`), which is fine for dev tooling. No GPL/AGPL.
- **Known vulnerabilities:** none (pip-audit on the env and on the hash-checked lock export, see the table above).
- **App factory:** `docs_url=None`, `redoc_url=None`, `openapi_url=None`, with a unit test asserting all three (`tests/unit/test_skeleton.py`).
- **`alembic.ini`:** no `sqlalchemy.url` and no credential. The `sqlalchemy.engine` logger is at WARNING, so SQL is not logged by default.
- **Static analysis config:** ruff selects `S` (flake8-bandit), and only `S101` is ignored, under `tests/**`. mypy is `strict`. Bandit is clean. Nothing in the skeleton deserialises data (SR-13).
- **`common_passwords.txt`:** the header names the source (SecLists `Passwords/Common-Credentials/10k-most-common.txt`), the licence (MIT, Daniel Miessler and contributors, which is SecLists' licence), the retrieval date, and the SHA-256 of the original. I recomputed it: `tail -n +9 … | sha256sum` → `68782d6a4a19a4768d5f15dd66bd534e7a33055cc755411e33f16d18c50fdcce`, which **matches the header**. The body has 10,001 lines and no `#` lines, so the specified comment-skipping loader drops no entry. It contains public data, not credentials.

### Findings

| ID | Severity | Location | Ref | Finding | Fix suggestion |
|---|---|---|---|---|---|
| S1-T02-SEC-01 | Low | `apps/api/pyproject.toml` `[build-system] requires = ["hatchling"]` | T-23, SR-25 | The build backend is not version-bounded and not covered by `uv.lock`. Each isolated build of the editable project (`uv sync`) resolves the latest `hatchling` from PyPI | Bound it (e.g. `hatchling>=1.27,<2`), or rely on `uv sync --frozen` together with uv's `build-constraint-dependencies` |
| S1-T02-SEC-02 | Info | `apps/api/pyproject.toml` dependency specifiers | SR-25 | Only lower bounds (`>=`) are declared. This is fine because `uv.lock` pins everything, as long as CI and the Dockerfile install with `uv sync --frozen` / `--locked` | S1-T12 and S1-T13 must use `--frozen`/`--locked`; I will check this in those reviews |
| S1-T02-SEC-03 | Info | `uvicorn[standard]` extras | SR-23 | The approved extras pull in `watchfiles` (auto-reload), `python-dotenv` (`--env-file`) and `websockets`. They are harmless if unused | S1-T12: the container command must not use `--reload` or `--env-file` (secrets via `*_FILE` only) |
| S1-T02-SEC-04 | Info | transitive `opentelemetry-api` 1.45.2 (via `fastapi` 0.165.0) | T-23 | An unexpected transitive runtime package (Apache-2.0, from PyPI). It comes with an approved direct dependency, so it is not an HC-2 item | None; note it in the PR dependency justification |
| S1-T02-SEC-05 | Info | `common_passwords.txt` provenance | — | The header hash matches the body, but I could not compare it with the upstream file: outbound fetches (`curl`/`wget`) are denied to agents by design | The maintainer can verify once: `sha256sum` of the upstream file at the retrieval date = `68782d6a…fdcce` |

---

## Threat-model change proposals (for the maintainer; not applied)

1. **T-23** (supply chain) mitigations: add "developer tooling executed from container images or hook repositories (Gitleaks, pre-commit hooks, later Semgrep/Trivy) is pinned by digest/commit SHA and run with `--network none` where possible". Today SR-23 covers application images and SR-40 covers GitHub Actions, but neither covers local or CI scanner images (S1-T01-SEC-02/03).
2. **T-20 / T-32**: add to SR-16's verification (TC-SEC-27) that the secret generator **fails closed**: a non-zero exit and no file when entropy or encoding fails, and kept files are validated (S1-T01-SEC-01/05).

## Guardrail observations during this review

- A combined read-only Bash command that included `ls -la infrastructure/compose/secrets` was **denied** before execution, consistent with the secrets-path deny intent (EV-S01-000). I re-ran the command without that path. I did not read the real secrets directory at any point. All secret-generation tests used scratch directories.
- Copying scanner artefacts into `docs/security/reviews/evidence/` was denied by the session's permission classifier. I did not work around it (see "Artefact retention gap").

## Verdict (initial review at `b796214`; superseded by the re-verification below)

| Task | Verdict | Open ≥ High | Notes |
|---|---|---|---|
| **S1-T01** | **No blocking findings** | 0 | Medium: SEC-01 (fail-open secret generation; fix before S1-T12a consumes the files), SEC-02 (Gitleaks image tag-pinned, rw/networked mount). Low: SEC-03, SEC-04, SEC-05. Info: SEC-06 to SEC-08 |
| **S1-T02** | **No blocking findings** | 0 | Low: SEC-01 (unbounded build backend). Info: SEC-02 to SEC-05. No HC-2 needed |

This review approves nothing; merge stays with the maintainer, and the QA notes are separate.

---

## Re-verification after fix cycle 1: S1-T01 and S1-T02 (fix commit `7e69ead`)

| Field | Value |
|---|---|
| Branch | `feat/S1-T01-T02-repo-tooling-backend-skeleton` |
| Fix commit | `7e69ead6ab1c10768bb5a115f8d23627a5f7ca39` on top of `cdd5c9f` and `b796214`. Diff: `git diff b796214..7e69ead` |
| Date (UTC) | 2026-11-22T01:58Z – 02:07Z |
| Environment | as above. Docker commands were run through `sg docker -c` |
| Method | Every fix was checked by **running** it: shims first on `PATH`, `/dev/urandom` bind-mounted over in a user and mount namespace (`unshare -rm`), a full 8 KiB tmpfs, `strace` (execve, openat, delayed openat), a logging docker wrapper and an inspecting docker wrapper, a throwaway git repo, a scratch copy of the `Makefile`. I did not rely on the diff alone. Everything ran in `mktemp -d` scratch directories. The real `infrastructure/compose/secrets/` was never read, written or listed by me. The only exception is that `make scan` mounts the whole repository into Gitleaks, as designed |

### File-bounds check (§3) for `7e69ead`

| Path | Task | Within bounds? |
|---|---|---|
| `.pre-commit-config.yaml`, `Makefile`, `scripts/setup-secrets` | S1-T01 | Yes |
| `apps/api/pyproject.toml` | S1-T02 | Yes |

No other path changed. `git status` after my tests shows only the untracked review and QA notes; no build output was left in the repo (`uv build` wrote to a scratch `--out-dir`).

### Status of each finding

| ID | Sev. | Status | Evidence (summary; details below) |
|---|---|---|---|
| S1-T01-SEC-01 | Medium | **Fixed** | Failing `head` → exit 1, no file. Failing `base64` → exit 1, no file. `head` returning 16 bytes → exit 1. `base64` returning garbage with exit 0 → exit 1. `/dev/urandom` bind-mounted to `/dev/null` (0 bytes) or to a 10-byte file → exit 1, directory empty. Full filesystem (8 KiB tmpfs) → `head: write error: No space left on device`, exit 1, directory empty. Every case left 0 secret files and 0 temp files |
| S1-T01-SEC-02 | Medium | **Fixed** (Info residual) | Digest pinned in the `Makefile` and in the pre-commit entry. Registry: `imagetools inspect ghcr.io/gitleaks/gitleaks:v8.30.1` → index `sha256:c00b6bd0…bbb7f` (multi-arch OCI index: amd64 `b109bc5f…`, arm64 `6b2d5224…`, plus attestations), the same as the pin. `--network none` was really applied: `docker inspect` of the actual containers shows `NetworkMode=none Networks=none` for **both** `make scan` and the pre-commit hook, and the running image is `sha256:c00b6bd0…`. The hook still blocks a staged synthetic `ghp_` token (`RuleID: github-pat`, exit 1, value redacted). Residual: pre-commit still mounts the repo `rw` (inherent to `docker_image`); with no network and a pinned digest, this needs a malicious image at pin time |
| S1-T01-SEC-03 | Low | **Partially fixed** | All four `rev:` values are commit SHAs. `git ls-remote` resolves each claimed tag to exactly the pinned SHA (all lightweight tags, so there is no `^{}` peel), and `git cat-file -t` in the cached clones says `commit` for each. **Open part:** `mirrors-prettier` is still archived upstream and pins Prettier 3.1.0. It is marked as an OPEN ITEM in the config and deferred to S1-T11 |
| S1-T01-SEC-04 | Low | **Fixed** (for the named variables; Info residual SEC-11) | `make -n clean CLEAN_PATHS=/nonexistent-aegis-probe`, `make -n -e clean` with `CLEAN_PATHS` in the environment, `make -n scan GITLEAKS_IMG=evil/img:latest`, `GITLEAKS_IMG=… make -n scan`, and `--eval='override CLEAN_PATHS := …'` all expand to the fixed values |
| S1-T01-SEC-05 | Low | **Fixed** | 13 pre-existing-file cases (table below). Each bad file was reported by name, left **unmodified** (type, mode, size and SHA-256 identical before and after), and the run exited 1. A valid `0600` file is kept, and the run exits 0. A dangling symlink is not followed: the victim is not created |
| S1-T01-SEC-06 | Info | **Fixed** | Scratch `Makefile` copy, fake `docker`: `SERVICE=api` → `[logs] [-f] [api]`. Rejected with exit 2: `x; echo INJECTED`, `` `id` ``, `--since=1h`, `-f`, `a b`, `*`, an embedded newline, and an injection through the environment. `SERVICE=$(id)` is expanded by make to an empty string, so nothing runs. Usability note: a list of several services (`api worker`) is now rejected |
| S1-T01-SEC-07 | Info | **Partially fixed** | `mkdir -p --` and `chmod 700 --` added. `chmod` still follows a symlinked target directory (a `0755` `realdir` behind `linkdir` became `0700`; same UID only). `mktemp "$target/.gen.XXXXXX"` has no `--`: `AEGIS_SECRETS_DIR=-x` makes it fail closed (`mktemp: invalid option -- 'x'`, exit 1, no file) |
| S1-T01-SEC-08 | Info | **Open** (deferred) | `make scan` is still dir mode only. I ran a full-history scan manually (below). Due with S1-T13 |
| S1-T02-SEC-01 | Low | **Fixed** (Info residual) | `requires = ["hatchling>=1.33.0,<2"]`. `uv build` resolves `hatchling==1.33.0` and builds sdist and wheel. Adding a `hatchling>=2` build constraint makes the build fail with "unsatisfiable", which shows the upper bound is enforced. Residual: the build environment (`hatchling` and its deps `packaging`, `pathspec`, …) is still resolved fresh and is not hash-locked; track it in S1-T12 (Dockerfile) |
| S1-T02-SEC-02 … SEC-05 | Info | Unchanged | Carried forward to S1-T12/S1-T13 as stated above |

### New findings introduced by the fix (`scripts/setup-secrets`, `Makefile`)

| ID | Severity | Location | Ref | Finding | Fix suggestion |
|---|---|---|---|---|---|
| S1-T01-SEC-09 | Low | `scripts/setup-secrets`: `( set -C; : > "$file" )` followed by `printf '%s' "$secret_value" > "$file"` | SR-16, T-20 | **Regression of the atomic create I verified in round 1.** The file is now opened twice. `strace` shows `openat(…redis_password, O_WRONLY\|O_CREAT\|O_EXCL)` and then `openat(…redis_password, O_WRONLY\|O_CREAT\|O_TRUNC)`. The second open follows symlinks. Demonstrated by delaying the openat calls with `strace -e inject=openat:delay_enter=3000000` and, between them, replacing the new empty file with a symlink to `race-victim2` (0 bytes, 0644): the script exited 0 and reported "4 created". The 43-byte secret ended up **in the victim file**, which was also `chmod`ed to 600, and `redis_password` was left as a symlink. The code comment ("Noclobber makes the create atomic") is therefore not true for the write. Exploiting it needs the same UID with write access to the 0700 directory (an attacker who could read the secrets anyway), so the severity is Low | Write through the same descriptor the exclusive open returned, e.g. `set -C; exec 3> "$file"; set +C; created_file=$file; printf '%s' "$secret_value" >&3 && exec 3>&-` (an `exec` redirection failure aborts a non-interactive dash, so it fails closed). Alternatively, restore the single-open form of round 1, now with the validated value: `( set -C; printf '%s' "$secret_value" > "$file" )`. Add a test: a symlink planted at the target path makes the run fail and the symlink target stays untouched |
| S1-T01-SEC-10 | Info | `scripts/setup-secrets` `generate()` temp file `"$target/.gen.XXXXXX"` | SR-16 | The new temp file holds the raw 32 random bytes inside the secrets directory. (1) A `SIGKILL` leaves it behind: a shim `base64` that runs `kill -9 $PPID` left `.gen.K6HVl3` (32 bytes, 0600), and the next run ignores it (exit 0, no warning). SIGTERM is handled correctly (exit 143, no residue). The residue is never used as a secret, so the impact is clutter. (2) `head > "$tmp"` reopens the path with `O_TRUNC`, the same pattern as SEC-09. The temp file is not needed: when the padding is stripped, base64 of *n* bytes is 43 characters only for *n* = 32, so `valid_value` alone already detects a short, empty or failed read | `secret_value=$(head -c 32 /dev/urandom \| base64 \| tr '+/' '-_' \| tr -d '=\n')` followed by the existing `valid_value` check (43 chars), with no temp file. Optionally, warn about leftover `.gen.*` files |
| S1-T01-SEC-11 | Info | `Makefile` built-in variables | T-26, SR-39 | `override` locks the five named variables, but the built-ins can still be overridden on the command line. `make clean SHELL=/bin/echo` (scratch copy) ran the recipe through `/bin/echo`, so any program can be run. `make scan PATH=<dir>:…` used a fake `docker` from `<dir>`. `make -n scan CURDIR=/` mounts the host `/` into Gitleaks (read-only, no network). There is no `Bash(make …)` allow rule in `.claude/settings.json` (only `make reset *` is ask), so every make call is still prompted. No trust boundary is crossed | Document that make arguments are operator-controlled. Optionally add `override SHELL := /bin/sh` and use `$(abspath .)` instead of `$(CURDIR)` in `scan`. PATH cannot be fully locked |
| S1-T01-SEC-12 | Info | `scripts/setup-secrets` | SR-16 | The script cannot detect a broken RNG. With a constant 64-byte zero file bind-mounted over `/dev/urandom`, all 4 secrets were identical (same SHA-256) and the run exited 0. If `/dev/urandom` is subverted the host is already compromised, so this is not a defect | Optional and cheap: fail if two generated values in one run are equal |

### Verified positive properties of the new code (no finding)

- **No value leaks.** `strace -f -e execve` over a full `--ci` run recorded 54 execs: `base64`, `tr +/ -_`, `tr -d =\n`, `wc -c`, `head`, `mktemp`, `rm -f -- …/.gen.*`, `chmod 600 -- <file>`, `mkdir`, `dirname`. None of the 5 generated values appears anywhere in the trace (grep per value: no match). `printf`, `[` and `valid_value` are shell builtins or functions. stdout and stderr hold only counts, paths and file names. None of the 13 SEC-05 cases printed the synthetic existing value.
- **Positive path:** `--ci` gives `5 created`, exit 0, dir `700`, 5 × `600`, each 43 characters matching `^[A-Za-z0-9_-]{43}$`, 5 distinct values, no `.gen.*` left. The rerun gives `0 created, 5 already present`, exit 0, and the SHA-256 of every file is unchanged.
- **Error paths and traps:** the EXIT trap removes the temp file and, on a non-zero status, the file created in this run. SIGTERM during generation → exit 143, directory empty. An interruption between the create and the write leaves at most an empty file, which the next run rejects ("is empty", exit 1), so it still fails closed. An unwritable target (`/proc/aegis-probe`) → exit 1.
- **`find -prune -perm 600`:** exact match. It rejects `644`, `400` and `2600` (setgid). The `[ -L ]` and `[ -f ]` checks run first, so `find` only sees regular files. A target named `!` or `(` works, because `find` receives `!/name`, which is not an operator. A target that starts with `-` cannot get this far, because `mktemp` fails first (fail closed). A file that is valid but has a trailing newline (44 bytes) or an embedded NUL is rejected by the `wc -c` = 43 check, which catches what command substitution strips.

SEC-05 matrix (all in scratch directories; "unmodified" = type, mode, size and SHA-256 identical before and after):

```
case                                   message                                              exit  unmodified
valid value, mode 644                  does not have mode 600                               1     yes
empty, 600                             is empty                                             1     yes
symlink -> valid 600 file              is a symlink                                         1     yes
dangling symlink                       is a symlink (victim not created)                    1     yes
garbage, 14 bytes                      does not hold a valid 43-character secret            1     yes
43 bytes, bad charset (= +)            does not hold a valid 43-character secret            1     yes
valid + trailing newline (44 bytes)    does not hold a valid 43-character secret            1     yes
43 chars + embedded NUL                does not hold a valid 43-character secret            1     yes
directory                              is not a regular file                                1     yes
FIFO 600                               is not a regular file (no hang)                      1     yes
valid, mode 400                        does not have mode 600                               1     yes
valid, mode 2600                       does not have mode 600                               1     yes
valid, mode 600 (control)              (kept)                                               0     yes
```

In every case the other three missing files were still created (`600`, 43 bytes) before the non-zero exit.

SEC-01 evidence (excerpt):

```
== shim head (exit 1) ==        exit=1  setup-secrets: ERROR: could not generate a valid value for postgres_superuser_password   dir: empty
== shim base64 (exit 1) ==      exit=1  (same message)  dir: empty
== shim head (16 bytes) ==      exit=1  dir: empty
== shim base64 (garbage, 0) ==  exit=1  dir: empty
== /dev/urandom -> /dev/null ==  (unshare -rm; mount --bind)  head|wc -c = 0 ; exit=1 ; dir: empty
== /dev/urandom -> 10-byte file ==  exit=1 ; dir: empty
== full tmpfs (8 KiB) ==        head: write error: No space left on device ; exit=1 ; dir: empty
```

SEC-02 evidence (logging and inspecting docker wrappers; paths shortened):

```
WRAP-DOCKER argv: [run] [--rm] [-u] [1000:139] [-v] [repo.3pjGAz:/src:rw,Z] [--workdir] [/src] [--network] [none]
                  [ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:c00b6bd0…bbb7f] [git] [--pre-commit] [--redact] [--staged] [--verbose]
INSPECT (pre-commit hook) NetworkMode=none Networks=none Image=sha256:c00b6bd0…bbb7f Mounts=repo.3pjGAz->/src:rw=true User=1000:139
INSPECT (make scan)       NetworkMode=none Networks=none Image=sha256:c00b6bd0…bbb7f Mounts=mk.oCVQac->/repo:rw=false
staged synthetic ghp_ token: Detect hardcoded secrets....Failed / RuleID: github-pat / Secret: REDACTED / leaks found: 1 (exit 1)
```

SEC-03 evidence:

```
9026c9127e153371d7a78dfcb0c45ae2046a3d10  refs/tags/v0.17.6   astral-sh/ruff-pre-commit     (pinned: same)
3e8a8703264a2f4a69428a0aa4dcb512790b2c8c  refs/tags/v6.0.0    pre-commit/pre-commit-hooks   (pinned: same)
ffb6a759a979008c0e6dff86e39f4745a2d9eac4  refs/tags/v3.1.0    pre-commit/mirrors-prettier   (pinned: same)
83d9cd684c87d95d656c1458ef04895a7f1cbd8e  refs/tags/v8.30.1   gitleaks/gitleaks             (pinned: same)
```

### Scanner results at `7e69ead`

| Scanner | Command | Exit | Result | Raw artefact (SHA-256, scratchpad) |
|---|---|---|---|---|
| Bandit 1.9.4 | `cd apps/api && uv run bandit -r src -f json -o <scratch>/bandit.json -q` | 0 | 0 issues, 60 LOC, 0 `#nosec` | `4ced7680…5fe15f22` |
| pip-audit 2.10.1 (env) | `uv run pip-audit -f json -o …` | 0 | 80 deps, 0 vulns (`aegissoc` skipped, local) | `d05fd746…41f66` (byte-identical to round 1) |
| pip-audit (hash-checked lock export) | `uv export --frozen --all-groups --no-emit-project …` then `pip-audit -r … --require-hashes --disable-pip` | 0 | 79 deps, 0 vulns. `uv lock --check`: `Resolved 81 packages` | `55b68c13…0ed8` (byte-identical to round 1) |
| Gitleaks (pinned digest), `sg docker -c 'make scan'` on the **working tree** | as in the `Makefile` | **2** (gitleaks exit 1) | `leaks found: 1`: `generic-api-key` in **untracked** `qa/reports/sprint-01/evidence/MANIFEST.md:14`, entropy 3.55. This is a false positive: the "Generic API Key" match is a SHA-256 evidence hash next to the word `secrets` (`t01_secrets.sh … : 84009c54…`). It is not a secret and not part of the reviewed commits | `make-scan.txt` `d10eb8b7…e1`; redacted JSON `eada6c92…9e25` |
| Gitleaks `dir` on the committed tree (`git archive 7e69ead`) | `docker run --rm --network none -v <tree>:/repo:ro <pinned> dir /repo --redact` | 0 | `no leaks found` (~715 KB) | console |
| Gitleaks `git`, full history, all refs | `… git /repo --log-opts=--all --redact -f json` | 0 | `11 commits scanned`, `no leaks found`; JSON `[]` | `37517e5f…b570` |
| Semgrep, Trivy | — | — | **Not run.** Arrive with S1-T13 | — |

**Observation (process, not a T01 code defect):** once the QA evidence manifest is committed, `make scan` and the future CI secret scan will fail on the false positive above. The QA author can reword or restructure the line so that no hash sits next to a word that triggers the rule. Alternatively, the maintainer can decide on a `.gitleaks.toml` allowlist in S1-T13. I do not grant or write waivers; this is a recommendation only.

The artefact retention gap from round 1 still applies. The raw files are under the session scratchpad `rv2.YX4V5v/` only, and they are reproducible with the commands above.

### Threat-model proposals (update)

Proposals 1 and 2 above still stand. The fix implements both for S1-T01, so they can now become verification items in TC-SEC-27. Proposal 3: in SR-16's verification, add "secret files are created with a single exclusive open (no second open by path)" (SEC-09).

## Verdict (after fix cycle 1, at `7e69ead`)

| Task | Verdict | Open ≥ High | Remaining Medium | Open Low / Info |
|---|---|---|---|---|
| **S1-T01** | **No blocking findings** | 0 | **0** (SEC-01 and SEC-02 Fixed) | Low: SEC-03 (partial: archived Prettier mirror, deferred to S1-T11), **SEC-09 (new: two-open create race)**. Info: SEC-07 (partial), SEC-08 (deferred to S1-T13), SEC-10, SEC-11, SEC-12 (new). I recommend fixing SEC-09 together with SEC-10 (both are small changes in `generate`/write) before S1-T12a consumes the files. It does not block |
| **S1-T02** | **No blocking findings** | 0 | 0 | SEC-01 Fixed (Info residual: build environment not hash-locked → S1-T12). Info SEC-02 to SEC-05 unchanged |

This review approves nothing. Merge stays with the maintainer, and the QA notes are separate.

---

## Re-verification after fix cycle 2: S1-T01 (fix commits `ec6bf1d` and `d5a6fd8`)

| Field | Value |
|---|---|
| Branch | `feat/S1-T01-T02-repo-tooling-backend-skeleton` |
| Fix commits | `ec6bf1d` (`.pre-commit-config.yaml` only) and `d5a6fd8f4eca5fc3e2d22a05b1cb98e7d8cb6b46` (`scripts/setup-secrets` only). Diff: `git diff 7e69ead..d5a6fd8 -- scripts/setup-secrets`. Script SHA-256 at `d5a6fd8`: `5b402f12…82664d92` |
| Date (UTC) | 2026-11-22T02:15Z – 02:28Z |
| Environment | as above; `/bin/sh` is dash 0.5.11 (Ubuntu); bash 5 used only for comparison. Docker through `sg docker -c` |
| Method | All tests **run**, in `mktemp -d` scratch directories only. PATH shims for `od` (fixed input, failure, signals, and a simulated concurrent attacker that plants an object at the target path inside the check-to-open window), `strace` (execve/openat/write, delayed `write`), `unshare -rm` bind mounts over `/dev/urandom` and small tmpfs mounts, a throwaway git repo for the pre-commit change. The real `infrastructure/compose/secrets/` was not read, written or listed; `make scan` mounts the repository read-only, as designed |

File bounds: `ec6bf1d` changes only `.pre-commit-config.yaml`, `d5a6fd8` only `scripts/setup-secrets` (S1-T01). Within bounds. While I worked, the working tree also showed uncommitted QA round-3 files under `qa/reports/sprint-01/` (another agent's pass). I did not touch them, and they are not part of the reviewed commits.

### Status of SEC-09, SEC-10, SEC-12

| ID | Sev. | Status | Evidence |
|---|---|---|---|
| S1-T01-SEC-09 | Low | **Fixed** (residual: new Low SEC-13) | `strace` of a full run: per file, one `newfstatat` (ENOENT), then one `openat(…, O_WRONLY\|O_CREAT\|O_EXCL, 0666) = 3`, then `dup2(3,1)` and `write(1, …, 43)`. There is **no** `O_TRUNC` open and no `chmod`/`fchmodat` on any file (the only `fchmodat` is the directory, `0700`). Round-2 race repeated: every `write` was delayed 1.5 s and, during the delay, the new `postgres_superuser_password` was renamed away and replaced by a symlink to `victimA` (0 bytes, `0644`). Result: `victimA` **still 0 bytes, 0644**. The 43-byte secret went into the original inode (the renamed file, `0600`). No write or chmod reached the victim. The run exits 0 ("4 created"), and the next run rejects the swapped-in symlink ("is a symlink", exit 1) |
| S1-T01-SEC-10 | Info | **Fixed** | There is no temp file, no `mktemp`, and no `head`/`base64`/`tr` (0 matches in the script). An `od` shim sending `SIGKILL` to the script during generation leaves **0 entries** in the directory (exit 137). With `SIGTERM` the run exits 143, also with 0 entries. Fail-closed generation still holds: `od` exits 1 → exit 1, 0 files. 31-byte source → exit 1, 0 files. `/dev/urandom` bind-mounted to `/dev/null` → exit 1, 0 files. Full tmpfs (write fails) → `printf: I/O error`, exit 1, and the file this run created is removed |
| S1-T01-SEC-12 | Info | **Partially fixed** | Within one run the guard works. With a constant source (zero file through an `od` shim, and separately bind-mounted over `/dev/urandom` with `unshare -rm`), the first file is created, then "random source produced a duplicate value; refusing", exit 1. Shim tests of 305 vectors all gave exit 1 with exactly 1 file. **Across runs it does not work.** The guard only remembers values from the current run, so simply re-running gives `exit 1, 1, 1, 0`. After 4 runs there are **4 secret files with the same SHA-256** (`0f007385…`), and the last run reports "1 created, 3 already present", exit 0. Fix (cheap): add each existing value that passes validation to `seen` (it is already read into `existing`), so a duplicate against a kept file is also refused. Severity stays Info (a subverted `/dev/urandom` means the host is already compromised) |

### Other attempts to break `d5a6fd8` (no finding unless stated)

- **Encoder correctness and bias.** I compared the output with `base64 -w0 | tr '+/' '-_' | tr -d '='` for 305 inputs: all zero, all `0xff`, the bytes 0–31 and 224–255, a vector that hits the last two alphabet characters, and 300 random vectors. There were **0 mismatches**. The alphabet string is the RFC 4648 §5 URL-safe alphabet in the correct order. Each character comes from an exact 6-bit field (`>> k & 63`), with no modulo, so there is no bias. The final 2-byte group gives 3 characters, and the last carries 4 bits. This is 10 × 24 + 16 = 256 bits, and 32 bytes give 43 characters. `od -tu1` pads with spaces, not leading zeros, so no value is read as octal by `$(( ))`. The largest intermediate value is 2^24 − 1. Each value decodes back to exactly 32 bytes.
- **Entropy.** `od -An -v -N 32 -tu1 /dev/urandom` reads 32 bytes. `-v` stops `*` line suppression, and `[ "$#" -eq 32 ]` rejects short output, so nothing is truncated. 4 or 5 values per run were distinct.
- **`set -- $raw` / `case $seen`.** `od` output contains only digits and blanks, so globbing and word splitting cannot produce anything else. An `IFS=0123456789` inherited from the environment had no effect: dash and bash both reset `IFS`, and the run created 4 valid files. The `case` pattern `*" $secret_value "*` quotes the value, and values are already restricted to `[A-Za-z0-9_-]`, so the match is literal. Only a malicious `od` earlier on `PATH` could inject other words, and that is operator-level control, not a trust boundary.
- **fd 3.** An `od` shim listing `/proc/$$/fd/3` shows fd 3 **closed** in every `od` child. The secret descriptor exists only between `exec 3>` and `exec 3>&-`, and only builtins run in that window. If the caller passes in its own fd 3, the first `od` inherits it. That is harmless: it is the caller's descriptor, and the script closes it at the first create. On the write-error path, the EXIT trap's `rm` inherits fd 3, which points at the file being removed. This is harmless.
- **Argv, environment, stdout and stderr.** `strace -f -s 65535 -v -e execve` over a `--ci` run and a re-run (28 execs: `od`, `mkdir`, `chmod`, `dirname`, and for existing files `find`, `cat`, `wc`) found **0 matches** for any of the 5 values in argv or envp, stdout or stderr. `printf`, `[`, `b64char` and `valid_value` are builtins or functions. No secret variable is exported, so nothing reaches `/proc/<pid>/environ`. Values do sit in shell memory, as in any generator. Core dumps are governed by the host's `ulimit -c`.
- **Modes at creation.** `umask 077` runs before `mkdir -p`. With the caller's umask at `000`, a new nested target `a/b` and every intermediate directory came out `700`, and the file `600`. No chmod by path happens on files, so there is no window.
- **Existing-file validation** (12-case matrix rerun; each case "exit 1, unmodified, other 3 files created" unless noted): 644, empty, symlink to a valid file, dangling symlink (the victim was not created), garbage, valid value plus newline, embedded NUL, directory, FIFO (no hang), 400, 2600 → each rejected with the right message. A valid `0600` file is kept (exit 0). The result is unchanged from round 2.
- **Pre-commit change `ec6bf1d`.** The config has no top-level `exclude`. The two new `exclude: ^qa/reports/[^/]+/evidence/` keys sit only under `end-of-file-fixer` and `prettier`, and the `gitleaks-docker` hook has no `exclude`/`files`. I tested this in a throwaway repo with a copy of the config, a synthetic `ghp_` token staged in `qa/reports/sprint-99/evidence/tok.json`, and a no-EOL JSON file both inside and outside that directory. `pre-commit run gitleaks-docker` → **Failed, `RuleID: github-pat`, `File: qa/reports/sprint-99/evidence/tok.json`, leaks found: 1** (value redacted). The fixers changed only `other/noeol.json`; the evidence file kept its SHA-256. A `dir` scan of the same repo with the pinned image (as `make scan` runs it) → leaks found: 1. `make scan` has no path filter, and there is no `.gitleaks.toml`. **No scanner is weakened.**

### New findings in `d5a6fd8`

| ID | Severity | Location | Ref | Finding | Fix suggestion |
|---|---|---|---|---|---|
| S1-T01-SEC-13 | Low | `scripts/setup-secrets:159-166` (`set -C; exec 3> "$file"`) and its comment | SR-16, T-20 | **noclobber is not a pure `O_EXCL` open.** dash (and bash) first runs `stat()`, which follows symlinks. If the path exists and is *not a regular file*, the shell opens it `O_WRONLY` without `O_EXCL` and keeps the descriptor. Using an `od` shim as a simulated concurrent attacker, I planted an object in the window between the `[ -e ]` check and the open (the window includes the whole `od` run). Results: **symlink → FIFO** and **plain FIFO**: the attacker's reader got the **43-byte secret**, and the run exited 0 with "4 created". **Symlink → `/dev/null`**: the value was discarded, exit 0, "4 created" (the next run flags "is a symlink"). **Symlink → `/dev/full`**: `printf: I/O error`, exit 1, and the EXIT trap then **removed the planted symlink, which this run did not create** (its target was untouched). Planted regular file, symlink to a regular file, dangling symlink, or symlink to a directory: the open failed, exit 2, nothing was written or removed, and the victim was untouched. The precondition is the same as for SEC-09: same UID with write access to the `0700` directory, so the attacker could read the secrets anyway. The code comment "it fails if the path exists, even as a symlink" is therefore not accurate | After the open, check the **descriptor**, not the path, and only then claim the file: `[ -f /dev/fd/3 ] && [ ! -s /dev/fd/3 ] \|\| { exec 3>&-; echo …; exit 1; }`, followed by `created_file=$file`. Tested in dash: a symlink to a FIFO is detected as "not regular", so the run refuses instead of writing. Opening a FIFO with no reader still blocks, so the residual is a hang, not a leak. Correct the comment. Add a test: a FIFO planted at the path is never written to |
| S1-T01-SEC-14 | Info | `scripts/setup-secrets:160-164` | SR-16 | The "could not create" branch is dead code in dash. A failing redirection on the special built-in `exec` aborts the non-interactive shell **before** the `if` runs, and `2>/dev/null` hides the shell's own message. Planted regular file, dangling symlink, symlink to a directory or full inode table (tmpfs `nr_inodes=3`) each gave **exit 2 with no output at all**. bash gives exit 1 with the message; `bash --posix` gives exit 1, silent. The run still fails closed, so only the diagnostics are lost | Use `command exec 3> "$file"` (POSIX: `command` removes the special-built-in fatal-error rule). Tested in dash, bash and `bash --posix`: the error branch is reached and the script continues to its own `exit 1`. Drop `2>/dev/null` so the cause (EEXIST, ENOSPC, …) is shown |
| S1-T01-SEC-15 | Info | `scripts/setup-secrets` (whole generation path) | SR-16, SR log hygiene | **The xtrace leaks the secret values.** `sh -x scripts/setup-secrets <scratch>` writes each value in full to stderr, on 5–8 trace lines per value (`secret_value=…`, `seen=…`, `printf %s …`), plus the raw decimal bytes (`set -- 23 237 …`) and every `out=` and `ch=` step. Under bash, the trace can also be enabled from the environment (`SHELLOPTS=xtrace` or a `BASH_ENV` that runs `set -x`): 5 lines per value. Under dash, neither `SHELLOPTS` nor `ENV` has any effect on a non-interactive shell (0 lines). The `Makefile` runs the script through its `#!/bin/sh` shebang. This is pre-existing (round-1 and round-2 versions also traced `printf '%s' "$secret_value"`) and needs an operator to turn tracing on. It matters if a CI job ever runs `make setup` or the script with `-x` or under bash with tracing, because the values would land in CI logs | Add `set +x` right after `set -eu`. This works even when the script is started as `sh -x`, and limits the trace to the first line. Optionally, state in the header: "do not run under xtrace" |
| S1-T01-SEC-16 | Info | `scripts/setup-secrets:111,153` | SR-16 | `seen` keeps every value generated in the run and is never cleared. In a normal run this only matters for process memory. If the script is **sourced** (`. scripts/setup-secrets`, which is not supported), `seen` stays in the caller's shell with all 4 values, and `umask 077`, `set -eu` and the traps remain set. dash also ignores arguments given to `.`, and `$0` is the caller, so the target resolves relative to the caller's working directory (in my scratch test it went to `<cwd>/../infrastructure/compose/secrets`) | `seen=""` before the final `echo`. Optionally, refuse to be sourced. Low priority |

### Scanner results at `d5a6fd8`

| Scanner | Command | Exit | Result | Raw artefact (SHA-256, session scratchpad `scan-d5a6fd8.9DONQS/`) |
|---|---|---|---|---|
| Bandit 1.9.4 | `cd apps/api && uv run bandit -r src -f json -o … -q` | 0 | 0 issues, 60 LOC, 0 `#nosec` | `bandit.json` `9f96d9b7…e960efd2a3` |
| pip-audit 2.10.1 (env) | `uv run pip-audit -f json -o …` | 0 | 80 deps, 0 vulns | `pip-audit.json` `d05fd746…41f66` (byte-identical to round 2) |
| pip-audit (hash-checked lock export) | `uv export --frozen --all-groups --no-emit-project`, then `pip-audit -r … --require-hashes --disable-pip`. `uv lock --check`: `Resolved 81 packages` | 0 | 79 deps, 0 vulns | `pip-audit-locked.json` `55b68c13…0ed8` (byte-identical to round 2) |
| Gitleaks (pinned digest), `sg docker -c 'make scan'` on the working tree | as in the `Makefile` | 0 | `scanned ~1.04 MB`, **no leaks found**. The round-2 false positive in `MANIFEST.md` no longer triggers | `make-scan.txt` `e1565bb9…c011b` |
| Gitleaks `dir` on the committed tree (`git archive d5a6fd8`) | `docker run --rm --network none -v <tree>:/repo:ro <pinned> dir /repo --redact` | 0 | ~928 KB, no leaks found | console (`tree.log`) |
| Gitleaks `git`, full history, all refs (mirror clone) | `… git /repo --log-opts=--all --redact` | 0 | 16 commits scanned, no leaks found | console (`history.log`) |
| Semgrep, Trivy | — | — | **Not run.** They arrive with S1-T13 | — |

The artefact retention gap still applies: the raw files are in the session scratchpad only, and they can be reproduced with the commands above.

### Threat-model proposals (update)

Proposal 3 (single exclusive open) is met for regular files. I propose to extend it: "the opened descriptor is verified to be a new, empty regular file before the value is written; a non-regular object at the path is refused" (SEC-13). Proposal 4: SR-16 verification adds "secret generators disable shell tracing and never write values to stdout or stderr, including under `-x`" (SEC-15).

## Verdict (after fix cycle 2, at `d5a6fd8`)

| Task | Verdict | Open ≥ High | Open Medium | Open Low / Info |
|---|---|---|---|---|
| **S1-T01** | **No blocking findings** | 0 | **0** | Low: SEC-03 (partial, deferred to S1-T11), **SEC-13 (new: noclobber opens a planted FIFO or device; same-UID precondition)**. Info: SEC-07 (partial), SEC-08 (deferred to S1-T13), SEC-11, SEC-12 (partial: no guard across runs), SEC-14 (new: silent exit 2), SEC-15 (new: xtrace leaks values), SEC-16 (new: `seen` not cleared). SEC-09 and SEC-10 are **Fixed**. I recommend SEC-13, SEC-14, SEC-15 and the SEC-12 cross-run check as one small follow-up before S1-T12a consumes the files. None of them blocks |
| **S1-T02** | **No blocking findings** | 0 | 0 | Unchanged since round 2. `d5a6fd8` and `ec6bf1d` do not touch S1-T02 paths. Bandit and pip-audit results are identical |

This review approves nothing. Merge stays with the maintainer, and the QA notes are separate.

---

## S1-T03 — Core (log redaction, error model, request id, cursor validation, config secret loading)

| Field | Value |
|---|---|
| Branch | `feat/S1-T03-core` |
| Commit | `61bbdd6` (`61bbdd6103b8a40fbbb656a9934fdd40fb01a3f3`). Diff reviewed: `git diff 8489ea3..61bbdd6` (14 files, +1703/−6) |
| Date (UTC) | 2026-11-22T02:58Z – 03:01Z |
| Environment | Linux 6.8.0-149-generic, Python 3.12 (project venv), uv 0.13.7, Docker 29.1.3. Libraries in the venv: structlog 26.1.0, pydantic 2.14.4, pydantic-settings 2.16.3, FastAPI 0.165.0, Starlette 1.10.0, uvicorn 0.54.0 |
| Method | Clean export with `git archive 61bbdd6 apps/api` into the session scratchpad. Attack scripts ran against that copy with `python -I`. A throwaway FastAPI app wired `RequestIdMiddleware` and `install_error_handlers` the way `main.py` is expected to, and ran under uvicorn on `127.0.0.1:18731`, driven by a raw-socket client. The real secrets directory was never read. Synthetic secret marker: `S3CRET-VALUE-xyz` |
| Requirements | SR-18, SR-16, SR-13, SR-09, SR-22 (context only); AC-PLAT-10; audit finding B-2; threats T-22, T-08, T-14, T-25 |
| Producer | security-reviewer agent |

**Status: No blocking findings** (0 Critical, 0 High, **1 Medium**, 7 Low, 8 Info). I recommend closing **S1-T03-SEC-01** before any endpoint that handles credentials (S1-T06) merges. The fix can land in this task or in the `main.py` wiring (S1-T05/S1-T09), but it must be tracked.

### File-bounds check (§3)

`git diff --name-only 8489ea3..61bbdd6 | grep -vE '^apps/api/(src/aegissoc/core/|tests/unit/core/)'` prints nothing, so every path is within S1-T03 bounds. `uv.lock` and `pyproject.toml` are unchanged (`git diff --quiet 8489ea3 61bbdd6 -- uv.lock pyproject.toml` → exit 0). The only new import, `uuid6` in `core/ids.py`, was already a declared and locked dependency from S1-T02 (MIT), so this task adds no dependency. The working tree has an untracked `qa/api/core_s1t03/`. It is not part of `61bbdd6` and I did not review it.

### Scanner results

| Scanner | Command | Exit | Result | Raw artefact (SHA-256) |
|---|---|---|---|---|
| Bandit 1.9.4 | `cd apps/api && uv run bandit -r src -f json -o <scratch>/bandit.json -q` | 0 | 0 issues, 540 LOC, 0 `#nosec` | `bandit.json` `7504d385…6bb0c` |
| pip-audit (installed env) | `uv run pip-audit -f json -o <scratch>/pip-audit-env.json` | 0 | 80 deps, 0 known vulnerabilities | `pip-audit-env.json` `d05fd746…1f66` (identical to the S1-T02 run) |
| pip-audit (lockfile, hash-checked) | `uv export --frozen --all-groups --no-emit-project …` then `pip-audit -r req-locked.txt --require-hashes --disable-pip` | 0 | 79 deps, 0 known vulnerabilities | `pip-audit-lock.json` `55b68c13…d0d8` (identical to the S1-T02 run) |
| Gitleaks v8.30.1 (working tree) | `sg docker -c 'make scan'` (digest-pinned image, `--network none`, `:ro`) | 0 | `scanned ~1367225 bytes (1.37 MB) in 519ms` / `no leaks found` | console only |
| Gitleaks v8.30.1 (commit range) | `docker run --rm --network none -v "$PWD:/repo:ro" ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:c00b6bd0… git /repo --log-opts=8489ea3..61bbdd6 --redact --no-banner` | 0 | `1 commits scanned.` / `no leaks found` | console only |
| Semgrep, Trivy | — | — | **Not run.** They arrive with S1-T13 | — |
| pnpm audit | — | — | Not applicable (no frontend change) | — |

Attack-run outputs (scratchpad, `…/scratchpad/t03/`): `log_attack.out` `cc7aa112…e110`, `log_blowup.out` `563dad2f…d0c7`, `client.out` `c7aaf91e…e2ba`, `uvicorn.stdout` `38bdc997…69ef`, `uvicorn.stderr` `50e8a446…ef88`, `cursor_attack.out` `8fcadf0d…d6f8`, `config_attack.out` `874a0950…40eb`, `fifo.out` `296a37e9…856c`. The same artefact retention gap as in earlier rounds applies: the orchestrator or QA should re-produce and commit them under `qa/reports/sprint-01/evidence/` if they are needed.

### What was verified (no finding)

- **Redaction at depth and case:** `PASSWORD=`, nested `{"a":{"b":{"password":…}}}`, `[{"password":…}]`, bytes values and bytes keys (`{b"password": …}`), header dicts (`X-CSRF-Token`, `set-cookie`, `Authorization`), `.bind(session_id=…)` and `contextvars.bind_contextvars(csrf_token=…)` are all dropped. A non-string key whose `__str__` returns `"password"` is dropped too, because `str(key)` is matched.
- **Logger created before `configure_logging()` is redacted:** `early = get_logger("early")` before configuration, then `early.info("e", password=S)` → `{"logger_name": "early", "event": "e", …}`, with no value.
- **Log forging:** newlines, CR, ANSI ESC, U+2028 and U+0085 in values **and keys** are JSON-escaped (`"k\n{\"f\":1}": "v"`, `"\u001b[31m"`, `"k y"`). No second line can be forged (SR-18).
- **Depth and cycles:** a 5000-deep dict and self-referencing dicts and lists stop at depth 8 with `"[truncated]"`. No `RecursionError`.
- **`format_exc_info` does not print frame locals:** `password = S` as a local in the raising frame does not appear (structlog's plain `format_exc` path).
- **Error model, 4xx:** 422 bodies carry only `loc`/`msg`/`type`. Pydantic `input` and `ctx` are dropped, so neither the submitted `password` nor the `extra` field value is reflected. The same holds for query validation (`?limit=S3CRET…` → `int_parsing`, no value). Malformed JSON → 400 `bad-request` "Malformed JSON body", with no parser position or excerpt. A non-string `HTTPException.detail` (`{"secret": …}`) is replaced by the title. `instance` never includes the query string.
- **Error model, 500:** the body is the fixed `internal-error` problem: no trace, no class, no message, no path to a source file. The app's own log line has `error_type`, `path` and `request_id` only. The 500 response still carries `X-Request-ID`.
- **Response splitting:** an `HTTPException` header value with `\r\nSet-Cookie:` is refused by the server (`RuntimeError: Invalid HTTP header value.`), and the connection closes with no response. No header is injected.
- **X-Request-ID:** `fullmatch` on `[A-Za-z0-9-]{8,64}`. Too short, 65 characters, `<script>`, a space, `!` and Latin-1 `é` are all replaced by a fresh UUIDv7 and never echoed. ASGI lowercases header names, so `X-REQUEST-ID` works the same. With duplicate headers the first one wins, and if it is invalid a fresh id is generated (the second one is not used as a fallback). A handler-set `X-Request-ID` is replaced: only one header goes out. `request_id` is only ever written into JSON or one header value from a restricted alphabet, so there is no log or header injection.
- **Cursor (B-2):** the 512-character length and alphabet check runs **before** any decode (1,000,000 characters → 400 in 41 µs). Padding, a non-canonical last base64 character, a BOM, invalid UTF-8, a list payload, duplicate keys, extra or missing keys, `v` of `true` or `1.0`, a bool, float, `NaN`, `1e2`, or `"5"` where an int is expected, `2**63`, a braced or uppercase UUID, naive or `+01:00` or `Z` datetimes, and a key type that differs from the sort field are all rejected with the fixed `"Invalid cursor"` (the input is never echoed, the chained exception is suppressed with `from None`). A 300-digit integer is rejected (it is out of range, well below Python's int-parsing limit). Nesting depth is bounded by the length cap, so there is no `RecursionError`. `decode_cursor` returns typed values (`str | int | datetime`, `uuid.UUID`). No module in `core/` builds SQL text (`git diff … | grep -E 'text\(|execute\('` finds nothing), so forging a cursor gives only what a bound parameter under the caller's permissions allows. Timing does not matter: there is no secret to compare against.
- **Config:** `extra="forbid"` plus `PrivateAttr` means neither `Settings(_database_password=…)` nor `Settings(database_password=…)` is accepted, and `AEGIS_DATABASE_PASSWORD` / `AEGIS__DATABASE_PASSWORD` in the environment have no effect (the secret still comes from the file). `repr`, `model_dump`, `model_dump_json`, `vars()` and `__pydantic_private__`'s string form do not contain the secret. Errors for a missing file, a directory, `/dev/null`, a file holding only `"\n"` and non-UTF-8 content name the path only. The `UnicodeDecodeError` (which would show bytes) is suppressed with `from None`, and the formatted traceback contains neither the content nor the decode error. `AEGIS_ENV=production` is rejected (`Literal["local","ci"]`). In `local`, missing `*_FILE` values fail closed.

### Findings

| ID | Severity | Location | Ref | Finding | Fix suggestion |
|---|---|---|---|---|---|
| **S1-T03-SEC-01** | **Medium** | `core/errors.py` `_handle_unhandled` (module docstring: "The server log gets the exception class and the request id, not the message"); `core/logging.py` processor order (`redact_sensitive` before `format_exc_info`) | SR-18, T-22 | **Unhandled exceptions reach the server log with their full message and traceback, unredacted and not as JSON.** Starlette's `ServerErrorMiddleware` calls the `Exception` handler, sends the 500, and then **re-raises** so the server can log it. uvicorn's `uvicorn.error` logger then writes `Exception in ASGI application` plus the full traceback to stderr. That includes the exception message and, for a Pydantic `ValidationError` raised inside a service, `input_value='<the submitted value>'`. So the docstring's guarantee does not hold in a real deployment. Realistic carriers of secrets in exception text: Pydantic errors on internal models built from request data (login bodies in S1-T06), and driver errors (asyncpg `DETAIL: Key (…)=(…)`). The same applies inside the app: any `log.exception(…)` / `exc_info=True` renders the message via `format_exc_info`, which runs **after** redaction, so the `exception` field is never redacted | (a) In `configure_logging`, take over stdlib logging: route `uvicorn`, `uvicorn.error` and the root logger through `structlog.stdlib.ProcessorFormatter` with the same JSON and redaction chain, and drop `exc_info` on `uvicorn.error` "Exception in ASGI application" records (the app's own line already gives class plus request id). Alternatively, (b) add an outermost pure-ASGI guard that swallows the re-raised exception after the 500 has been sent. Also decide on a policy for `exc_info` in app logs: either strip `exc_info` and log only `error_type`, or put a processor after `format_exc_info` that keeps only the frame list and the exception class. Add a test: a route raising `ValueError("…S3CRET…")` and an internal `ValidationError` with a password input; capture **stdout and stderr** of the server/app logging and assert the marker is absent (proposed TC under TC-SEC-20) |
| S1-T03-SEC-02 | Low | uvicorn access log (wiring outside `core/`, noted here because the `instance` design relies on it) | SR-18, T-22 | The uvicorn access log is plain text (not JSON) and records the **full query string**: `"GET /boom?token=S3CRET-VALUE-xyz HTTP/1.1" 500`. `errors.py` deliberately keeps query strings out of `instance` because "they may hold tokens", but the access log writes them anyway | In S1-T05/S1-T09 wiring, run uvicorn with `--no-access-log` (or a `log_config`) and emit a JSON access line from middleware with method, path (no query), status, duration and `request_id`. Or redact query values whose names match the sensitive pattern |
| S1-T03-SEC-03 | Low | `core/logging.py` `_SENSITIVE_KEY`, `_clean` | SR-18 | **Gaps in the key denylist.** Not redacted: `pwd`, `passwd`, `credential(s)`, bare `csrf`, `private_key`, `ingest_key` and other `*_key` names, `anthropic_key` (SR-18 names Anthropic keys explicitly), and `dsn` (`postgresql://u:S3CRET@h/db` was logged verbatim). Keys are not normalised, so `ｐａｓｓｗｏｒｄ` (fullwidth), `pass​word` and `pаssword` (Cyrillic а) bypass it. That matters only where keys come from untrusted data, such as a logged header or JSON dict. `set`/`frozenset` values are not traversed and render as `repr`: `{("password", S)}` gave `"{('password', 'S3CRET-VALUE-xyz')}"`. Sequences of pairs (`[("password", S)]`) are not treated as mappings | Extend the pattern to `passw(or)?d\|pwd\|secret\|token\|session\|authori[sz]ation\|cookie\|csrf\|credential\|api[-_]?key\|private[-_]?key\|(^\|[-_])key$\|dsn`. Normalise the key first: `unicodedata.normalize("NFKC", str(key))`, then remove `Cf` characters, then casefold. Traverse `set`/`frozenset` as lists. Add the cases above to `test_core_logging.py` |
| S1-T03-SEC-04 | Low | `core/logging.py` `_clean` | T-14 | **No breadth or size bound, so shared references expand exponentially.** Depth is capped at 8, but a dict that references itself under *n* keys expands to n⁸ nodes: n=5 → 1.7 MB in 0.05 s, n=7 → 17.4 MB in 0.53 s, n=10 → about 10⁸ nodes (not run). A flat 2,000,000-item list → a 16.9 MB log line in 0.86 s. JSON parsed from a request cannot build shared references, so an attacker can trigger this only if code logs a large untrusted collection. That is why the severity is Low | Cap the items per container (for example 100, then `"[truncated]"`) and the total node budget per event. Track `id()` of containers already visited and emit `"[cycle]"`. Optionally cap the length of rendered strings |
| S1-T03-SEC-05 | Low | `core/pagination.py` `_decode`, `_decode_key` | B-2, SR-09 | **The decoder is not as strict as its docstring claims, and some `str` keys will fail later as a 500.** Accepted although `encode_cursor` never produces them: whitespace JSON (`{"v": 1, "k": 5, …}`), reordered keys, `A` escapes, `-0`. Also accepted as `str` keys: `"a\u0000b"` (PostgreSQL `text` rejects NUL, so the bound parameter will raise a driver error and the client gets a 500 instead of a 400) and a lone surrogate `"\ud800"` (cannot be UTF-8 encoded by the driver, also a 500). The nil UUID is accepted (harmless). There is no security bypass because the values stay bound parameters, but it is an availability and error-hygiene gap and the docstring is wrong | After parsing, rebuild with `encode_cursor(key, id)` and require `== token`. That enforces the canonical form fully, and a surrogate raises `UnicodeEncodeError` (a `ValueError`) → 400. Additionally reject `str` keys that contain `\x00`–`\x1f` or surrogates. Add tests |
| S1-T03-SEC-06 | Low | `core/config.py` `read_secret_file` | SR-16, T-14 | `path.read_bytes()` has **no type or size check**. A FIFO blocks startup forever (`timeout 5 … Settings()` → exit 124). A 200 MiB file of NUL bytes is accepted as the password (432 MiB RSS, 0.72 s). `/dev/zero` would exhaust memory. A symlink is followed (`link → /etc/hostname` was accepted). The path is operator-controlled (an environment variable or Docker secret), so there is no remote trust boundary | `fd = os.open(path, os.O_RDONLY \| os.O_NONBLOCK \| os.O_CLOEXEC)`. Use `os.fstat` and require `S_ISREG`, then read at most `MAX_SECRET_BYTES + 1` (for example 4096) and reject anything longer. Reject NUL and control characters in the value. Following a symlink is fine, because Docker secrets can be symlinks; just document it |
| S1-T03-SEC-07 | Low | `core/config.py` `database_url`, `redis_url` (plain `str`) | SR-16, SR-18 | **A secret can still enter through an environment variable.** `AEGIS_DATABASE_URL=postgresql://u:S3CRET@h/db` is accepted and printed by `repr(settings)` (`leak_in_repr=True`), and it would appear in a `ValidationError` `input_value` and in any log of the settings. That contradicts the module docstring ("Secrets are never read from plain environment variables") | Validate both URLs and reject any URL with a password in its userinfo (`urllib.parse.urlsplit(u).password is not None` → `ValueError("… must not contain a password; use *_PASSWORD_FILE")`, without echoing the URL). Or type them as `SecretStr` |
| S1-T03-SEC-08 | Low | `core/logging.py` (documented limit) | SR-18 | **Redaction covers keys only, never text.** `log.info(f"login password={S}")` and `exception="password=…"` are logged verbatim. I find this limit **acceptable** as a design choice, because redacting free text is unreliable. It is only safe with a mechanical guard, because SR-18 is a hard requirement | When S1-T13 adds `.semgrep/aegissoc.yml`, add a rule against f-strings, `%` or `.format` in the first argument of `log.*` calls, and against passing `password`/`token`/`secret` variables as positional arguments. Until then, reviewers check it by hand |
| S1-T03-SEC-09 | Info | `core/errors.py` `_slug_and_title` | AC-PLAT-10 | Statuses outside the table map to `bad-request` / "Bad request" while keeping their own status: 405 → `{"type": ".../bad-request", "title": "Bad request", "status": 405, "detail": "Method Not Allowed"}`, and 418 likewise. `type`/`title` no longer match the status. This is not a disclosure | Add `405 method-not-allowed` (keep `Allow`), or map unknown 4xx codes to a generic `client-error` slug. Ask the maintainer whether API_SPECIFICATION §1.3 should list 405 |
| S1-T03-SEC-10 | Info | `core/errors.py` `_handle_http_exception` | T-22 | `HTTPException.detail` (when it is a string) and `.headers` pass through verbatim. Both are developer-controlled today (Starlette's own details are "Not Found" and "Method Not Allowed"), but a future `HTTPException(400, f"user {name} …")` would reflect input or internal data | Prefer `DomainError` subclasses with fixed details in services. Consider passing through only an allowlist of headers (`Allow`, `Retry-After`, `WWW-Authenticate`) |
| S1-T03-SEC-11 | Info | `core/errors.py` `instance=request.url.path` | T-22 | `instance` reflects the percent-decoded path, including control characters (`"/S3CRET-VALUE-xyzX-Injected: 1\u001b[31m"`) and long paths (a 20,000-character path → a 20,173-byte body). It is JSON-encoded, sent only to the same requester and bounded by the server's request-line limit. **Acceptable** | Optionally truncate `instance` (for example to 256 characters) |
| S1-T03-SEC-12 | Info | `core/request_id.py` | T-08 | A client can choose any valid id, including one that another request already used, so correlation by `request_id` can be confused on purpose. This is inherent to accepting client ids | When the trusted-proxy work lands (S1-T09), consider accepting client ids only from the trusted proxy, or log both `client_request_id` and a server-generated id |
| S1-T03-SEC-13 | Info | `core/config.py` | SR-13 | `SecretStr` pickles in plain text (`pickle.dumps(settings)` contains the secret). `model_copy(update={"_database_password": "X"})` can overwrite a private secret. `copy.deepcopy` keeps the secret. None of this is reachable from input, and SR-13 already forbids `pickle` | No action beyond SR-13 enforcement (Bandit/Semgrep) |
| S1-T03-SEC-14 | Info | `core/config.py` | SR-16 | `AEGIS_DATABASE_PASSWORD=…` is silently ignored instead of rejected, so an operator who sets it believes it took effect (it fails safe, because the file is still required) | Optionally fail fast if `AEGIS_*_PASSWORD` (without `_FILE`) is present |
| S1-T03-SEC-15 | Info | `core/config.py` `read_secret_file` | SR-16 | Only one `\n` is stripped, so a CRLF-terminated file keeps a trailing `\r` in the password ("crlf value ends with CR: True"). This only causes an authentication failure, not a disclosure | Document it, or also strip one `\r\n` |
| S1-T03-SEC-16 | Info | `core/logging.py` `get_logger` | — | `log.info("e", event=…)` raises `TypeError` (structlog's `event` positional). A future handler logging a dict that contains `event` would turn a log call into a 500 | Avoid `**untrusted_dict` in log calls (reviewer checklist item) |

**Evidence for S1-T03-SEC-01** (throwaway app under uvicorn 0.54.0; `/boom` raises `RuntimeError("db password=S3CRET-VALUE-xyz …")`, `/boom-validation` builds a model with an invalid password):

```
$ client: GET /boom?token=S3CRET-VALUE-xyz
HTTP/1.1 500 Internal Server Error
x-request-id: 01a20131-7162-7f22-b289-229d67168563
content-type: application/problem+json
{"type":"https://aegissoc.local/problems/internal-error","title":"Internal server error","status":500,"detail":"An internal error occurred.","instance":"/boom","request_id":"01a20131-…"}
leak S3CRET: False                                   <- response body is clean

uvicorn.stdout:
{"logger_name": "aegissoc.errors", "error_type": "RuntimeError", "path": "/boom", "request_id": "01a20131-…", "event": "unhandled_exception", "level": "error", …}
INFO:     127.0.0.1:54190 - "GET /boom?token=S3CRET-VALUE-xyz HTTP/1.1" 500 Internal Server Error   <- SEC-02

uvicorn.stderr:
5:   ERROR:    Exception in ASGI application
       (… full traceback, starlette/middleware/errors.py line 186 re-raise …)
60:  RuntimeError: db password=S3CRET-VALUE-xyz at /srv/app/x.py
61:  ERROR:    Exception in ASGI application
119: pydantic_core._pydantic_core.ValidationError: 2 validation errors for Login
124:   String should have at least 100 characters [type=string_too_short, input_value='S3CRET-VALUE-xyz', input_type=str]
```

App logger with `exc_info` (`log_attack.out`): `[exc_info-msg] leak=True … "exception": "Traceback (most recent call last):\n … ValueError: bad password S3CRET-VALUE-xyz"`.

**Evidence for S1-T03-SEC-03 / SEC-08** (`log_attack.out`, excerpts):

```
[pwd] leak=True        [passwd] leak=True     [credential] leak=True   [csrf] leak=True
[api_key: ingest_key] leak=True   [private_key] leak=True   [dsn] leak=True
[fullwidth] leak=True  out='{… "ｐａｓｓｗｏｒｄ": "S3CRET-VALUE-xyz" …}'
[zero-width] leak=True [cyrillic-a] leak=True
[set-of-tuples] leak=True out='{… "a": "{(\'password\', \'S3CRET-VALUE-xyz\')}" …}'
[obj-repr] leak=True   (object whose __repr__ prints a secret; documented limit)
[event-text] leak=True out='{… "event": "login password=S3CRET-VALUE-xyz" …}'   (documented limit, SEC-08)
[upper] leak=False  [nested-dict] leak=False  [list-dict] leak=False  [bytes-key] leak=False  [early-logger] leak=False
```

**Evidence for S1-T03-SEC-04** (`log_blowup.out`): `self-ref dict with 5 keys: 0.05s, 1699313 bytes` / `7 keys: 0.53s, 17431755 bytes`; `big list time 0.86 s, bytes 16888993`.

**Evidence for S1-T03-SEC-05** (`cursor_attack.out`):

```
[whitespace json] ACCEPTED key=5      [reordered keys] ACCEPTED key=5     [unicode escape in str] ACCEPTED key='A'
[NUL in str key] ACCEPTED key='a\x00b'                 [lone surrogate] ACCEPTED key='\ud800'
[-0] ACCEPTED key=0                    [uuid nil] ACCEPTED
[bool] / [float] / [NaN int] / [1e2 int] / [int as str] / [int64 max+1] / [dup key] / [uuid upper] / [dt +01] / [dt Z] / [padding] / [long 1e6] -> 400 detail='Invalid cursor'
```

**Evidence for S1-T03-SEC-06 / SEC-07** (`config_attack.out`, `fifo.out`):

```
[symlink to /etc/hostname] OK …
[200MiB sparse file] OK …   time 0.72 s maxrss MiB 432
[url with password] OK repr=Settings(env='local', database_url='postgresql://u:S3CRET-VALUE-xyz@h/db', …)  leak_in_repr=True
FIFO: exit=124 (124 = killed by timeout, i.e. blocked on FIFO)
[binary content] ValidationError leak=False: "… secret file …/bin is not valid UTF-8 [type=value_error, input_value={'database_password_file'…}, …]"
[traceback of binary-content failure] leak: False | mentions UnicodeDecodeError: False
```

### Threat-model change proposals (for the maintainer; not applied)

1. **T-22** mitigations: add "server and third-party loggers (uvicorn, stdlib) are routed through the same JSON and redaction pipeline; server tracebacks for handled 500s are suppressed or reduced to class plus request id". Add a test case under TC-SEC-20: "a 500 caused by an exception whose message or Pydantic input contains a marker secret leaves no trace of it on stdout or stderr".
2. **SR-18** verification: "access logs omit query strings (or redact sensitive parameters)" (SEC-02), and "sensitive-key matching is Unicode-normalised" (SEC-03).
3. **SR-16**: "connection URLs must not contain passwords; secret files must be regular files of bounded size" (SEC-06, SEC-07).

### Verdict (S1-T03 at `61bbdd6`)

| Task | Verdict | Open ≥ High | Open Medium | Open Low / Info |
|---|---|---|---|---|
| **S1-T03** | **No blocking findings** | **0** | **1**: SEC-01 (unhandled-exception message and Pydantic `input_value` reach uvicorn's stderr traceback; app `exc_info` is unredacted) | Low: SEC-02 (access log query string), SEC-03 (denylist gaps, Unicode, sets), SEC-04 (exponential expansion / no size cap), SEC-05 (non-canonical cursors; NUL/surrogate str keys → future 500), SEC-06 (secret file type/size), SEC-07 (password in URL settings), SEC-08 (text redaction limit, accepted with Semgrep follow-up). Info: SEC-09 … SEC-16 |

SEC-01 should be fixed, or tracked with an owner and a test, before S1-T06 (authentication) merges, because that is the first code path where secrets reach exceptions. This review approves nothing. Merge stays with the maintainer, and the QA notes are separate.

---

## Re-verification at `e9d1473`: S1-T03 (fix commit for S1-T03-SEC-01 … SEC-16)

| Field | Value |
|---|---|
| Branch | `feat/S1-T03-core` |
| Commit | `e9d1473` (`e9d1473883d5d33b86791ab0a4e8b49ac9e60e15`). Diff reviewed: `git diff 61bbdd6..e9d1473` (10 files, +625/−47; source: `core/config.py`, `core/errors.py`, `core/logging.py`, `core/pagination.py`, `core/request_id.py`) |
| Date (UTC) | 2026-11-22T18:36Z – 18:38Z |
| Environment | Same as the initial S1-T03 review (Python 3.12 project venv; structlog 26.1.0, pydantic 2.14.4, FastAPI 0.165.0, Starlette 1.10.0, uvicorn 0.54.0) |
| Method | Clean export with `git archive e9d1473 apps/api` into the session scratchpad. All attack scripts were rewritten (the earlier scratchpad was gone) and ran with `python -I` against the export. A throwaway FastAPI app wired `RequestIdMiddleware` and `install_error_handlers` and ran under `uvicorn.run(...)` with uvicorn's default log config on `127.0.0.1:18732`, driven by a raw-socket client. Secret files were synthetic files in the scratchpad; the real secrets directory was never read. Marker: `S3CRET-VALUE-xyz` |
| Requirements | SR-18, SR-16, SR-09; AC-PLAT-10; B-2; T-22, T-14, T-08 |
| Producer | security-reviewer agent |

**Status: No blocking findings** (0 Critical, 0 High, **1 Medium still open: SEC-01, now narrowed to the server/stdlib path**, 4 Low open or partially fixed, 1 new Low, Info items below).

### File-bounds check (§3)

`git diff --name-only 61bbdd6..e9d1473 | grep -vE '^apps/api/(src/aegissoc/core/|tests/unit/core/)'` prints nothing (exit 1), so the commit stays within S1-T03 bounds. `uv.lock` and `pyproject.toml` are unchanged (`git diff --quiet 61bbdd6 e9d1473 -- uv.lock apps/api/pyproject.toml pyproject.toml` → exit 0). The new imports (`os`, `stat`, `traceback`, `unicodedata`, `urllib.parse`) are stdlib, so no dependency was added. The untracked `qa/**` files in the working tree are not part of `e9d1473` and I did not review them.

### SEC-01: plain answer

**It is not closed by this commit. It is partially fixed.**

- **Fixed (app logger):** `render_exception` replaces structlog's `format_exc_info` and keeps only the frames and the exception type. `log.exception(...)`, `exc_info=True`, `exc_info=<exception>`, `exc_info=sys.exc_info()`, chained exceptions, `ExceptionGroup`, `add_note()` and a Pydantic `ValidationError` with a password input all leave no marker in the app's JSON line (`log_attack.out`, nine `exc_info-*` cases, all `leak=False`). Under uvicorn, `/app-exc` (handled `ValueError("bad password …")` + `log.exception`) gives a JSON line with frames and `ValueError` only.
- **Still open (server path):** the fix does nothing about stdlib or uvicorn logging. `configure_logging` still configures structlog only (`PrintLoggerFactory`), and Starlette's `ServerErrorMiddleware` still re-raises after the 500 is sent. uvicorn's `uvicorn.error` logger still writes `Exception in ASGI application` and the full traceback, **with the exception message and the Pydantic `input_value`**, to stderr as plain text:

```
uvicorn.stderr (e9d1473, default uvicorn log config):
5:   ERROR:    Exception in ASGI application
60:  RuntimeError: db password=S3CRET-VALUE-xyz at /srv/app/x.py
61:  ERROR:    Exception in ASGI application
119: pydantic_core._pydantic_core.ValidationError: 1 validation error for Login
121:   String should have at least 100 characters [type=string_too_short, input_value='S3CRET-VALUE-xyz', input_type=str]
```

The response bodies are still clean (`leak S3CRET in response: False` for `/boom` and `/boom-validation`), and the app's own `unhandled_exception` line still holds only `error_type`, `path` and `request_id`. The `core/errors.py` module docstring still says "The server log gets the exception class and the request id, not the message". That is still false for a real deployment.

**What closing it needs, and who owns each part.** The remaining work spans three file sets:

1. **Core code (S1-T03 bounds, so it can be done in this task):** a stdlib bridge in `core/logging.py`. `configure_logging` routes the root, `uvicorn` and `uvicorn.error` loggers through `structlog.stdlib.ProcessorFormatter` with the same `render_exception` + `redact_sensitive` + JSON chain. Or, as an alternative, an outermost pure-ASGI guard in `core/` that swallows the exception re-raised after `http.response.start` was sent.
2. **`main.py` wiring (S1-T09, which owns `main.py` middleware wiring):** install the guard as the outermost middleware, or call the bridge at app creation.
3. **uvicorn invocation (S1-T12, DevOps, which owns `backend.Dockerfile` and the compose `api` service):** run uvicorn with `log_config=None` (or a JSON `--log-config`) so its default `dictConfig` does not replace the bridge at startup. The same step closes SEC-02 (`--no-access-log`).

If the maintainer does not want the core part in S1-T03, it has to be recorded as a tracked item with an owner (I suggest S1-T09) and a test. The test: a route raising `ValueError("…S3CRET…")` and an internal `ValidationError` with a password input, run under real uvicorn with **stdout and stderr captured**, asserting the marker is absent (proposed TC under TC-SEC-20). Either way it must close **before S1-T06 (authentication) merges**. Severity stays **Medium**, so it does not block S1-T03.

### Status of each finding

| ID | Sev. | Status at `e9d1473` | Evidence (clean export) |
|---|---|---|---|
| SEC-01 | Medium | **Partially fixed.** App `exc_info` is fixed. The uvicorn stderr traceback with message and `input_value` is **open**, and the docstring is still inaccurate (see above) | `log_attack.out` `exc_info-*` all `leak=False`; `uvicorn.stderr` lines 60, 121 |
| SEC-02 | Low | **Open** (outside `core/`; owner S1-T12 uvicorn flags or S1-T09 JSON access middleware) | `uvicorn.stdout`: `"GET /boom?token=S3CRET-VALUE-xyz HTTP/1.1" 500` |
| SEC-03 | Low | **Partially fixed.** Now redacted: `pwd`, `passwd`, `credential(s)`, `csrf`, `private_key`, `dsn`, fullwidth, zero-width (U+200B), soft hyphen (U+00AD), `ſecret` (long s), `bytes` keys, sets and frozensets of pairs, lists of pairs, ASGI header pairs (`(b"cookie", …)` dropped, `(b"x-ok", b"1")` kept). **Still logged verbatim:** `ingest_key`, `anthropic_key` (SR-18 names Anthropic keys), `signing_key`, a bare `key`, `bearer`, `jwt`, `otp`. Cyrillic look-alikes and combining marks (`pássword`) are now a documented limit, which I accept | `log_attack.out`: `[ingest_key] leak=True`, `[anthropic_key] leak=True`, `[signing_key] leak=True`, `[key] leak=True`, `[bearer]/[jwt]/[otp] leak=True`; `[cyrillic-a]`, `[combining] leak=True` (documented) |
| SEC-04 | Low | **Fixed** (a node budget of 2000 per event). A new side effect is reported as SEC-17 | self-ref dict n=5/7/10/50: 0.002–0.003 s, 37–43 KB (was 17.4 MB at n=7); 2,000,000-item list: 0.078 s, 10.9 KB (was 16.9 MB). Strings are still not capped (a 20 MB string gives a 20 MB line, 0.08 s). That is the optional part of the suggestion and stays Info |
| SEC-05 | Low | **Fixed.** Canonical re-encode check plus NUL and surrogate refusal on both encode and decode | `cursor_attack.out`: whitespace JSON, reordered keys, `A`, `\/`, `-0`, NUL, lone surrogate → 400 `"Invalid cursor"` (cause `None`, context suppressed); the encoder refuses NUL and surrogates with `ValueError`; round-trips OK; 1,000,000 chars → 400 in 585 µs. Residual Info: `\u0001`-style control characters are canonical JSON and still accepted (harmless for PostgreSQL `text`) |
| SEC-06 | Low | **Fixed.** fd-based `O_NONBLOCK`, `fstat` + `S_ISREG`, at most 4097 bytes read | `config_attack.out`: FIFO, symlink→FIFO, `/dev/zero`, `/dev/null` and a directory → "is not a regular file" (no hang); 200 MiB sparse and 4097 bytes → "too large"; exactly 4096 → OK; whitespace-only → rejected; max RSS 33 MiB (was 432 MiB). A symlink to a regular file is followed (documented, acceptable). Residual Info: a NUL byte inside the value is accepted |
| SEC-07 | Low | **Partially fixed.** Userinfo passwords are rejected without echo (`postgresql://u:S@h/db`, `redis://:S@h`, even an empty `u:@`), and `hide_input_in_errors=True` keeps the input out of `str(ValidationError)` and the traceback. **Still accepted and printed by `repr(settings)`:** a password in the **query string** (`postgresql://u@h/db?password=S`, `redis://h:6379/0?password=S`, which SQLAlchemy/asyncpg and redis-py both honour) and a libpq keyword DSN (`host=h user=u password=S`) | `[url password in query] OK leak_in_repr=True`, `[redis password in query] OK leak_in_repr=True`, `[libpq keyword DSN] OK leak_in_repr=True`. `exc.errors()` still contains the input by default (`leak_errors_default=True`), as the new `Settings` docstring says (`include_input=False` required) |
| SEC-08 | Low | **Open, accepted limit** (Semgrep rule pending S1-T13). The docstring now lists it | `[event-text] leak=True` |
| SEC-09 | Info | **Open** | `/only-post` GET → 405 with `"type": ".../bad-request"`, `"title": "Bad request"`, `allow: POST` |
| SEC-10 | Info | Open (no change; developer-controlled) | — |
| SEC-11 | Info | Open, accepted | — |
| SEC-12 | Info | Open (S1-T09 trusted-proxy work) | — |
| SEC-13 | Info | Open, no action beyond SR-13 | — |
| SEC-14 | Info | **Open**: `AEGIS_DATABASE_PASSWORD=…` is still silently ignored | `[plain AEGIS_DATABASE_PASSWORD] OK` |
| SEC-15 | Info | **Fixed** (one CRLF or LF stripped) | `crlf value ends with CR: False` |
| SEC-16 | Info | Open (reviewer checklist item) | — |

Other changes I checked (no finding):

- **Request id context:** `bind_contextvars` tokens plus `reset_contextvars` restore the outer binding. On one keep-alive connection, `actor` bound in request 1 is absent from request 2's line, and request 2 gets its own `request_id` (`uvicorn.stdout`). There is no cross-request context leak under uvicorn.
- **Bodyless statuses:** `HTTPException(204, headers={"X-Extra": "1"})` → `204` with no body, `x-request-id` present, and no duplicate header.
- **`render_exception` robustness:** a string `exc_info` is dropped (no crash, no echo). `stack_info=True` passes through as a boolean only (there is no `StackInfoRenderer`). Frame locals never appear. Source lines of the frames do appear, which is acceptable because they are code, not data.
- **`RecursionError` removed from the cursor `except`:** a 180-deep `[[[…]]]` payload inside the 512-character cap → 400. The length cap bounds nesting well below the recursion limit.

### New findings in `e9d1473`

| ID | Severity | Location | Ref | Finding | Fix suggestion |
|---|---|---|---|---|---|
| **S1-T03-SEC-17** | Low | `core/logging.py` `_Walk` applied to the whole `event_dict` | SR-18 (log usefulness), T-08, T-14 | **The node budget is shared with the record's own fields, so one large value erases `event`, `level`, `timestamp` and `request_id`.** `info("login_failed", attacker_list=list(range(5000)))` with `request_id` bound renders as `{"logger_name": "t", "attacker_list": [... "[truncated]"], "[truncated]": true}`: there is no `event`, `level`, `timestamp` or `request_id` (`[budget-displacement]` in `log_attack.out`). A sensitive key after the cut-off is still not emitted (`[sensitive-after-budget] leak=False`), so this is not a disclosure. It does make a log line uncorrelatable and unfilterable by level, and anyone who can make the app log a large collection controls that | Walk each top-level value with its own budget (or reserve budget for the top level). Or apply `_Walk` to user-supplied values only and add `level`, `timestamp` and context after redaction. At minimum, never truncate the top-level keys `event`, `level`, `timestamp`, `request_id` and `logger_name`. Add a test |

Info notes (no new IDs): the `MAX_SECRET_BYTES` read is a single `os.read`, which on some network or FUSE filesystems can return fewer bytes and would silently shorten a password (fails closed as an authentication error, no disclosure). The ASGI header pairs that are kept render as `"b'x-ok'"` (`repr` of bytes), which is cosmetic.

### Scanner results at `e9d1473`

| Scanner | Command | Exit | Result | Raw artefact (SHA-256) |
|---|---|---|---|---|
| Bandit 1.9.4 | `uv run --frozen bandit -r <export>/apps/api/src -f json -o <scratch>/bandit.json -q` | 0 | 0 issues, 670 LOC (all of `src/`), 0 `#nosec` | `bandit.json` `8fe591cc…8886` |
| pip-audit (installed env) | `uv run --frozen pip-audit -f json -o <scratch>/pip-audit-env.json` | 0 | No known vulnerabilities | `pip-audit-env.json` `d05fd746…1f66` (identical to the earlier runs) |
| pip-audit (lockfile, hash-checked) | `uv export --frozen --all-groups --no-emit-project --format requirements-txt` then `pip-audit -r req-locked.txt --require-hashes --disable-pip` | 0 | No known vulnerabilities | `pip-audit-lock.json` `55b68c13…d0d8` (identical) |
| Gitleaks v8.30.1 (commit range) | `docker run --rm --network none -v "$PWD:/repo:ro" ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:c00b6bd0… git /repo --log-opts=61bbdd6..e9d1473 --redact --no-banner` | 0 | `1 commits scanned.` / `no leaks found` | console only |
| Gitleaks v8.30.1 (working tree) | same image, `dir /repo --redact --no-banner` | 0 | `scanned ~1938437 bytes (1.94 MB)` / `no leaks found` | console only |
| Semgrep, Trivy | — | — | Not run (they arrive with S1-T13) | — |

Attack-run outputs (scratchpad `…/scratchpad/out/`): `log_attack.out` `f12ddc4f…41ca`, `client.out` `9c6e14bb…dc7f3`, `uvicorn.stdout` `9fbab10b…b9cb3`, `uvicorn.stderr` `0a140557…1b75`, `cursor_attack.out` `3f78092b…c7f3`, `config_attack.out` `6290e8a5…3aa3`. The retention gap from earlier rounds still applies: QA or the orchestrator should re-produce and commit them under `qa/reports/sprint-01/evidence/` if they are needed.

### Threat-model proposals (update)

Proposals 1–3 from the initial S1-T03 review stand unchanged. Addition to SR-16 proposal 3: "connection settings must not carry a password in userinfo, **query parameters or keyword DSNs**" (SEC-07 residual). Addition to SR-18: "the redaction size bound must not remove the record's `event`, `level`, `timestamp` and `request_id`" (SEC-17).

### Verdict (S1-T03 at `e9d1473`)

| Task | Verdict | Open ≥ High | Open Medium | Open Low / Info |
|---|---|---|---|---|
| **S1-T03** | **No blocking findings** | **0** | **1**: SEC-01, server/stdlib path only (uvicorn stderr traceback with message and `input_value`). Needs the core bridge or guard plus `main.py` and uvicorn wiring; owner to be assigned by the maintainer (suggested: core part in S1-T03 or S1-T09, uvicorn flags in S1-T12). Must close before S1-T06 merges | Low: SEC-02 (open), SEC-03 (partial: `*_key`, `anthropic_key`, `bearer`, `jwt`, `otp`), SEC-07 (partial: query-string and keyword-DSN passwords), SEC-08 (accepted, Semgrep pending), **SEC-17 (new)**. Fixed: SEC-04, SEC-05, SEC-06, SEC-15. Info open: SEC-09 … SEC-14, SEC-16 |

This review approves nothing. Merge stays with the maintainer, and the QA notes are separate.
