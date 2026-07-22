# TC-002 Business File Extraction

Date Created: 2026-04-30
Last Updated: 2026-05-05
Status: Passed

## Purpose

Verify that normal business files can be converted into normalized requirement context.

## Traceability Sources

- `docs/superpowers/development/05_development_workflow.md` - Checkpoint 4
- `docs/superpowers/development/01_product_scope.md` - MVP input scope
- `docs/superpowers/development/02_agent_behavior_contract.md` - source handling and traceability
- `docs/superpowers/testing/test_case_index.md`

## Inputs

- MD
- TXT
- PDF
- DOCX
- XLSX
- CSV

## Preconditions

File upload and extractor modules exist.

## Steps

1. Upload each supported file type.
2. Run extraction.
3. Review normalized output and metadata.

## Expected Output

- text files extract text
- selectable PDFs extract text
- DOCX extracts paragraphs, tables, and header/footer text
- XLSX/CSV summarizes rows, headers, comments/formulas where available, and multiline or quoted cells
- source metadata is saved
- unsupported or failed files show clear errors

## Real Output

- `extract_requirement_source()` extracts text from MD and TXT files.
- Selectable PDF text is extracted with page-count metadata.
- DOCX paragraphs, table cells, and header/footer paragraphs are extracted with paragraph, header/footer, table, and table-row metadata.
- CSV files are summarized with row count, columns, and preview rows, including quoted commas and multiline cell text.
- XLSX files are summarized by sheet with row count, columns, preview rows, comments, and formulas where workbook text exposes them.
- Unsupported files raise a clear message that lists supported types.
- Empty readable content raises a clear message.
- Streamlit now includes a multi-file uploader for MD, TXT, PDF, DOCX, XLSX, and CSV.
- Uploaded file context is previewed in the UI and included in the requirement-analysis input for the current deterministic checkpoint.

## Differences / Issues

- The current extractor is local and deterministic; it does not save source records to Firestore yet.
- CSV/XLSX extraction summarizes rows, headers, comments, and formulas instead of importing a full canonical table model. Canonical source records come in the later schema/persistence checkpoints.
- Scanned image-only PDFs are expected to fail with a readable-content error until image/OCR support is added in a future phase.
- Damaged, protected, parser-incompatible, or scanned PDFs now show business-friendly guidance instead of raw parser errors such as `Stream has ended unexpectedly`.
- Image content inside PDF/DOCX/XLSX files is not analyzed in this checkpoint. OCR/vision input remains future scope according to the product scope and behavior contract.

## Evidence

```text
Command: .\.venv\Scripts\pytest.exe tests\test_business_file_extraction.py
Result: 7 passed in 1.16s
```

```text
Command: .\.venv\Scripts\pytest.exe tests\test_app_shell.py tests\test_business_file_extraction.py
Result: 14 passed in 1.25s
```

```text
Command: .\.venv\Scripts\pytest.exe
Result: 41 passed in 5.21s
```

```text
Command: Streamlit server smoke on localhost:8503
Result: /_stcore/health returned 200 ok; page returned 200
```

## Decision

Passed for Checkpoint 4 local business file extraction.

Continue to Checkpoint 5: canonical JSON schema validation.
