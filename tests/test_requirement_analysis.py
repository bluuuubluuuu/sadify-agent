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
    assert analysis.completeness_score == 72
    assert analysis.completeness_level == "Good"
    assert analysis.confidence_label == "Medium"
    assert analysis.scoring_basis == "local deterministic evidence checklist"
    assert any("Business problem:" in item for item in analysis.evidence_summary)
    assert [item.category for item in analysis.missing_information] == [
        "approval",
        "access",
        "operating_needs",
    ]
    assert len(analysis.clarification_questions) == 3
    assert analysis.draft_allowed is True


def test_analysis_display_copy_is_written_for_business_users():
    analysis = analyze_requirement_text("We need a better system.")

    display = analysis.to_display_dict()

    assert display["sections"] == [
        "What SADify understands",
        "Readiness",
        "Confidence",
        "What we still need to know",
        "Questions to confirm",
        "Draft option",
    ]
    first_missing = display["missing_information"][0]
    assert list(first_missing) == [
        "area",
        "priority",
        "what_is_unclear",
        "why_this_matters",
        "what_to_answer_next",
    ]
    assert first_missing["area"] == "Business problem"
    assert first_missing["priority"] == "Critical"
    assert first_missing["what_is_unclear"] == (
        "We do not yet know what business problem should be solved."
    )
    assert display["clarification_questions"][0]["question"] == (
        "What business problem should the system solve?"
    )


def test_analysis_display_dict_has_no_raw_secret_shaped_data():
    analysis = analyze_requirement_text(
        "Operators need a mobile form to record machine downtime by line, "
        "date, reason, and supervisor review."
    )

    display = analysis.to_display_dict()

    assert display["sections"] == standard_first_response_sections()
    assert display["draft_allowed"] is True
    assert display["scoring_basis"] == "local deterministic evidence checklist"
    assert isinstance(display["evidence_summary"], list)
    assert "api_key" not in str(display).lower()
    assert "token" not in str(display).lower()


def test_keyword_matching_does_not_count_date_inside_update_as_data_field():
    analysis = analyze_requirement_text(
        "Operators update the process when mistakes happen."
    )

    assert "details" in [
        item.category for item in analysis.missing_information
    ]


def test_role_only_input_does_not_inflate_completeness():
    analysis = analyze_requirement_text("admin")

    assert analysis.is_valid is True
    assert analysis.completeness_score <= 10
    assert analysis.confidence_label == "Low"
    assert analysis.missing_information[0].area == "Business problem"
    assert "too little business context" in analysis.confidence_reason.lower()
