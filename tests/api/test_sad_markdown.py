from sadify_api.schemas import SadPreviewResponse
from sadify_api.services.sad_markdown import compose_sad_markdown
from tests.api.test_sad_preview import VALID_PREVIEW


def test_compose_emits_h1_title():
    markdown = compose_sad_markdown(_preview())

    assert markdown.startswith("# Operational Workflow Validation\n")


def test_compose_emits_h2_per_section():
    markdown = compose_sad_markdown(_preview())

    assert "## Problem" in markdown
    assert "## Proposed system" in markdown


def test_compose_includes_assumptions_list_when_present():
    markdown = compose_sad_markdown(_preview())

    assert "## Assumptions" in markdown
    assert "- The preview is based on the current Q&A state only." in markdown


def test_compose_includes_open_questions_list_when_present():
    markdown = compose_sad_markdown(_preview())

    assert "## Open Questions" in markdown
    assert "- Who approves the final workflow before build starts?" in markdown


def test_compose_includes_source_references_footer():
    markdown = compose_sad_markdown(_preview())

    assert "## Source References" in markdown
    assert "- SRC-000001" in markdown


def test_compose_handles_missing_sections_gracefully():
    preview = _preview().model_copy(update={"sections": []})

    markdown = compose_sad_markdown(preview)

    assert markdown.startswith("# Operational Workflow Validation")
    assert "## Assumptions" in markdown


def test_compose_escapes_markdown_special_chars_in_section_text():
    preview = _preview().model_copy(
        update={
            "sections": [
                {
                    "title": "Sensitive *section*",
                    "body": r"Use [role]_name_ and `cost\value` *carefully*.",
                    "source_references": [],
                }
            ]
        }
    )

    markdown = compose_sad_markdown(preview)

    assert r"Use \[role\]\_name\_ and \`cost\\value\` \*carefully\*." in markdown


def _preview() -> SadPreviewResponse:
    return SadPreviewResponse.model_validate(VALID_PREVIEW)
