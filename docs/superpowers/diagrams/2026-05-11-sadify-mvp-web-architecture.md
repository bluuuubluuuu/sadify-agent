# SADify MVP Web Architecture

Created: 2026-05-11
Status: Draft for user review

## Purpose

This diagram shows the planned MVP architecture after the Streamlit prototype baseline.

The older architecture diagram remains the prototype reference. This document is the target architecture for the proper MVP web app.

## Runtime Architecture

```mermaid
flowchart TD
    user["Guest or signed-in user"] --> web["Cloud Run frontend<br/>Next.js / React"]

    web --> auth["Firebase Auth / Google Identity Platform<br/>persistent Google session"]
    web --> api["Cloud Run backend<br/>Python FastAPI"]
    web --> picker["Drive Picker / folder selection"]

    picker --> api
    auth --> web

    api --> verify["Verify Firebase identity<br/>or guest session"]
    api --> gemini["Vertex AI Gemini<br/>gemini-2.5-flash"]
    api --> firestore["Firestore<br/>guest drafts, users, projects,<br/>answers, knowledge, SAD versions, exports"]
    api --> secrets["Secret Manager or approved token store<br/>Drive/Docs OAuth grants"]
    api --> drive["Google Drive API<br/>project repo, sources, wiki, metadata"]
    api --> docs["Google Docs API<br/>SAD Google Doc versions"]

    api --> services["Reusable SADify Python services<br/>schemas, extraction, wiki, SAD, validation"]
    services --> firestore

    drive --> repo["User-owned Drive project repo<br/>Sources / SAD / Wiki / _SADify"]
    docs --> sad["SAD/SAD-v### Google Doc"]
    services --> wiki["Wiki Markdown plan<br/>taxonomy, links, backups"]
```

## First Thin Slice

```text
Next.js frontend
-> FastAPI backend
-> guest Firestore draft
-> live Gemini structured analysis
-> first Q&A state saved
```

## Drive Repo Shape

```text
Project Name/
  Sources/
  SAD/
  Wiki/
  _SADify/
```

## Key Boundaries

| Boundary | Rule |
| --- | --- |
| Frontend to Firestore | Frontend does not write canonical Firestore records directly. |
| Frontend to Drive/Docs | Frontend does not write generated artifacts directly. |
| Backend to Gemini | Gemini responses must validate against strict schemas before use. |
| Backend to Drive/Docs | Backend writes using the user's approved Drive/Docs grant. |
| Wiki updates | Existing wiki is reverified before update; new folders/files require approval. |
| SAD versions | Formal versions are append-only except approved current pointers. |
