# S1-T03 re-validation 1 mutation check on e9d1473 (changed rules only; throwaway export; harness scratchpad mutate2.py)

Command per mutant: `pytest tests/unit -x` (implementer) and `pytest qa/api/core_s1t03 -x` (QA), 120 s timeout (a hang counts as killed). 27 mutants, all patterns found.

| # | Mutation | impl unit tests | QA tests |
|---|---|---|---|
| 1 | logging: no NFKC | killed | SURVIVED |
| 2 | logging: keep Cf chars | killed | SURVIVED |
| 3 | logging: pair redaction off | killed | killed |
| 4 | logging: drop new key words | killed | SURVIVED |
| 5 | logging: drop passwd|pwd | killed | SURVIVED |
| 6 | logging: node budget off | killed | SURVIVED |
| 7 | logging: mapping depth cap off | killed | killed |
| 8 | logging: exception message leaked | killed | SURVIVED |
| 9 | logging: order swapped | SURVIVED | SURVIVED |
| 10 | config: S_ISREG off | killed | SURVIVED |
| 11 | config: size limit off | killed | SURVIVED |
| 12 | config: CRLF strip off | killed | killed |
| 13 | config: whitespace-only allowed | killed | killed |
| 14 | config: URL password allowed | killed | SURVIVED |
| 15 | config: input echoed | killed | killed |
| 16 | config: no O_NONBLOCK | killed | SURVIVED |
| 17 | config: read limit off by one | killed | SURVIVED |
| 18 | pagination: NUL allowed | killed | killed |
| 19 | pagination: surrogate allowed | killed | SURVIVED |
| 20 | pagination: canonical form off | killed | killed |
| 21 | pagination: decode text check off | killed | killed |
| 22 | pagination: encode text check off | killed | SURVIVED |
| 23 | errors: bodyless off | killed | SURVIVED |
| 24 | errors: 304 bodied | killed | SURVIVED |
| 25 | errors: bodyless no request id | SURVIVED | SURVIVED |
| 26 | request_id: clear instead of reset | killed | SURVIVED |
| 27 | request_id: no cleanup | killed | killed |

Reading: implementer unit tests kill 25 of 27. QA tests kill 11 of 27: the QA suite was written for the first-cycle rules and is not a mutation-complete oracle for the new hardening (NFKC, FIFO, size limit, bodyless statuses, URL password); those rules are covered by the implementer tests instead.
Survivors in both suites:
- #9 processor order (redact before/after render_exception): equivalent today, the rendered exception is a plain string without keys.
- #25 bodyless status (204/205/304/1xx) response without X-Request-ID header: untested gap (S4, QA-S1T03-008).
