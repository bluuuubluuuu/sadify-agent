from __future__ import annotations

import re
import string
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sadify_api.schemas import (
    DriveRepoRecord,
    SadPreviewResponse,
    SadPreviewSection,
    SadSaveRecord,
    SourceRecord,
)

WikiFileCategory = Literal[
    "index",
    "requirements",
    "actors",
    "workflows",
    "entities",
    "decisions",
    "reports",
    "sources",
]

MANAGED_WIKI_FILES: tuple[tuple[str, WikiFileCategory, str, list[str]], ...] = (
    ("Wiki.md", "index", "SADify Project Wiki", ["sadify", "index"]),
    ("requirements.md", "requirements", "Requirements", ["sadify", "requirements"]),
    ("actors.md", "actors", "Actors", ["sadify", "actors"]),
    ("workflows.md", "workflows", "Workflows", ["sadify", "workflows"]),
    ("entities.md", "entities", "Entities", ["sadify", "entities"]),
    ("decisions.md", "decisions", "Decisions", ["sadify", "decisions"]),
    ("reports.md", "reports", "Reports", ["sadify", "reports"]),
    ("sources.md", "sources", "Sources", ["sadify", "sources"]),
)
MANAGED_WIKI_FILE_NAMES: tuple[str, ...] = tuple(file[0] for file in MANAGED_WIKI_FILES)

_ROUTE_RULES: tuple[tuple[tuple[str, ...], WikiFileCategory], ...] = (
    (("goal", "scope"), "requirements"),
    (("user", "role", "actor"), "actors"),
    (("access", "permission"), "actors"),
    (("workflow", "step", "flow", "handoff"), "workflows"),
    (("exception", "edge case"), "workflows"),
    (("data", "record", "field", "entity"), "entities"),
    (("rule", "approval"), "decisions"),
    (("non functional", "nfr"), "decisions"),
    (("report", "summary"), "reports"),
    (("integration",), "reports"),
)


@dataclass(frozen=True)
class WikiFileDraft:
    name: str
    category: WikiFileCategory
    markdown: str


def compose_wiki_files(
    *,
    repo: DriveRepoRecord,
    latest_save: SadSaveRecord,
    latest_preview: SadPreviewResponse,
    all_saves_for_repo: list[SadSaveRecord],
    sources: list[SourceRecord],
    requirement_text: str,
    composed_at: datetime | None = None,
) -> list[WikiFileDraft]:
    updated_at = composed_at or datetime.now(UTC)
    routed = _route_sections(latest_preview.sections)

    return [
        WikiFileDraft(
            name="Wiki.md",
            category="index",
            markdown=_index_markdown(
                repo=repo,
                latest_save=latest_save,
                all_saves_for_repo=all_saves_for_repo,
                updated_at=updated_at,
            ),
        ),
        WikiFileDraft(
            name="requirements.md",
            category="requirements",
            markdown=_requirements_markdown(
                latest_preview=latest_preview,
                requirement_text=requirement_text,
                sections=routed["requirements"],
                other_sections=routed["other"],
                updated_at=updated_at,
            ),
        ),
        WikiFileDraft(
            name="actors.md",
            category="actors",
            markdown=_section_note_markdown(
                title="Actors",
                tags=["sadify", "actors"],
                sections=routed["actors"],
                empty_message="No actor or permission sections have been confirmed yet.",
                updated_at=updated_at,
            ),
        ),
        WikiFileDraft(
            name="workflows.md",
            category="workflows",
            markdown=_section_note_markdown(
                title="Workflows",
                tags=["sadify", "workflows"],
                sections=routed["workflows"],
                empty_message="No workflow or exception sections have been confirmed yet.",
                updated_at=updated_at,
            ),
        ),
        WikiFileDraft(
            name="entities.md",
            category="entities",
            markdown=_section_note_markdown(
                title="Entities",
                tags=["sadify", "entities"],
                sections=routed["entities"],
                empty_message="No data or entity sections have been confirmed yet.",
                updated_at=updated_at,
            ),
        ),
        WikiFileDraft(
            name="decisions.md",
            category="decisions",
            markdown=_section_note_markdown(
                title="Decisions",
                tags=["sadify", "decisions"],
                sections=routed["decisions"],
                empty_message="No rules, approvals, or NFR sections have been confirmed yet.",
                updated_at=updated_at,
            ),
        ),
        WikiFileDraft(
            name="reports.md",
            category="reports",
            markdown=_section_note_markdown(
                title="Reports",
                tags=["sadify", "reports"],
                sections=routed["reports"],
                empty_message="No report or integration sections have been confirmed yet.",
                updated_at=updated_at,
            ),
        ),
        WikiFileDraft(
            name="sources.md",
            category="sources",
            markdown=_sources_markdown(
                sources=sources,
                updated_at=updated_at,
            ),
        ),
    ]


