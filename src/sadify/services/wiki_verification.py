from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Sequence

from sadify.renderers.wiki_markdown import WikiNoteDraft
from sadify.schemas import KnowledgeItemRecord


@dataclass(frozen=True)
class WikiVerificationIssue:
    code: str
    message: str
    severity: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class WikiVerificationResult:
    status: str
    issues: tuple[WikiVerificationIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "issues": [issue.to_dict() for issue in self.issues],
        }


class WikiApprovalError(ValueError):
    pass


_REQUIRED_FRONTMATTER_FIELDS = (
    "id",
    "type",
    "slug",
    "status",
    "sources",
    "relationships",
    "related",
)

_REQUIRED_SECTIONS = (
    ("summary", "## Summary\n"),
    ("related_notes", "## Related Notes\n"),
    ("sources", "## Sources\n"),
)


def verify_wiki_note(
    note: WikiNoteDraft,
    *,
    all_notes: Sequence[WikiNoteDraft],
) -> WikiVerificationResult:
    issues: list[WikiVerificationIssue] = []
    issues.extend(_frontmatter_issues(note))
    issues.extend(_section_issues(note))
    issues.extend(_broken_link_issues(note, all_notes))

    return WikiVerificationResult(
        status="failed" if issues else "passed",
        issues=tuple(issues),
    )


def prepare_wiki_draft_for_approval(
    *,
    item: KnowledgeItemRecord,
    note: WikiNoteDraft,
    all_notes: Sequence[WikiNoteDraft],
) -> KnowledgeItemRecord:
    verification = verify_wiki_note(note, all_notes=all_notes)
    if verification.status == "passed":
        markdown_status = "pending_human_approval"
        pending_summary = (
            f"Generated wiki draft for {item.title}. "
            "Rule checks passed. Awaiting owner approval."
        )
    else:
        markdown_status = "rule_failed"
        issue_count = len(verification.issues)
        pending_summary = (
            f"Generated wiki draft for {item.title}. "
            f"Rule checks failed with {issue_count} issue(s)."
        )

    return item.model_copy(
        update={
            "markdown_draft": note.markdown,
            "markdown_status": markdown_status,
            "pending_change_summary": pending_summary,
            "verification_result": _verification_payload(verification),
        }
    )


def approve_wiki_draft(
    item: KnowledgeItemRecord,
    *,
    reviewed_by: str,
    reviewed_at: datetime | None = None,
) -> KnowledgeItemRecord:
    _require_pending_draft(item)
    timestamp = reviewed_at or datetime.now(UTC)
    verification_result = _copy_verification_result(item)
    verification_result["human_review"] = {
        "status": "approved",
        "reviewer_role": "owner",
        "reviewed_by": reviewed_by,
        "reviewed_at": timestamp.isoformat(),
    }

    return item.model_copy(
        update={
            "markdown_current": item.markdown_draft,
            "markdown_draft": None,
            "markdown_status": "verified",
            "pending_change_summary": f"Approved by {reviewed_by}.",
            "verification_result": verification_result,
        }
    )


def reject_wiki_draft(
    item: KnowledgeItemRecord,
    *,
    reviewed_by: str,
    reason: str,
    reviewed_at: datetime | None = None,
) -> KnowledgeItemRecord:
    _require_pending_draft(item)
    timestamp = reviewed_at or datetime.now(UTC)
    verification_result = _copy_verification_result(item)
    verification_result["human_review"] = {
        "status": "rejected",
        "reviewer_role": "owner",
        "reviewed_by": reviewed_by,
        "reviewed_at": timestamp.isoformat(),
        "reason": reason,
    }

    return item.model_copy(
        update={
            "markdown_draft": None,
            "markdown_status": "rejected",
            "pending_change_summary": f"Rejected by {reviewed_by}: {reason}",
            "verification_result": verification_result,
        }
    )


