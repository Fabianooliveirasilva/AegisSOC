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