def _route_sections(
    sections: list[SadPreviewSection],
) -> dict[WikiFileCategory | Literal["other"], list[SadPreviewSection]]:
    routed: dict[WikiFileCategory | Literal["other"], list[SadPreviewSection]] = {
        "requirements": [],
        "actors": [],
        "workflows": [],
        "entities": [],
        "decisions": [],
        "reports": [],
        "other": [],
    }
    for section in sections:
        category = _category_for_section(section.title)
        routed[category].append(section)
    return routed


def _category_for_section(title: str) -> WikiFileCategory | Literal["other"]:
    normalized = _normalize_title(title)
    for terms, category in _ROUTE_RULES:
        if any(term in normalized for term in terms):
            return category
    return "other"


def _normalize_title(title: str) -> str:
    translation = str.maketrans({char: " " for char in string.punctuation})
    lowered = title.lower().translate(translation)
    return re.sub(r"\s+", " ", lowered).strip()


def _index_markdown(
    *,
    repo: DriveRepoRecord,
    latest_save: SadSaveRecord,
    all_saves_for_repo: list[SadSaveRecord],
    updated_at: datetime,
) -> str:
    lines = [
        _frontmatter(
            title="SADify Project Wiki",
            tags=["sadify", "index"],
            updated_at=updated_at,
            extra={
                "project_repo": repo.repo_folder_name,
                "repo_grant_id": repo.grant_id,
                "latest_save_id": latest_save.save_id,
            },
        ),
        "# SADify Project Wiki",
        "",
        f"**Project repo:** {_escape_markdown(repo.repo_folder_name)}",
        f"**Latest SAD:** {_sad_link(latest_save)}",
        "",
        "## Knowledge Notes",
        "",
    ]
    lines.extend(
        [
            "- [[requirements]]",
            "- [[actors]]",
            "- [[workflows]]",
            "- [[entities]]",
            "- [[decisions]]",
            "- [[reports]]",
            "- [[sources]]",
            "",
            "## Save History",
            "",
        ]
    )
    for save in all_saves_for_repo:
        lines.append(
            f"- {save.save_id} - {save.created_at.isoformat()} - {_doc_link(save)}"
        )
    return _join(lines)


def _requirements_markdown(
    *,
    latest_preview: SadPreviewResponse,
    requirement_text: str,
    sections: list[SadPreviewSection],
    other_sections: list[SadPreviewSection],
    updated_at: datetime,
) -> str:
    lines = [
        _frontmatter(
            title="Requirements",
            tags=["sadify", "requirements"],
            updated_at=updated_at,
        ),
        "# Requirements",
        "",
        "## Original Requirement",
        "",
        _escape_markdown(requirement_text),
        "",
    ]
    _append_sections(lines, sections, empty_message="No goal or scope sections have been confirmed yet.")
    if other_sections:
        lines.extend(["", "## Other", ""])
        _append_sections(lines, other_sections, heading_level="###")
    lines.extend(["", "## Assumptions", ""])
    _append_list(lines, latest_preview.assumptions, empty_message="No assumptions recorded.")
    lines.extend(["", "## Open Questions", ""])
    _append_list(lines, latest_preview.open_questions, empty_message="No open questions recorded.")
    return _join(lines)


