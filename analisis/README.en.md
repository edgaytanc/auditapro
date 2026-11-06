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

## Pasting rule: each value in its own column (all templates)

Client rule (PT A-11 guide): every template has its own table with named columns; transactions are pasted there,
replacing the examples. Applies to any template with a transaction table (amount + date or document number, TOTAL `=SUM`).
Columns are matched by name/synonym (e.g. «Monto Doc. (Q)» ← `Total_Facturado`); one transaction per row; when they do
not fit, **rows are inserted like Excel does** (the total `=SUM` grows; everything below moves with its formulas, merges,
formats, validations and print area — `engine/sheet_rows.py`). «Observaciones» gets the system's analysis per
transaction; auditor-only columns stay empty and a formula depending on them is guarded (`=IF(J19="","",J19-F19)`);
test parameters are filled; the template's example conclusion is replaced by the proposal (original kept in a comment);
everything else goes to the «ANÁLISIS AGENTES» and «Evidencia» sheets. The copy is verified against the original with
the row shift applied. Sample tables without a TOTAL row (Internal Audit) end at the first blank row; an identical column name always wins; with several tables in a workbook the auditor's chosen sheet wins. 98 of 538 templates have a transaction table. Tests: `test_ingresos_a11.py` (500 invoices), `test_egresos_a12.py`, `test_interna_pruebas.py`, all 538 templates.

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

`python manage.py test analisis --settings=saas_project.settings_test` — 125 tests (performance and all-538-templates tests run with `ANALISIS_SLOW_TESTS=1`).

## Not included in this version

Client Portal and Continuous Monitoring (folder 8) modules; OCR for scanned PDFs (flagged as "evidence without text");
decision cards, PBC, credits/plans, closed-file lock, multi-firm isolation; Word "pages" are page-break sections; the queue is
in-process threads (move to Celery/RQ at scale).

**Real Audit-module templates** (`static/templates_base_*`): all **538** tested (437 Financial, 67 Internal, 34 Statutory).
All fill and pass the cell-by-cell check, 0 formulas overwritten (26,765 formulas). 4 copies drop a minor drawing element
(3 lines/text boxes, 1 extended conditional-format rule) and **the system warns about it** on that paper version.
The Claude API was tested live.
