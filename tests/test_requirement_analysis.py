from sadify.services.requirement_analysis import (
    analyze_requirement_text,
    standard_first_response_sections,
)


def test_analyze_requirement_rejects_empty_text():
    analysis = analyze_requirement_text("   ")

    assert analysis.is_valid is False
    assert analysis.validation_error == "Enter an operational problem before analysis."
    assert analysis.completeness_score == 0
    assert analysis.missing_information == ()
    assert analysis.clarification_questions == ()


def test_analyze_requirement_returns_standard_first_response_for_messy_text():
    analysis = analyze_requirement_text(
        "Our warehouse team keeps losing track of stock movement. "
        "Items are moved between locations but operators sometimes forget "
        "to update the record. Supervisors only notice mistakes during "
        "monthly checking. We need a system to fix this."
    )

    assert analysis.is_valid is True
    assert analysis.analysis_mode == "deterministic"
    assert "warehouse team" in analysis.understanding_summary.lower()
    assert analysis.completeness_score == 62
    assert analysis.completeness_level == "Partial"
    assert analysis.confidence_label == "Medium"
    assert [item.category for item in analysis.missing_information] == [
        "Approval rules",
        "Permissions",
        "Non-functional constraints",
    ]
    assert len(analysis.clarification_questions) == 3
    assert analysis.draft_allowed is True


def test_analysis_display_dict_has_no_raw_secret_shaped_data():
    analysis = analyze_requirement_text(
        "Operators need a mobile form to record machine downtime by line, "
        "date, reason, and supervisor review."
    )

    display = analysis.to_display_dict()

    assert display["sections"] == standard_first_response_sections()
    assert display["draft_allowed"] is True
    assert "api_key" not in str(display).lower()
    assert "token" not in str(display).lower()


def test_keyword_matching_does_not_count_date_inside_update_as_data_field():
    analysis = analyze_requirement_text(
        "Operators update the process when mistakes happen."
    )

    assert "Data fields" in [
        item.category for item in analysis.missing_information
    ]