def _frontmatter_issues(note: WikiNoteDraft) -> list[WikiVerificationIssue]:
    issues: list[WikiVerificationIssue] = []
    frontmatter = _frontmatter(note.markdown)
    if frontmatter is None:
        return [
            WikiVerificationIssue(
                code="missing_frontmatter",
                message="Wiki note must start with YAML frontmatter.",
                severity="critical",
            )
        ]

    for field in _REQUIRED_FRONTMATTER_FIELDS:
        if not re.search(rf"^{re.escape(field)}:", frontmatter, re.MULTILINE):
            issues.append(
                WikiVerificationIssue(
                    code=f"missing_frontmatter_{field}",
                    message=f"Frontmatter is missing `{field}`.",
                    severity="high",
                )
            )
    return issues


def _section_issues(note: WikiNoteDraft) -> list[WikiVerificationIssue]:
    issues: list[WikiVerificationIssue] = []
    if f"# {note.item_id}" in note.markdown and f"# {note.slug}" in note.markdown:
        issues.append(
            WikiVerificationIssue(
                code="weak_title_heading",
                message="Wiki note heading should use the readable item title.",
                severity="medium",
            )
        )

    if not re.search(r"^# .+", note.markdown, re.MULTILINE):
        issues.append(
            WikiVerificationIssue(
                code="missing_title_heading",
                message="Wiki note is missing a top-level title heading.",
                severity="critical",
            )
        )

    for code, heading in _REQUIRED_SECTIONS:
        if heading not in note.markdown:
            issues.append(
                WikiVerificationIssue(
                    code=f"missing_{code}_section",
                    message=f"Wiki note is missing `{heading.strip()}`.",
                    severity="high",
                )
            )
    return issues


def _broken_link_issues(
    note: WikiNoteDraft,
    all_notes: Sequence[WikiNoteDraft],
) -> list[WikiVerificationIssue]:
    valid_stems = {draft.file_name.removesuffix(".md") for draft in all_notes}
    issues: list[WikiVerificationIssue] = []
    for link in _wiki_links(note.markdown):
        if link not in valid_stems:
            issues.append(
                WikiVerificationIssue(
                    code="broken_wiki_link",
                    message=f"Wiki link target does not exist: [[{link}]].",
                    severity="critical",
                )
            )
    return issues


def _frontmatter(markdown: str) -> str | None:
    if not markdown.startswith("---\n"):
        return None
    parts = markdown.split("---\n", 2)
    if len(parts) < 3:
        return None
    return parts[1]


def _wiki_links(markdown: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\[\[([^\]]+)\]\]", markdown))


def _verification_payload(
    verification: WikiVerificationResult,
) -> dict[str, object]:
    return {
        "rule_based": verification.to_dict(),
        "gemini_quality": {
            "status": "not_run",
            "issues": [],
            "reason": (
                "Live Gemini quality verification is deferred for the local-first "
                "C10 slice."
            ),
        },
        "human_review": {
            "status": "pending",
            "reviewer_role": "owner",
            "reviewed_by": None,
            "reviewed_at": None,
        },
    }


def _require_pending_draft(item: KnowledgeItemRecord) -> None:
    if item.markdown_status != "pending_human_approval" or not item.markdown_draft:
        raise WikiApprovalError(
            "Wiki approval requires markdown_status='pending_human_approval' "
            "and a non-empty markdown_draft."
        )
    verification_result = item.verification_result or {}
    rule_status = (
        verification_result.get("rule_based", {})
        if isinstance(verification_result, dict)
        else {}
    ).get("status")
    if rule_status != "passed":
        raise WikiApprovalError("Wiki approval requires passed rule checks.")


def _copy_verification_result(item: KnowledgeItemRecord) -> dict[str, object]:
    if not isinstance(item.verification_result, dict):
        return {}
    return {
        key: value.copy() if isinstance(value, dict) else value
        for key, value in item.verification_result.items()
    }
