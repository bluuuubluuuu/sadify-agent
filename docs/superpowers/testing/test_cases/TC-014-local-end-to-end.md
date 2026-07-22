# TC-014 Local End-To-End Test

Date Created: 2026-05-08  
Last Updated: 2026-05-11  
Status: Passed

## Purpose

Prove that SADify can run the local MVP path from business requirement intake through analysis, relationship graph, wiki generation and approval, project-level SAD generation, export preparation, diagnostics, and canonical persistence boundaries without live model calls or cloud writes.

## Inputs

Representative warehouse operations requirement:

```text
Warehouse operators scan stock during receiving, picking, packing, and dispatch. They record item code, quantity, location, date, status, and remarks. Supervisors approve rejected records. Managers need daily dashboards and weekly exports. The system needs role-based access, audit history, mobile use, offline support, and safe handling when records are missing or wrong.
```

Local source record:

```text
SRC-001 warehouse-notes.txt
```

## Preconditions

- Python `.venv` exists.
- Dependencies are installed.
- No live model key, Drive write, Cloud Run deployment, or real Firestore cloud write is required.
- Existing checkpoints 1 through 12 are passing.

## Steps

1. Run the local workflow test.
2. Run selected neighboring service tests.
3. Run the full test suite.
4. Start Streamlit headlessly on a spare local port and check `/_stcore/health`.

## Expected Output

- Requirement analysis is valid.
- Completeness and confidence are calculated.
- Relationship graph contains canonical knowledge items and relationships.
- Wiki Markdown notes are rendered.
- Rule-based wiki verification passes.
- Local owner approval promotes wiki drafts to verified current Markdown.
- Project-level SAD is generated.
- Google-Doc-import HTML, PDF, DOCX, and wiki Markdown export artifacts are prepared.
- Canonical records can be saved through the Firestore repository abstraction.
- Diagnostics show successful local stages.
- Streamlit local health endpoint returns `200 ok`.

## Real Output

Automated local workflow:

```text
Command: .\.venv\Scripts\pytest.exe tests\test_local_end_to_end.py -q
Result: 4 passed in 1.79s
```

Selected checkpoint integration set:

```text
Command: .\.venv\Scripts\pytest.exe tests\test_local_end_to_end.py tests\test_export_generation.py tests\test_sad_generation.py tests\test_wiki_verification.py tests\test_firestore_persistence.py tests\test_app_shell.py -q
Result: 37 passed in 2.08s
```

Full local suite:

```text
Command: .\.venv\Scripts\pytest.exe
Result: 89 passed in 9.05s
```

Streamlit local smoke:

```text
Command: headless Streamlit start on localhost:8502, then GET /_stcore/health
Result: STREAMLIT_HEALTH:200:ok
```

Fresh review evidence on 2026-05-11:

```text
Command: .\.venv\Scripts\pytest.exe
Result: 89 passed in 12.49s

Command: headless Streamlit start on localhost:8502, then GET /_stcore/health
Result: STREAMLIT_HEALTH:200:ok
```

Development commit:

```text
77adef3 feat: add local end-to-end workflow
```

## Differences / Issues

- The C13 workflow is deterministic and local-first; it does not call Gemini or any other live model.
- Repository persistence is verified through the Firestore repository abstraction with a fake local client, not the real Firestore cloud database.
- Exports are prepared locally; real Drive/Docs upload remains deferred.
- A prior manual Streamlit run appeared to stop after startup. The C13 headless smoke did not reproduce an app startup failure; the health endpoint returned `200 ok`.

## Evidence

- `tests/test_local_end_to_end.py`
- `src/sadify/services/local_end_to_end.py`
- Full pytest output: `89 passed in 9.05s`
- Streamlit health smoke: `STREAMLIT_HEALTH:200:ok`

## Decision

Passed.

Checkpoint 13 is complete. The MVP local path is ready enough to proceed to Cloud Run deployment preparation, with real cloud writes and live model calls still controlled by explicit approval and budget awareness.
