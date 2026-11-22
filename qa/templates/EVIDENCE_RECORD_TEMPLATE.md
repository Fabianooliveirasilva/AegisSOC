# Evidence record

A claim without this record and its artefacts is not evidence. Rules: [SPRINT_01_EXECUTION_PROTOCOL.md §7](../../docs/SPRINT_01_EXECUTION_PROTOCOL.md#7-evidence-requirements).

| Field | Value |
|---|---|
| Evidence ID | EV-SNN-### |
| Requirement(s) | AC-… / SR-… |
| Test case(s) | TC-… |
| Task / PR | S1-T.. / PR.. |
| Git commit SHA | full 40-char SHA of the code under test |
| Date/time (UTC) | YYYY-MM-DDTHH:MM:SSZ |
| Environment | OS; Docker / Compose versions; Python, Node, tool versions; local-stack / disposable DB / CI (run URL) |
| Command(s) | exact command line(s) |
| Exit status | 0 / non-zero (per command) |
| Result | Pass / Fail — counts (passed / failed / skipped, findings by severity) |
| Artefacts | path(s) under `qa/reports/sprint-NN/evidence/` or CI artefact name, each with SHA-256 |
| Produced by | agent / person |
| Independent reproduction | reproduced by …, at SHA …, clean worktree: match / mismatch (link to bug) |
| Notes | |
