# Component diagram — backend modules

Arrows mean "calls the service interface of". Modules never import another module's models or touch its tables (enforced by import-linter).

```mermaid
flowchart TB
  subgraph aegissoc
    CORE[core<br/>settings · db · redis · errors · pagination · ids · metrics]
    AUTH[platform.auth<br/>users · sessions · CSRF · RBAC · API keys]
    AUD[platform.audit]
    SIEM[siem<br/>sources · ingest · parsers · normaliser · event store · search · retention]
    DET[detection<br/>rules · versions · validator · evaluator · correlation · ATT&CK]
    ALR[alerts<br/>create · dedup · triage · disposition]
    INC[incidents<br/>lifecycle · notes · evidence · timeline · playbooks]
    INTEL[intel<br/>IOC lists · import · matcher]
    HUNT[hunting<br/>query DSL · saved hunts · retro-hunt]
    AI[ai<br/>context builder · redaction · provider · tool loop · validator · proposals]
    QA[qa<br/>scenario runner · validation runs · metrics]
    OBSM[observability<br/>/metrics · health]
  end

  AUTH --> AUD
  SIEM --> AUTH
  SIEM --> AUD
  DET --> SIEM
  DET --> ALR
  ALR --> AUD
  INC --> ALR
  INC --> AUD
  INTEL --> SIEM
  INTEL --> ALR
  HUNT --> SIEM
  HUNT --> DET
  AI --> SIEM
  AI --> ALR
  AI --> INC
  AI --> DET
  AI --> AUD
  QA --> DET
  OBSM --> CORE
  AUTH & SIEM & DET & ALR & INC & INTEL & HUNT & AI & QA & AUD --> CORE
```

Each module has the same internal layout:

```
aegissoc/<module>/
  api.py        # FastAPI router (HTTP only: parse, authorise, call service)
  service.py    # public interface for other modules + business logic
  models.py     # SQLAlchemy models (private to module)
  schemas.py    # Pydantic request/response models
  repository.py # queries (private)
  workers.py    # stream consumers (if any)
```
