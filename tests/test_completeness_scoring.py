from sadify.services.completeness_scoring import score_requirement_context


def test_role_only_input_stays_low_even_when_role_keyword_matches():
    result = score_requirement_context("admin")

    assert result.score <= 10
    assert result.level == "Low"
    assert result.confidence_label == "Low"
    assert "too little business context" in result.confidence_reason.lower()
    assert result.missing_categories[0].area == "Business problem"
    assert result.present_categories == ()


def test_partial_operational_input_scores_middle_with_visible_evidence():
    result = score_requirement_context(
        "Warehouse operators record stock movement by item, quantity, "
        "location, and status. Supervisors review rejected records."
    )

    assert 45 <= result.score <= 75
    assert result.level in {"Partial", "Good"}
    assert result.confidence_label == "Medium"
    assert [category.category for category in result.present_categories] == [
        "business_problem",
        "people",
        "process",
        "details",
        "approval",
        "exceptions",
    ]
    assert any("operators" in evidence for evidence in result.evidence_summary)
    assert any(
        missing.area == "Reports and visibility"
        for missing in result.missing_categories
    )


def test_strong_operational_input_scores_strong_without_live_model():
    result = score_requirement_context(
        "Warehouse operators scan stock during receiving, picking, packing, "
        "and dispatch. They record item code, quantity, location, date, "
        "status, and remarks. Supervisors approve adjustments and rejected "
        "records. Managers need daily dashboards and weekly exports. The "
        "system needs role-based access, audit history, mobile use, fast "
        "busy-hour performance, and safe handling for missing or failed scans."
    )

    assert result.score >= 85
    assert result.level == "Strong"
    assert result.confidence_label == "High"
    assert result.missing_categories == ()
    assert result.scoring_basis == "local deterministic evidence checklist"


def test_vague_people_word_does_not_count_as_clear_people_evidence():
    result = score_requirement_context("people")

    assert result.score <= 10
    assert result.present_categories == ()
    assert result.missing_categories[0].what_is_unclear == (
        "We do not yet know what business problem should be solved."
    )
