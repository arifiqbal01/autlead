# app/policies/qualification/people.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DecisionMakerRoleGroup = Literal[
    "primary",
    "secondary",
    "professional",
    "other",
    "unknown",
]

DecisionMakerConfidence = Literal[
    "high",
    "medium",
    "low",
]


@dataclass(frozen=True, slots=True)
class PersonDecisionMakerAssessment:
    role_group: DecisionMakerRoleGroup
    confidence: DecisionMakerConfidence
    ai_decision_maker: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class PersonDecisionMakerDecision:
    is_decision_maker: bool
    role_group: DecisionMakerRoleGroup
    confidence: DecisionMakerConfidence
    reason: str | None


def evaluate_person_decision_maker(
    assessment: PersonDecisionMakerAssessment,
) -> PersonDecisionMakerDecision:
    """
    Apply Autlead's decision-maker qualification policy.

    Gemini provides semantic interpretation.

    This function determines whether Autlead accepts that
    interpretation as a decision-maker classification.
    """

    if not assessment.ai_decision_maker:
        return PersonDecisionMakerDecision(
            is_decision_maker=False,
            role_group=assessment.role_group,
            confidence=assessment.confidence,
            reason=assessment.reason,
        )

    if assessment.role_group == "primary":
        return PersonDecisionMakerDecision(
            is_decision_maker=True,
            role_group="primary",
            confidence=assessment.confidence,
            reason=assessment.reason,
        )

    if (
        assessment.role_group == "secondary"
        and assessment.confidence in {
            "high",
            "medium",
        }
    ):
        return PersonDecisionMakerDecision(
            is_decision_maker=True,
            role_group="secondary",
            confidence=assessment.confidence,
            reason=assessment.reason,
        )

    return PersonDecisionMakerDecision(
        is_decision_maker=False,
        role_group=assessment.role_group,
        confidence=assessment.confidence,
        reason=assessment.reason,
    )