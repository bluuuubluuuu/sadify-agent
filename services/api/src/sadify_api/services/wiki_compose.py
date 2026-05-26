from __future__ import annotations

from sadify_api.schemas import DriveRepoRecord, SadSaveRecord, SourceRecord


def compose_wiki_markdown(
    *,
    repo: DriveRepoRecord,
    latest_save: SadSaveRecord,
    all_saves_for_repo: list[SadSaveRecord],
    sources: list[SourceRecord],
    requirement_text: str,
) -> str:
    lines = [
        "# SADify Project Wiki",
        "",
        f"**Project repo:** {_escape_markdown(repo.repo_folder_name)}",
        f"**Updated:** {latest_save.updated_at.isoformat()}",
        "",
        "## Latest SAD",
        "",
        _sad_link(latest_save),
        "",
        "### Requirement",
        _escape_markdown(requirement_text),
        "",
        "### Section summaries",
        _section_summary(latest_save),
        "",
        "## Sources",
        "",
    ]

    if sources:
        lines.extend(
            f"- {_escape_markdown(source.original_file_name)}" for source in sources
        )
    else:
        lines.append("- No uploaded sources linked to the latest saved SAD.")

    lines.extend(["", "## Save history", ""])
    for save in all_saves_for_repo:
        lines.append(
            f"- {save.save_id} - {save.created_at.isoformat()} - {_doc_link(save)}"
        )

    return "\n".join(lines).strip() + "\n"


def _sad_link(save: SadSaveRecord) -> str:
    if save.sad_doc.url:
        return f"[{_escape_markdown(save.preview_id)}]({save.sad_doc.url})"
    return _escape_markdown(save.preview_id)


def _doc_link(save: SadSaveRecord) -> str:
    if save.sad_doc.url:
        return f"[doc]({save.sad_doc.url})"
    return "doc unavailable"


def _section_summary(save: SadSaveRecord) -> str:
    title = _escape_markdown(save.manifest.sad_title)
    count = save.manifest.preview_section_count
    return f"- **{title}:** {count} sections saved for this SAD preview."


def _escape_markdown(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for char in ("*", "_", "`", "[", "]"):
        escaped = escaped.replace(char, f"\\{char}")
    return escaped.replace("<", "&lt;").replace(">", "&gt;")
