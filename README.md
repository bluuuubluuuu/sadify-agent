# SADify

SADify is an AI system analyst prototype for the Google for Startups AI Agents Challenge.

It helps non-technical production and operations users turn messy business requirements into clarified, complete, developer-ready System Analysis and Design documents.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and fill in private local values.

If editable install fails because of local temp-folder permissions, use the direct requirements files:

```powershell
pip install -r requirements-dev.txt
```

## Run Tests

```powershell
.\.venv\Scripts\pytest.exe
```

## Run App

```powershell
.\.venv\Scripts\streamlit.exe run src/sadify/app.py
```

## ADK Agent

The ADK-compatible agent entrypoint lives in:

```text
sadify_agent/agent.py
```

It exports:

```text
root_agent
```
