"""Validate AI-judged slot evidence and derive readiness confidence.

The analysis model returns one evidence verdict per required slot. The backend
never trusts a verdict's strength unless a partial or strong verdict cites a
quote that actually appears in the supplied material. This keeps readiness
grounded in real evidence and blocks hallucinated coverage.
"""

from typing import Literal

from sadify_api.schemas import SlotEvidence

_DOWNGRADE = {"strong": "partial", "partial": "none", "none": "none"}


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


def validate_slot_evidence(
    verdicts: list[SlotEvidence],
    *,
    material: str,
) -> tuple[list[SlotEvidence], list[str]]:
    """Return quote-validated verdicts plus human-readable diagnostics.

    A partial or strong verdict whose evidence_quote is empty or not present in
    the material is downgraded one notch (strong -> partial -> none).
    """
    normalised_material = _normalise(material)
    validated: list[SlotEvidence] = []
    diagnostics: list[str] = []
    for verdict in verdicts:
        if verdict.strength in ("partial", "strong"):
            quote = _normalise(verdict.evidence_quote)
            if not quote or quote not in normalised_material:
                downgraded = _DOWNGRADE[verdict.strength]
                diagnostics.append(
                    f"{verdict.category_id}.{verdict.slot_id}: "
                    f"{verdict.strength} downgraded to {downgraded} "
                    "because the cited evidence was not found."
                )
                validated.append(
                    verdict.model_copy(update={"strength": downgraded})
                )
                continue
        validated.append(verdict)
    return validated, diagnostics


def evidence_map(
    verdicts: list[SlotEvidence],
) -> dict[tuple[str, str], SlotEvidence]:
    """Index verdicts by (category_id, slot_id). Later entries win."""
    return {
        (verdict.category_id, verdict.slot_id): verdict for verdict in verdicts
    }


_STRENGTH_RANK = {"none": 0, "partial": 1, "strong": 2}


def merge_evidence(
    *,
    prior: list[SlotEvidence],
    new: list[SlotEvidence],
    edited_slots: set[tuple[str, str]],
) -> list[SlotEvidence]:
    """Monotonic carry-forward merge of prior + new slot-evidence verdicts.

    Per (category, slot):
    - if the slot is in `edited_slots` (the user changed an earlier answer for
      this slot) -> use the new verdict only;
    - else take the stronger of prior/new (strong > partial > none);
    - `not_applicable` is sticky: once either side marks the slot
      not_applicable, the merged verdict stays not_applicable;
    - a slot present on only one side carries through unchanged.

    The goal is to stop the per-turn flicker SADify was hitting where a slot
    judged `strong` last turn could regress to `partial` or `none` this turn
    just because the model output varies. Once evidence is established, it
    sticks until the user explicitly edits that answer.
    """
    prior_map = {} if not prior else evidence_map(prior)
    new_map = {} if not new else evidence_map(new)
    keys = set(prior_map) | set(new_map)
    merged: list[SlotEvidence] = []
    for key in keys:
        n = new_map.get(key)
        p = None if key in edited_slots else prior_map.get(key)
        if p is None and n is None:
            continue
        if p is None:
            merged.append(n)
            continue
        if n is None:
            merged.append(p)
            continue
        winner = n if _STRENGTH_RANK[n.strength] >= _STRENGTH_RANK[p.strength] else p
        applicability = (
            "not_applicable"
            if "not_applicable" in (p.applicability, n.applicability)
            else "applicable"
        )
        merged.append(winner.model_copy(update={"applicability": applicability}))
    return merged


def derive_confidence(
    verdicts: list[SlotEvidence],
    *,
    downgrade_count: int,
) -> Literal["Low", "Medium", "High"]:
    """Derive readiness confidence from the verdict mix.

    High: at least 70% of applicable verdicts are strong and nothing was
    downgraded. Low: more than half are none, or two or more downgrades.
    Medium: anything else.
    """
    applicable = [v for v in verdicts if v.applicability == "applicable"]
    total = len(applicable)
    if total == 0:
        return "Low"
    strong = sum(1 for v in applicable if v.strength == "strong")
    none = sum(1 for v in applicable if v.strength == "none")
    if downgrade_count >= 2 or none > total / 2:
        return "Low"
    if strong / total >= 0.7 and downgrade_count == 0:
        return "High"
    return "Medium"
