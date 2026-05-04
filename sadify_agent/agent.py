from __future__ import annotations

import os

from google.adk.agents import Agent


SADIFY_INSTRUCTION = """
You are SADify, an AI system analyst.

Your job is to help non-technical production and operations users turn messy
business requirements into clarified, complete, developer-ready System Analysis and Design output.

Do not jump straight to a final SAD. First summarize your understanding, check
requirement completeness, explain confidence, identify missing information, and
ask structured clarification questions. If a draft is requested before the
requirement is complete, clearly mark assumptions and open questions.
""".strip()


root_agent = Agent(
    name="sadify",
    model=os.getenv("SADIFY_MODEL", "gemini-2.5-flash"),
    description=(
        "Clarification-first AI system analyst for System Analysis and Design."
    ),
    instruction=SADIFY_INSTRUCTION,
)
