# S1-T03 mutation check, throwaway copy of the 61bbdd6 export (harness: scratchpad mutate.py)

Rows 2, 3 first ran with a harness bug (pattern matched the docstring) and were re-run with the pattern anchored on the code line: both killed. Command per mutant: `pytest tests/unit` (implementer tests) and `pytest qa/api/core_s1t03 -k 'not BUG'` (QA tests), `-x`.

| # | Mutation | impl unit tests | QA tests |
|---|---|---|---|
| 1 | request_id fullmatch->match | killed | killed |
| 2 | request_id max 64->65 | killed | killed |
| 3 | request_id min 8->7 | killed | killed |
| 4 | request_id keep handler header (dup) | killed | killed |
| 5 | request_id no contextvar clear in finally | SURVIVED | killed |
| 6 | request_id no bind | killed | killed |
| 7 | logging drop 'cookie' | killed | killed |
| 8 | logging no list recursion | killed | killed |
| 9 | logging case-sensitive | killed | killed |
| 10 | logging no nested mapping recursion | killed | killed |
| 11 | cursor no canonical b64 check | killed | killed |
| 12 | cursor bool accepted as int | killed | killed |
| 13 | cursor duplicate keys allowed | killed | killed |
| 14 | cursor non-canonical uuid allowed | killed | killed |
| 15 | cursor max len 513 | killed | SURVIVED |
| 16 | cursor version unchecked | killed | killed |
| 17 | cursor extra keys allowed | killed | killed |
| 18 | cursor datetime canonical off | killed | killed |
| 19 | cursor RecursionError not caught | SURVIVED | SURVIVED |
| 20 | errors 500 leaks message | killed | killed |
| 21 | errors validation echoes input | killed | killed |
| 22 | errors instance has query | killed | killed |
| 23 | errors 409 invalid-transition slug | killed | killed |
| 24 | errors problem content-type json | killed | killed |
| 25 | errors json_invalid -> 422 | killed | killed |
| 26 | errors no X-Request-ID in problem | killed | killed |
| 27 | errors unhandled not registered | killed | killed |
| 28 | config ci check inverted | killed | killed |
| 29 | config strip() all whitespace | killed | killed |
| 30 | config empty allowed | killed | killed |
| 31 | ids uuid4 | killed | killed |
| 32 | clock frozen accepts naive | killed | killed |
| 33 | clock advance no-op | killed | killed |

Survivors: #5 (impl tests only: contextvar cleanup in finally not tested by implementer); #15 (QA tests only: a 513-char token is never a valid base64url of this payload shape, tested by implementer); #19 equivalent mutant (the 512-char limit makes RecursionError unreachable, the except branch is defensive dead code).
