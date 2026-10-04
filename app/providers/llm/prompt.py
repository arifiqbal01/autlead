# app/providers/llm/prompt.py

from __future__ import annotations

from app.models.schemas.people import PersonCandidate


def build_people_prompt(
    *,
    company_name: str,
    website_url: str,
    website_text: str,
    candidates: list[PersonCandidate],
) -> str:
    candidate_text = _build_candidate_text(
        candidates
    )

    return f"""
Validate the supplied person candidates using only the website
content below.

Company: {company_name}
Website: {website_url}

CANDIDATES:
{candidate_text}

Rules:
- Evaluate every candidate.
- Keep people supported as real humans associated with the company.
- Remove clear false positives such as companies, brands,
  departments, locations, headings, and generic role labels.
- Do not add people outside the candidate list.
- Merge duplicates.
- Correct names or titles only when clearly supported.
- Never invent information.
- If a person is valid but their title or authority is unclear,
  keep them with conservative values.

Role groups:
- primary: owner, founder, partner, director, CEO, executive,
  or equivalent leadership.
- secondary: manager, department/team/practice/branch lead,
  or equivalent operational leadership.
- professional: skilled professional without clear leadership.
- other: known role outside the groups above.
- unknown: insufficient reliable role information.

Decision maker:
- true only with evidence of ownership, leadership, management,
  purchasing, or meaningful business authority.
- primary normally=true when supported.
- secondary may=true when meaningful authority is supported.
- professional, other, and unknown normally=false.

Confidence:
- high: explicit evidence.
- medium: strong contextual evidence.
- low: ambiguous or incomplete evidence.

Keep evidence and decision_maker_reason short and factual.
Preserve source/LinkedIn URLs only when supported.
Use null when no reliable title is available.

WEBSITE CONTENT:
{website_text}
""".strip()


def _build_candidate_text(
    candidates: list[PersonCandidate],
) -> str:
    if not candidates:
        return "(no deterministic candidates)"

    lines: list[str] = []

    for candidate in candidates:
        lines.append(
            
                f"- name={candidate.name!r}, "
                f"title={candidate.title!r}, "
                f"linkedin_url={candidate.linkedin_url!r}, "
                f"source_url={candidate.source_url!r}"
            
        )

    return "\n".join(lines)