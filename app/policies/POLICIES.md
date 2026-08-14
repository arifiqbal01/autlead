# Autlead — Policies Guide

## 1. Purpose

This document defines the policies that govern how Autlead makes decisions about data processing, lead qualification, provider usage, enrichment, intelligence, and outreach.

Policies are different from providers and extraction logic.

A provider answers:

> How do we obtain information?

A pipeline answers:

> In what order do we process information?

A policy answers:

> Under what conditions are we allowed or expected to perform an action?

For example:

```text
Provider
    ↓
Observation
    ↓
Signal
    ↓
Policy
    ↓
Decision


Policies should remain explicit, testable, and explainable.

2. Policy Philosophy

Autlead should use policies to keep business decisions separate from extraction and infrastructure code.

Avoid embedding rules such as:

if score > 70:
    ...

throughout unrelated modules.

Instead, define the policy in one place and make it testable.

Policies should be:

Explicit
Deterministic where possible
Testable
Explainable
Product-aware where necessary
Independent of providers
Independent of Celery
Independent of HTTP clients
Independent of database implementation where practical
3. Policy Categories

Policies will generally fall into these categories:

Policies
├── Data
├── Discovery
├── Enrichment
├── Qualification
├── Scoring
├── Provider
├── Pipeline
├── Retry
├── Outreach
├── Suppression
├── Compliance
└── Intelligence

Do not create every policy category immediately.

Create a policy only when a real decision needs to be centralized.

4. Policy vs Rule

A rule is usually a condition used to derive a signal.

Example:

PageSpeed < 40
    ↓
poor_performance

A policy usually determines what the system should do with the resulting information.

Example:

poor_performance
+
WebArtsy ICP
    ↓
eligible for WebArtsy scoring

Conceptually:

Observation
    ↓
Rule
    ↓
Signal
    ↓
Policy
    ↓
Decision

Keep these concepts separate.

5. Policy Scope

A policy should answer one clear question.

Good:

Should this company be analyzed?
Should this contact be verified?
Should this lead be qualified?
Should this message be sent?
Should this provider be retried?
Should this company be suppressed?

Bad:

LeadManagerPolicy

containing discovery, scoring, verification, outreach, and provider-selection logic.

Prefer small policies with clear responsibilities.

6. Data Collection Policy

Autlead should collect only information that serves a real pipeline requirement.

Before adding a new field, ask:

What feature needs it?
Where will it be used?
Is it required for scoring, qualification, intelligence, or outreach?
Is there already an existing model that represents it?
Does storing it create unnecessary personal-data exposure?

Do not collect information merely because a provider makes it available.

7. Data Minimization

Autlead should follow data minimization.

Collect and retain the smallest useful amount of information needed for the intended pipeline operation.

For company data:

business identity
website
domain
location
relevant business signals

For contact data:

name
role
business email
relevant professional source

Avoid unnecessary personal information.

Do not build personal profiles when a business lead record is sufficient.

8. Provenance Policy

Important data should have a traceable origin.

Where practical, Autlead should be able to determine:

What was discovered?
Where was it discovered?
Which provider produced it?
When was it observed?
How was it transformed?
Which rule produced the resulting signal?

A conclusion without evidence should be treated cautiously.

Example:

Website
    ↓
Crawler Provider
    ↓
Observation
    ↓
Signal Rule
    ↓
Signal
    ↓
Lead Score

This chain should remain explainable.

9. Source Reliability Policy

Not all sources have equal reliability.

Source information may eventually influence confidence.

For example:

Primary company website
        ↓
higher confidence


Third-party directory
        ↓
potentially lower confidence

Do not hard-code arbitrary reliability scores without evidence.

Start with explicit source information and introduce reliability weighting when real data demonstrates a need.

10. Discovery Policy

Discovery should prioritize sources appropriate to the target ICP.

For example:

WebArtsy

Potential sources:

Business directories
Maps/business discovery
Ecommerce-related sources
Local business sources
Autply

Potential sources:

Software/company directories
Ecommerce businesses
Support-related sources
Review sources
Other relevant business databases

The product pipeline decides which discovery strategy to use.

The provider only performs the requested capability.

11. Discovery Deduplication Policy

Repeated discovery of the same company should not create unlimited duplicate records.

Use deterministic identity signals first.

Preferred order may include:

1. Known source identifier
2. Normalized domain
3. Phone
4. Strong business identity match

Do not introduce fuzzy/AI entity resolution until deterministic matching proves insufficient.

12. Website Analysis Policy

A website should only be analyzed when there is a useful reason to do so.

Potential reasons:

WebArtsy qualification
Autply technology detection
Support-channel analysis
Product-specific signal generation

Avoid repeatedly crawling the same website without a reason.

Where practical, cache or persist previous analysis results and observations.

13. Provider Selection Policy

Autlead should not become permanently dependent on one external provider for a capability.

When multiple providers exist, the system may eventually select based on:

Availability
Capability
Source coverage
Data quality
Rate limits
Cost
Geographic coverage
Historical reliability

However:

Do not build a provider-routing system before multiple providers create a real requirement.

Initially, explicitly select the provider.

Later:

Capability
    ↓
Available providers
    ↓
Provider selection policy
    ↓
Selected provider
14. Provider Failure Policy

Provider failure should not automatically mean lead failure.

Classify failures.

Temporary

Examples:

timeout
429
temporary network failure
provider unavailable

These may be retried.

Permanent

Examples:

invalid input
invalid domain
404
unsupported operation

These should generally not be retried indefinitely.

Unknown

Unknown failures should be recorded with enough context for investigation.

15. Retry Policy

Retries should be limited and intentional.

A retry policy should define:

what can retry
maximum attempts
backoff
which errors trigger retry
what happens after exhaustion

Do not use unlimited retries.

Do not retry deterministic failures.

Example:

HTTP 429
    ↓
retry with backoff


Invalid URL
    ↓
no retry
16. Enrichment Policy

Enrichment should happen only when it improves the lead record enough to justify the additional processing.

Typical sequence:

Company
    ↓
Initial qualification
    ↓
Worth enriching?
    ↓
Contact discovery
    ↓
Verification

Do not spend expensive or rate-limited resources enriching every discovered company.

Start with cheap signals and progressively enrich promising records.

17. Progressive Enrichment

Autlead should eventually support staged enrichment.

Example:

Stage 1
Business discovery
    ↓
cheap qualification


Stage 2
Website analysis
    ↓
better qualification


Stage 3
Contact discovery
    ↓
decision maker


Stage 4
Email verification
    ↓
send eligibility

This prevents expensive operations from being performed on obviously irrelevant leads.

18. Verification Policy

Verification should be treated as time-sensitive information.

Do not treat:

verified = true

as permanently true.

A verification result should retain:

provider
status
checked_at
reason

A future policy can decide when a verification result has become stale.

Do not implement automatic re-verification schedules until outreach volume justifies them.

19. Lead Scoring Policy

Lead scoring should be explainable.

Conceptually:

ICP fit
+
Relevant signals
+
Contact quality
+
Business opportunity
=
Lead score

The score should not be treated as an objective truth.

It is a prioritization mechanism.

Store enough information to explain the score.

20. Product-Specific Scoring

Scoring policies belong to the product/ICP.

WebArtsy

Potential scoring factors:

website quality
SEO opportunity
technology
ecommerce opportunity
business category
contact availability
Autply

Potential scoring factors:

support complexity
competitor detected
chat/support technology
multiple channels
customer-support growth
relevant complaints
contact availability

The exact weights should be tuned using real outcomes.

Do not assume initial weights are correct.

21. Qualification Policy

Qualification is separate from scoring.

Example:

Score
+
ICP fit
+
Required contact information
+
No suppression
    ↓
Qualified

Possible states:

qualified
needs_review
parked
rejected

A high score does not automatically mean a lead can be contacted.

22. Send Eligibility Policy

Before outreach, Autlead should evaluate all required conditions.

Conceptually:

Qualified?
   +
Valid contact?
   +
Verification acceptable?
   +
Not suppressed?
   +
Product eligible?
   +
Compliance requirements satisfied?
   ↓
Send eligible

This policy should be centralized.

Do not scatter send checks across email tasks.

23. Suppression Policy

Suppression must take precedence over outreach.

Potential suppression reasons:

unsubscribe
manual exclusion
bounce
complaint
data deletion request
company exclusion
internal exclusion

Conceptually:

Lead
  ↓
Suppression check
  ↓
Suppressed?
 ┌───────┴───────┐
 YES             NO
  ↓               ↓
STOP          Continue

A suppressed company/contact should not accidentally re-enter the outreach pipeline through another product.

24. Cross-Product Suppression

WebArtsy and Autply share infrastructure.

Therefore, suppression should be considered across products where appropriate.

Example:

Company
   ↓
Suppressed
   ↓
WebArtsy ❌
Autply ❌

Do not allow a product-specific pipeline to bypass a global suppression decision.

Product-specific exclusions may still exist where necessary.

25. Outreach Policy

Outreach should initially be human-reviewed.

Preferred early flow:

Lead
 ↓
Intelligence
 ↓
Draft
 ↓
Human review
 ↓
Approval
 ↓
Send

Do not begin with fully autonomous outreach.

Automation can increase gradually after:

Lead quality is validated
Personalization is reliable
Suppression works
Bounce handling works
Compliance controls exist
Sending infrastructure is stable
26. Outreach Volume Policy

Sending volume should be controlled.

Do not make volume scaling the first objective.

Initially:

small volume
+
high-quality leads
+
human review

Then use real metrics to determine whether scaling is justified.

Do not create arbitrary large-volume automation without validation.

27. Compliance Policy

Autlead may process business contact information and may operate across jurisdictions.

Compliance requirements should be considered before scaling outreach.

At minimum, the system should support:

Clear sender identity
Unsubscribe handling
Suppression
Data minimization
Data provenance
Deletion/suppression workflows
Country-aware policies

Do not assume that a single outreach rule applies to every country.

Legal requirements should be verified separately before high-volume campaigns.

This document is an engineering policy, not legal advice.

28. Country Policy

The company/contact record should eventually support country information because outreach rules can differ by jurisdiction.

Country information may influence:

discovery
enrichment
qualification
outreach
volume
compliance checks

Do not hard-code detailed country legislation into generic ETL modules.

Keep jurisdiction-specific policies isolated.

29. Intelligence Policy

LLMs should not be the source of truth for factual observations.

For example, do not ask the LLM:

Does this website use WordPress?

if the technology provider can determine it.

Prefer:

Technology provider
    ↓
WordPress detected
    ↓
Structured observation
    ↓
LLM receives observation
    ↓
LLM interprets business relevance

The LLM should primarily handle:

Interpretation
Reasoning
Summarization
Personalization
Draft generation

Facts should come from evidence-producing systems.

30. LLM Output Policy

LLM output should be structured when consumed programmatically.

Use Pydantic schemas.

Example:

PersonalizationResult
├── primary_observation
├── business_implication
├── pitch_angle
├── confidence
└── draft

Do not rely on free-form LLM output when downstream code requires specific fields.

Validate the output before persistence or outreach.

31. LLM Failure Policy

An LLM failure should not invalidate an otherwise valid lead.

For example:

Lead qualified
    ↓
LLM unavailable
    ↓
Lead remains qualified
    ↓
Intelligence step = failed/pending

The pipeline should be resumable.

LLM availability is not the same as lead validity.

32. Signal Policy

Signals should be based on evidence.

Avoid signals that cannot be explained.

Bad:

AI says this company looks promising.

Better:

Company has:
- relevant ICP category
- weak website
- ecommerce presence
- outdated technology


Therefore:
web_modernization_opportunity

LLM reasoning may assist interpretation, but important signals should remain traceable.

33. Confidence Policy

Confidence should be used where uncertainty genuinely exists.

Examples:

technology detection confidence
contact match confidence
email verification confidence
entity-resolution confidence

Do not assign arbitrary confidence values to everything.

A confidence value should have a meaningful interpretation.

34. Freshness Policy

Some data becomes stale.

Potentially stale information includes:

Website technology
Chat platform
Contact role
Email validity
Reviews
Job postings
Support tooling

When freshness matters, store observation timestamps.

Do not introduce a universal freshness system before the actual use cases require one.

35. Policy Evaluation

Policies should ideally be pure functions or small deterministic components when possible.

Example:

def can_send(lead: LeadContext) -> bool:
    ...

This makes policies:

Easy to test
Easy to reason about
Independent of Celery
Independent of HTTP
Independent of PostgreSQL implementation

Database reads can happen outside the pure policy where practical.

36. Policy Testing

Every important policy should have explicit tests.

Example:

suppressed lead
    → cannot send


unverified email
    → cannot send


qualified + verified + unsuppressed
    → can send

For scoring:

strong signals
    → higher score


irrelevant company
    → low score

For retry:

429
    → retry


invalid input
    → no retry

Policies should be tested around boundary conditions.

37. Policy Versioning

Some policies may eventually affect historical lead scores or qualification decisions.

When a policy becomes important enough to change frequently, consider recording:

policy_name
policy_version

with the resulting decision.

Example:

WebArtsy scoring policy v3
    ↓
score = 78

Do not implement full policy-version infrastructure until policy changes create a real reproducibility requirement.

38. Policy Changes

When changing a policy:

Identify what behavior changes.
Add/update tests.
Determine whether existing records need reprocessing.
Determine whether scores need recalculation.
Consider whether historical results must remain reproducible.
Document the change if it affects lead qualification or outreach.

Do not silently change qualification behavior in production.

39. Provider vs Policy

Never put product decisions inside providers.

Bad:

class GoogleMapsProvider:
    if webartsy_score > 70:
        ...

Correct:

Google Maps Provider
        ↓
BusinessRecord
        ↓
Normalization
        ↓
WebArtsy policy

The provider provides information.

The policy decides what the information means for Autlead.

40. Pipeline vs Policy

Pipelines determine when/where a capability runs.

Policies determine whether/why a decision should occur.

Example:

Pipeline:
    discover
    analyze
    enrich
    verify
    score


Policy:
    should_analyze?
    should_enrich?
    should_verify?
    should_qualify?
    should_send?

Do not put all policy decisions inside pipeline orchestration code.

41. Worker vs Policy

Workers execute tasks.

Workers should not become policy engines.

Bad:

@celery.task
def process_lead():
    if score > 70:
        if email_verified:
            if not suppressed:
                ...

Prefer:

Celery task
    ↓
Application operation
    ↓
Policy evaluation
    ↓
Decision

This keeps policy logic testable without running Celery.

42. Policy Execution Order

A typical lead decision flow is:

Company
    ↓
Basic eligibility
    ↓
Analysis eligibility
    ↓
Enrichment eligibility
    ↓
Verification eligibility
    ↓
Scoring
    ↓
Qualification
    ↓
Suppression check
    ↓
Send eligibility

The exact sequence may differ by pipeline.

43. Fail Closed for High-Risk Actions

For actions that can create external consequences, prefer conservative behavior.

Examples:

Missing suppression status
    → do not send


Unclear unsubscribe state
    → do not send


Invalid recipient
    → do not send


Compliance requirement not satisfied
    → do not send

For non-destructive internal processing, failure may instead result in:

pending
needs_review
retry
44. Manual Review Policy

Manual review should be available when automation lacks sufficient confidence.

Examples:

ambiguous company match
ambiguous contact identity
uncertain email
borderline lead score
uncertain compliance
LLM output failure

Do not force uncertain decisions into qualified or rejected.

Use:

needs_review

when appropriate.

45. Policy Evolution

Policies should evolve based on evidence.

For example:

Initial assumption
      ↓
Real leads
      ↓
Outreach results
      ↓
Conversion data
      ↓
Policy adjustment

Do not optimize policies solely based on theoretical assumptions.

Track outcomes and use them to improve:

Discovery selection
Signals
Scoring
Qualification
Personalization
Outreach
46. What Not to Build

Do not prematurely create:

Universal policy engine
Generic rules DSL
JSON-based policy language
Policy database
Complex rules engine
ML policy system
Automated legal decision engine
Country-specific compliance framework for every jurisdiction

Start with normal Python code.

Introduce a more sophisticated policy mechanism only when real complexity justifies it.

47. Adding a New Policy

Before creating a policy:

Identify the actual decision.
Identify where the decision is currently made.
Determine whether it is reused.
Determine whether centralization improves clarity.
Define the inputs.
Define the output.
Write tests.
Integrate it into the relevant pipeline.

Prefer a small function/class over a framework.

48. Example

A send policy might eventually look conceptually like:

def can_send(context: SendContext) -> bool:
    if context.suppressed:
        return False


    if not context.qualified:
        return False


    if not context.email_verified:
        return False


    if not context.compliance_allowed:
        return False


    return True

The important property is not the exact implementation.

The important property is that the decision is:

Centralized
Explicit
Testable
Explainable
Independent from the email provider
49. Golden Rule

Policies are where Autlead's business decisions live.

Providers answer:

"What can we obtain?"

ETL answers:

"How does information move through the system?"

Models answer:

"What do we store and reason about?"

Policies answer:

"What should Autlead do with what it knows?"

Keep these responsibilities separate.

The objective is not to build a sophisticated policy framework.

The objective is to make important decisions explicit, explainable, testable, and easy to change as real-world evidence changes.