from __future__ import annotations

from sadify_api.schemas import SadPreviewResponse


def compose_sad_markdown(preview: SadPreviewResponse) -> str:
    lines: list[str] = [
        f"# {preview.title}",
        "",
        f"_{_escape_markdown(preview.temporary_notice)}_",
        "",
    ]

    for section in preview.sections:
        title = _section_value(section, "title")
        body = _section_value(section, "body")
        if not title or not body:
            continue
        lines.extend(
            [
                f"## {title}",
                "",
                _escape_markdown(body),
                "",
            ]
        )

    if preview.assumptions:
        lines.extend(["## Assumptions", ""])
        lines.extend(f"- {_escape_markdown(item)}" for item in preview.assumptions)
        lines.append("")

    if preview.open_questions:
        lines.extend(["## Open Questions", ""])
        lines.extend(f"- {_escape_markdown(item)}" for item in preview.open_questions)
        lines.append("")

    if preview.source_references:
        lines.extend(["## Source References", ""])
        lines.extend(f"- {_escape_markdown(item)}" for item in preview.source_references)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _section_value(section: object, field: str) -> str:
    if isinstance(section, dict):
        return str(section.get(field, ""))
    return str(getattr(section, field, ""))


def _escape_markdown(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for char in ("*", "_", "`", "[", "]"):
        escaped = escaped.replace(char, f"\\{char}")
    return escaped
