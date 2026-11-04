# Audita Análisis — AuditaPro module

The auditor uploads **their working paper (Excel)**, the **ledger/subsidiary report** and the
**client's documents** (PDF, Word, Excel, CSV). The **orchestrator** recognises the paper and
activates only the agents that are needed; the agents analyse, and **the result is written into a
copy of the same working paper**, each figure linked to its file and page. The auditor reviews,
decides and approves.

Spanish version: [README.md](README.md)

## Rules enforced in code

- **Code computes the numbers, not the AI** (`Decimal` engine; AI is optional and only classifies/drafts).
- **The original is never modified**: it is read, results go to a `_llenado.xlsx` copy, SHA-256 compared before/after.
- **A formula is never overwritten**; occupied target → next free cell / cancel. Text from documents starting with `=` is stored as text.
- **Every figure has an origin** (file, sheet, rows/page, coordinates) and a cell comment in the paper.
- **The copy is verified** cell by cell against the original; if anything outside the written range changed, it is not delivered. Anything the copy cannot keep (shapes, images, conditional formats…) is reported.
- **Proposed ≠ approved**: only the project's audit manager approves, and only if all figures re-check against their source.
- **Hash-chained, append-only log** (ISA 230). **An alert is not proof of fraud**: the conclusion is the auditor's.

## Protecting the system from overload

File validation (real content, not only extension; zip-bomb guard; random internal names; SHA-256;
private storage), configurable limits (file size/total/count/rows/PDF pages — exceeding a limit
reads up to the limit **and warns**), bounded worker pool with global and per-user caps, stale-run
recovery, streaming Excel reads. **Measured**: 50,000-row ledger + 100-page PDF + template, 4 agents:
**≈ 56 s, ≈ 104 MB** Python peak (guide target: < 5 min).

## Screens (`/analisis/`)

New analysis → live progress (01 classify → 02 extract → 03 cross-match → 04 agents → consolidate →
fill paper) → orchestrator plan (each agent "active" / "not used" with reason), indicators, conclusion,
tables, risks & findings with auditor decisions → versioned filled paper + "Evidence" sheet →
validate figures → approve. Click any figure for the source viewer (Excel row + neighbours; PDF page with the amount highlighted).

## Integration papers: results inside the paper's own table

For **integration** papers (e.g. `10_INTEGRACION_EGRESOS` · A-12, `8_INTEGRACION_INGRESOS` · A-10) results are also
written **inside the paper's detail table**: one row per item if they fit, otherwise a **monthly integration** (Σ per
month, each total traceable) plus all items in a **«Detalle integración»** sheet with mark and observation. The ledger
total cell is filled from the auditor's "saldo según mayor"; the paper's own formula computes the difference. Formulas are
never touched and rows are never inserted. General observations get the findings; the **auditor's conclusion is never
replaced** (a comment with the proposal is added). Test: `test_egresos_a12.py`.

## Claude (optional)

Works fully without a key. With a key, Claude classifies doubtful pages, reads hard documents (literal
evidence required), interprets the request and drafts the conclusion. Every answer is schema-validated and
every number in drafted text must exist in the computed data, otherwise it is discarded. Document content is
treated as data, never as instructions. **The key is read from `ANTHROPIC_API_KEY` and never stored in the repo.**
Only the needed text (≤ 6,000 chars/page) is sent — review the provider's data-retention terms before production.

## Configuration

See the table in [README.md](README.md#configuración-variables-de-entorno). In production, mount a **persistent
volume** for `ANALISIS_STORAGE_ROOT`. Install: `pip install -r requirements.txt && python manage.py migrate`.

## Tests

`python manage.py test analisis --settings=saas_project.settings_test` — 113 tests (performance and all-538-templates tests run with `ANALISIS_SLOW_TESTS=1`).

## Not included in this version

Client Portal and Continuous Monitoring (folder 8) modules; OCR for scanned PDFs (flagged as "evidence without text");
decision cards, PBC, credits/plans, closed-file lock, multi-firm isolation; Word "pages" are page-break sections; the queue is
in-process threads (move to Celery/RQ at scale).

**Real Audit-module templates** (`static/templates_base_*`): all **538** tested (437 Financial, 67 Internal, 34 Statutory).
All fill and pass the cell-by-cell check, 0 formulas overwritten (26,765 formulas). 4 copies drop a minor drawing element
(3 lines/text boxes, 1 extended conditional-format rule) and **the system warns about it** on that paper version.
The Claude API was tested live.
