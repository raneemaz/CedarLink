# Report figures

Three Mermaid diagrams and the project counts, for chapter 6.

Everything here was read out of the code on **2026-09-04**, at commit
`32348c0`. The older figures in `files related/` — the three-layer
architecture sketch in `CedarLink.md` and `ERD.drawio.pdf` — are both out
of date and should not be used.

## Diagrams

| File | Figure |
|---|---|
| `architecture.mmd` | Four layers: React presentation, Flask routes, services, data. Names all 12 services. |
| `erd.mmd` | All 26 tables, all 36 foreign keys, with cardinality taken from each FK's nullability. |
| `checkout-sequence.mmd` | Checkout end to end, with the conditional stock decrement and its zero-rowcount failure branch drawn explicitly. |

### Rendering

The `.mmd` source is the deliverable; PNGs are generated from it.

```bash
cd frontend
npx @mermaid-js/mermaid-cli -i ../docs/diagrams/architecture.mmd \
                            -o ../docs/diagrams/architecture.png -s 2 -b white
```

GitHub renders `.mmd` fenced as ```mermaid``` natively, so the source can
also be pasted straight into a Markdown document.

**Two Mermaid syntax traps** cost time here and are worth knowing before
editing these files:

- A **bare `%%` line** — a comment marker with nothing after it — swallows
  the following newline and glues the comment block onto the diagram
  declaration, producing `%%flowchart TB` and a parse error on line 1. Give
  every separator line some content (`%% --`).
- An attribute with **two key constraints** must comma-separate them:
  `int user_id FK,UK`, not `int user_id FK UK`.

## Counts

| Measure | Value |
|---|---|
| API endpoints (distinct route rules) | **121** |
| Database tables | **26** |
| Foreign keys | **36** |
| Alembic migrations | **42** |
| Service modules | **12** |
| Route blueprint modules | **20** (21 registered blueprints) |
| Tests — total | **301** |
| — integration | 259 (17 files) |
| — unit | 29 (1 file) |
| — regression | 13 (3 files) |
| Architecture decision records | **23** |
| Python — `app/` | **14,286** |
| Python — `tests/` | **6,881** |
| Python — `migrations/` | 2,364 |
| Python — total (app + tests + run.py) | **21,173** |
| JSX / JS / TS — `frontend/src/` | **18,485** |
| — `.jsx` | 17,264 |
| — `.js` | 970 |
| — `.ts` | 251 |
| Backend statement coverage | **70%** (1,546 of 5,193 uncovered) |

`app/` breaks down as routes 5,412 · services 4,387 · models 2,141 ·
top-level (`cli.py`, `config.py`, `seed_data.py`, `__init__.py`,
`extensions.py`) 2,075 · utils 271.

Endpoints by method: GET 36 · POST 38 · PUT 18 · DELETE 15 · PATCH 14.
Every rule carries exactly one method.

### Reproducing them

```bash
# endpoints, tables, foreign keys
flask shell -c "..."           # see the one-liners below

# migrations, ADRs
ls migrations/versions/*.py | wc -l
ls docs/decisions/*.md | wc -l

# tests
pytest --collect-only -q | tail -1
pytest tests/integration --collect-only -q | grep -cE "^tests"

# lines of code — frontend/src only, so node_modules and dist are excluded
find app tests -name "*.py" -not -path "*/__pycache__/*" | xargs wc -l | tail -1
find frontend/src -name "*.jsx" -o -name "*.js" -o -name "*.ts" | xargs wc -l | tail -1

# coverage
pytest -q --cov=app --cov-report=term | grep ^TOTAL
```

Endpoint and table counts come from the live app, not from grepping
decorators, so a blueprint that fails to register is counted as absent
rather than present:

```python
from app import create_app
from app.config import DevConfig
from app.extensions import db

app = create_app(DevConfig)
rules = [r for r in app.url_map.iter_rules() if r.endpoint != "static"]
print(len(rules))
with app.app_context():
    print(len(db.metadata.tables))
    print(sum(len(t.foreign_keys) for t in db.metadata.tables.values()))
```

## Caveats worth stating in the chapter

- **Coverage is 70% of backend statements only.** There is no frontend test
  suite, so the figure says nothing about the 18,485 lines of JSX. The
  weakest backend modules are `cli` (15%, and it is the demo seed),
  `payment_routes` (17%) and `user_routes` (30%); the modules carrying the
  correctness arguments are well covered — `coupon_service` 96%,
  `store_service` 94%, `order_service` 87%.
- **The 121 endpoints include admin and vendor surfaces**, not just the
  customer API. Roughly a third are behind a role check.
- **`migrations/` is excluded from the headline Python figure** because it
  is generated code; it is listed separately at 2,364 lines.
- **i18n JSON is not counted as source.** The three locale files add a
  further 4,498 lines.
