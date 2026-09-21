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
You are validating and refining people extracted from a company website.

Company: {company_name}

Website: {website_url}

The deterministic extractor produced these candidates:

--- BEGIN CANDIDATES ---
{candidate_text}
--- END CANDIDATES ---

Use the supplied website content as the source of truth.

Your primary goal is to refine the deterministic candidates without
discarding legitimate people simply because their role information is
incomplete.

Candidate preservation rules:

- Evaluate every supplied deterministic candidate.
- Preserve a candidate when the website supports that they are a real
  human associated with the company.
- Do not remove a candidate merely because their title is missing.
- Do not remove a candidate merely because their authority is unclear.
- Do not remove a candidate merely because evidence is incomplete.
- When a candidate is clearly a real person but role information is
  insufficient, return them with:
  - role_group = "unknown"
  - decision_maker = false
  - decision_maker_confidence = "low"
- Only exclude a supplied candidate when the website evidence clearly
  indicates that it is a false positive or not a real person.
- The output should normally preserve valid deterministic candidates.
- Returning an empty people list is appropriate only when none of the
  supplied candidates are actually supported as real people and no
  other clearly identified people exist in the supplied website content.

General validation:

- Return only real human people associated with this company.
- Validate deterministic candidates against the website content.
- Remove clear false positives.
- Remove company names mistaken for people.
- Remove brands, products, departments, locations, organizations,
  headings, and generic role labels.
- Merge duplicate representations of the same person.
- Correct a person's name only when the website content clearly supports
  the correction.
- Correct a person's title only when the website content clearly supports
  it.
- Add a person missed by the deterministic extractor only when the
  website content clearly identifies that person.
- Preserve LinkedIn profile URLs only when explicitly supported by the
  supplied content.
- Preserve the original-language professional title when clearly stated.
- Do not invent names.
- Do not invent titles.
- Do not invent LinkedIn URLs.
- Do not infer an identity from a title without a person's name.

Title requirements:

- The title field must contain only the person's actual professional title.
- Keep titles concise.
- Do not include evidence, commentary, explanations, dates, or surrounding
  sentences in the title.
- Do not include prefixes such as "Feedback:", "Role:", "Title:", or
  similar commentary.
- Do not translate a clearly stated title unless necessary to understand it.
- If a person is clearly real but no reliable title is available, use null.

Decision-maker classification:

- Classify every returned person based only on the supplied website
  evidence and company context.
- Set decision_maker to true only when the evidence supports meaningful
  ownership, leadership, management, purchasing, or business decision
  authority.
- Do not mark ordinary employees, assistants, administrative staff,
  junior staff, or individual contributors as decision makers unless
  explicit evidence shows meaningful decision authority.

Use these role groups:

primary:
- Owner, founder, co-founder, partner, managing partner, director,
  managing director, CEO, president, executive, board-level leader,
  or equivalent.
- Include equivalent titles in any language.

secondary:
- Manager, department head, team lead, commercial lead, sales lead,
  operations lead, branch manager, practice manager, or equivalent
  operational leadership role.
- Include equivalent titles in any language.

professional:
- Skilled professional or specialist without clear management or
  ownership authority.

other:
- Real person associated with the company whose role is known but does
  not fit primary, secondary, or professional.

unknown:
- The person is clearly identified, but the supplied content does not
  provide enough reliable role information.

Decision-maker rules:

- primary normally means decision_maker=true when the role is clearly
  supported.
- secondary may mean decision_maker=true when the role indicates
  meaningful operational or purchasing authority.
- professional does not automatically mean decision_maker=true.
- other normally means decision_maker=false.
- unknown normally means decision_maker=false.
- Do not classify someone as a decision maker merely because their surname
  matches the company name.
- Do not infer ownership from prominence on a webpage alone.
- Do not infer management authority from senior-sounding wording unless
  the content supports it.

Decision-maker confidence:

- high: explicit website evidence clearly supports the person's authority.
- medium: strong contextual evidence supports the classification.
- low: role or authority is limited, ambiguous, incomplete, or weakly
  supported.

Decision-maker reason:

- Keep decision_maker_reason short and evidence-based.
- State the specific role or evidence supporting the classification.
- If role information is unavailable, briefly state that authority is not
  established by the supplied content.

Evidence:

- Keep evidence short and factual.
- Evidence must come from the supplied website content.
- Prefer explicit role statements over inference.

Source URL:

- Set source_url to the page URL that supports the person's identity or
  role when identifiable.
- Do not invent a source URL.
- If the exact page cannot be identified, use the main website URL only
  when appropriate.

Final requirements:

- Return each real person only once.
- Prefer the cleanest and best-supported name and title.
- When evidence conflicts, prefer explicit company website statements.
- When evidence is insufficient about a person's role, preserve a
  supported person and use conservative role values rather than dropping
  them.
- Never create information merely to complete a field.

Website content:

--- BEGIN WEBSITE CONTENT ---
{website_text}
--- END WEBSITE CONTENT ---
""".strip()


def _build_candidate_text(
    candidates: list[PersonCandidate],
) -> str:
    if not candidates:
        return "(no deterministic candidates)"

    lines: list[str] = []

    for candidate in candidates:
        lines.append(
            (
                f"- name={candidate.name!r}, "
                f"title={candidate.title!r}, "
                f"linkedin_url={candidate.linkedin_url!r}, "
                f"source_url={candidate.source_url!r}"
            )
        )

    return "\n".join(lines)