def _section_note_markdown(
    *,
    title: str,
    tags: list[str],
    sections: list[SadPreviewSection],
    empty_message: str,
    updated_at: datetime,
) -> str:
    lines = [
        _frontmatter(title=title, tags=tags, updated_at=updated_at),
        f"# {_escape_markdown(title)}",
        "",
    ]
    _append_sections(lines, sections, empty_message=empty_message)
    return _join(lines)


def _sources_markdown(*, sources: list[SourceRecord], updated_at: datetime) -> str:
    lines = [
        _frontmatter(title="Sources", tags=["sadify", "sources"], updated_at=updated_at),
        "# Sources",
        "",
        "## Uploaded Sources",
        "",
    ]
    if not sources:
        lines.append("- No uploaded sources linked to the latest saved SAD.")
        return _join(lines)

    for source in sources:
        lines.extend(
            [
                f"### {_escape_markdown(source.source_id)} - {_escape_markdown(source.original_file_name)}",
                "",
                f"- **Type:** {_escape_markdown(source.source_type)}",
                f"- **Status:** {_escape_markdown(source.extraction_status)}",
                "",
                _escape_markdown(_source_snippet(source)),
                "",
            ]
        )
    return _join(lines)


def _append_sections(
    lines: list[str],
    sections: list[SadPreviewSection],
    *,
    heading_level: str = "##",
    empty_message: str | None = None,
) -> None:
    if not sections:
        if empty_message:
            lines.append(f"- {_escape_markdown(empty_message)}")
        return

    for index, section in enumerate(sections):
        if index:
            lines.append("")
        lines.extend(
            [
                f"{heading_level} {_escape_markdown(section.title)}",
                "",
                _escape_markdown(section.body),
            ]
        )
        if section.source_references:
            refs = ", ".join(_escape_markdown(ref) for ref in section.source_references)
            lines.extend(["", f"Source refs: {refs}"])


def _append_list(lines: list[str], values: list[str], *, empty_message: str) -> None:
    if values:
        lines.extend(f"- {_escape_markdown(value)}" for value in values)
    else:
        lines.append(f"- {_escape_markdown(empty_message)}")


def _frontmatter(
    *,
    title: str,
    tags: list[str],
    updated_at: datetime,
    extra: dict[str, str] | None = None,
) -> str:
    lines = [
        "---",
        f"title: {_yaml_value(title)}",
        f"tags: [{', '.join(tags)}]",
        f"updated_at: {_yaml_value(updated_at.isoformat())}",
    ]
    for key, value in (extra or {}).items():
        lines.append(f"{key}: {_yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def _sad_link(save: SadSaveRecord) -> str:
    if save.sad_doc.url:
        return f"[{_escape_markdown(save.preview_id)}]({save.sad_doc.url})"
    return _escape_markdown(save.preview_id)


def _doc_link(save: SadSaveRecord) -> str:
    if save.sad_doc.url:
        return f"[doc]({save.sad_doc.url})"
    return "doc unavailable"


def _source_snippet(source: SourceRecord) -> str:
    text = (source.extracted_text_preview or source.extracted_text or "").strip()
    if len(text) <= 500:
        return text
    return text[:497].rstrip() + "..."


def _yaml_value(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9 _./:-]+", value):
        return value
    return "'" + value.replace("'", "''") + "'"


def _escape_markdown(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for char in ("*", "_", "`", "[", "]"):
        escaped = escaped.replace(char, f"\\{char}")
    return escaped.replace("<", "&lt;").replace(">", "&gt;")


def _join(lines: list[str]) -> str:
    return "\n".join(lines).strip() + "\n"
