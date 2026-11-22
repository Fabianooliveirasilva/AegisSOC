# detections/ — detection-as-code

Lifecycle and rules: [SYSTEM_DESIGN.md §4](../docs/SYSTEM_DESIGN.md#4-module-b--detection-engineering), [ADR-0015](../docs/adr/0015-detection-as-code-and-four-eyes.md). Content arrives in Sprint 3.

| Path | Contents |
|---|---|
| `rules/<area>/<slug>.yml` | Sigma rules (areas: `windows`, `linux`, `web`, `cloud`) |
| `correlation/<slug>.yml` | Sigma correlation rules (Sprint 4) |
| `scenarios/<rule-sigma-id>/<name>.yml` | positive/negative scenarios (format in SYSTEM_DESIGN §8) |

Commands (from Sprint 3): `aegissoc detections validate`, `aegissoc detections test`, `aegissoc detections sync` (imports as **draft** only; never activates).

Every rule needs ≥ 1 positive and ≥ 1 negative scenario and must meet the [detection rule DoD](../docs/DEFINITION_OF_DONE.md#3-detection-rule). Rules derived from SigmaHQ keep DRL 1.1 attribution.
