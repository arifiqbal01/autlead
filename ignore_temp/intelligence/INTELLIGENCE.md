# Autlead — Intelligence Guide

## 1. Purpose

The Intelligence layer converts structured lead data into useful business understanding and actionable output.

It sits after extraction, analysis, enrichment, signals, scoring, and qualification.

Conceptually:

    External Sources
          ↓
    Observations
          ↓
    Signals
          ↓
    Lead Score
          ↓
    Qualification
          ↓
    Intelligence
          ↓
    Action / Outreach

The Intelligence layer should answer questions such as:

- Why is this company relevant?
- What is the strongest opportunity?
- What evidence supports that conclusion?
- What problem might the company have?
- Which product is relevant?
- What should WebArtsy or Autply offer?
- What is the strongest personalization angle?
- How should the lead be approached?

---

# 2. Intelligence Philosophy

Intelligence must be based on evidence.

Autlead should not ask an LLM to discover facts that the extraction and analysis pipeline can already determine.

Prefer:

    Provider
       ↓
    Observation
       ↓
    Signal
       ↓
    Deterministic interpretation
       ↓
    LLM reasoning/writing

Not:

    Raw website
       ↓
    LLM
       ↓
    "Maybe this company needs our service"

The LLM is an intelligence component, not the source of truth.

---

# 3. Facts vs Interpretation

Keep factual information separate from interpretation.

### Fact

    WordPress detected.

### Observation

    WordPress detected by technology provider
    confidence = 0.96

### Signal

    Website modernization opportunity

### Interpretation

    The company's current website may have an opportunity for modernization.

### Outreach angle

    Offer a website modernization review.

These are different levels of information.

Conceptually:

    FACT
      ↓
    OBSERVATION
      ↓
    SIGNAL
      ↓
    INTERPRETATION
      ↓
    ACTION

---

# 4. Intelligence Inputs

The intelligence layer should consume structured information.

Typical inputs:

    Company
    Website
    Observations
    Signals
    Contacts
    Verification results
    Lead score
    Qualification
    Product
    Product knowledge

Example:

    Company
        ├── name
        ├── domain
        └── location

    Observations
        ├── technology
        ├── website
        └── performance

    Signals
        ├── poor_mobile_performance
        └── website_modernization_opportunity

    LeadScore
        └── 82

    Product
        └── webartsy

These structured inputs become the intelligence context.

---

# 5. Intelligence Outputs

The output should be structured.

A potential result:

    IntelligenceResult
        ├── summary
        ├── strongest_observation
        ├── business_implication
        ├── opportunity
        ├── pitch_angle
        ├── personalization
        ├── confidence
        └── draft

The exact schema should remain small and should evolve as the real pipeline requires more information.

Do not create a huge LLM response schema upfront.

---

# 6. Deterministic Intelligence First

Not every intelligence task requires an LLM.

Use deterministic logic for:

- Signal extraction
- Score calculation
- ICP matching
- Qualification
- Known technology interpretation
- Simple categorization
- Rule-based opportunity detection

Use an LLM when the task benefits from language reasoning.

Examples:

- Summarization
- Combining multiple observations
- Hypothesis generation
- Personalization
- Message drafting
- Natural-language explanation

Prefer deterministic logic whenever it can solve the problem reliably.

---

# 7. LLM Responsibilities

The LLM should primarily handle:

    Interpretation
    Reasoning
    Summarization
    Personalization
    Writing

It should not be responsible for:

    Company identity
    Domain normalization
    Email verification
    Technology detection
    Database state
    Lead qualification rules
    Suppression decisions

These belong elsewhere in Autlead.

---

# 8. LLM Provider

LLMs should be integrated through a provider protocol.

Example:

    app/providers/llm/
        protocol.py
        ollama.py

Conceptually:

```python
class LLMProvider(Protocol):
    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        ...


The application depends on the capability.

It should not depend directly on Ollama throughout the codebase.

9. Ollama

Ollama is the initial local LLM provider.

Potential models may include:

Llama
Qwen
Other suitable local models

The specific model should remain configuration rather than being hard-coded throughout the intelligence layer.

The intelligence layer should not need to know which model is running.

10. Structured LLM Output

When downstream code needs specific fields, require structured output.

Example:

class IntelligenceResult(BaseModel):
    summary: str
    strongest_observation: str
    business_implication: str
    opportunity: str
    pitch_angle: str
    personalization: str
    confidence: float

Validate the result before using it.

If validation fails:

LLM output
     ↓
Validation failure
     ↓
retry / repair / manual review

Do not blindly persist malformed output.

11. Evidence Context

The LLM should receive relevant evidence rather than an uncontrolled dump of all available data.

Example:

Company:
    Example Business


Relevant observations:
    WordPress detected
    mobile performance = 32
    missing meta description


Signals:
    poor_mobile_performance
    website_modernization_opportunity


Product:
    WebArtsy

This produces a focused intelligence request.

12. Evidence Selection

The intelligence layer should eventually select the most relevant evidence.

Not every observation is useful for every product.

For WebArtsy:

website performance
technology
SEO observations
ecommerce signals

may be important.

For Autply:

support platform
chat provider
support channels
competitor technology

may be important.

Avoid sending irrelevant information to the LLM.

13. Evidence Hierarchy

When multiple pieces of information exist, prefer stronger evidence.

Conceptually:

Direct observation
    ↓
Strong derived signal
    ↓
Weak inference
    ↓
Generic assumption

The LLM should be encouraged to distinguish these.

For example:

Bad:

"They probably struggle with customer support."

Better:

"Their site exposes email, live chat, and social support channels but no unified support platform was detected."

The second statement is grounded in observations.

14. No Hallucinated Facts

The intelligence layer must not invent:

Technologies
Features
Customers
Employees
Revenue
Problems
Complaints
Product usage
Business priorities

If evidence is insufficient, the result should say so.

Example:

Evidence:
    WordPress detected

Valid:

"Their website is running WordPress."

Invalid:

"Their team is struggling to maintain WordPress."

The second statement is an unsupported assumption.

15. Confidence

Intelligence results may include confidence where useful.

Confidence should represent uncertainty in the interpretation.

It should not be a meaningless number generated for every response.

For example:

Observation:
    Zendesk detected


Interpretation:
    Existing support platform may create a competitive displacement opportunity.

The interpretation can have lower confidence than the underlying technology observation.

Keep those concepts separate.

16. Business Hypotheses

Intelligence may generate hypotheses.

A hypothesis is not a fact.

Example:

Observation:
    Multiple support channels detected


Signal:
    multi_channel_support


Hypothesis:
    The company may benefit from centralized support handling.

The system should distinguish:

observed
inferred
hypothesized

This prevents assumptions from becoming database facts.

17. WebArtsy Intelligence

WebArtsy intelligence should focus on digital/web opportunities.

Potential reasoning areas:

Website modernization
SEO
Ecommerce
Performance
Conversion opportunities
Technology modernization
Custom software opportunities
ERP opportunities

Example:

Observations:
    WordPress
    poor mobile performance
    weak metadata


    ↓


Signals:
    poor_mobile_performance
    SEO_opportunity
    modernization_opportunity


    ↓


Intelligence:


"The website is functional but shows several modernization
opportunities, particularly mobile performance and SEO metadata."

The output should focus on evidence rather than generic agency language.

18. Autply Intelligence

Autply intelligence should focus on customer-support and communication workflows.

Potential reasoning areas:

Support complexity
Multiple channels
Existing support platforms
Competitor displacement
Customer-service growth
Support-team scaling
Potential inbox fragmentation

Example:

Observations:
    live chat detected
    email support visible
    Zendesk detected


    ↓


Signals:
    multi_channel_support
    existing_support_platform


    ↓


Intelligence:


"The company already operates a structured support workflow
and may be a candidate for evaluating a unified support experience."

The conclusion should remain appropriately cautious.

19. Product Knowledge

Intelligence depends on product knowledge.

Knowledge lives outside core pipeline code.

Example:

knowledge/
    webartsy/
        icp.md
        services.md
        positioning.md
        objections.md
        messaging.md


    autply/
        icp.md
        product.md
        competitors.md
        positioning.md
        messaging.md

The intelligence layer combines:

Lead evidence
    +
Product knowledge
    ↓
Product-specific interpretation
20. Product Context

Every intelligence request should know which product it is serving.

For example:

target_product = webartsy

or:

target_product = autply

The same company can potentially produce different interpretations.

Example:

Company
   ↓
Evidence
   ├───────────────┐
   ↓               ↓
WebArtsy         Autply
interpretation   interpretation

Do not force one generic lead interpretation across all products.

21. Strongest Observation

A useful intelligence result should identify the strongest relevant evidence.

Example:

strongest_observation:
    "Mobile performance score is 31."

This prevents generic personalization.

Instead of:

"I noticed some opportunities on your website."

Prefer:

"I noticed your mobile performance is currently quite low."

Only make this statement when the observation actually exists.

22. Business Implication

The next step is interpreting why the observation matters.

Example:

Observation:
    mobile performance = 31


Business implication:
    Slow mobile experience may affect usability and conversion.

The implication is an interpretation.

It should not be presented as a confirmed business outcome unless evidence exists.

23. Opportunity

An opportunity connects the evidence to the product.

Example:

Observation:
    poor mobile performance


Signal:
    website_modernization_opportunity


Opportunity:
    website performance and UX improvement

The opportunity should be relevant to the product's actual capabilities.

24. Pitch Angle

The pitch angle describes what should be offered.

Example:

Evidence:
    poor mobile performance


Pitch angle:
    offer a quick performance/UX review

Avoid generic:

"We provide digital solutions."

Prefer an angle derived from the actual evidence.

25. Personalization

Personalization should be specific and evidence-based.

Weak:

"I came across your company and thought you might be interested."

Strong:

"I noticed your ecommerce site is running on Shopify but the mobile experience appears significantly slower than expected."

Only mention facts that Autlead has actually observed.

26. Message Generation

Message generation is the final intelligence step before outreach.

Conceptually:

Evidence
    ↓
Signals
    ↓
Product opportunity
    ↓
Pitch angle
    ↓
Personalization
    ↓
Draft

The draft should not introduce new facts that were not present in the intelligence context.

27. Cold Outreach Draft Policy

Early drafts should be:

Concise
Specific
Evidence-based
Professional
Low-pressure
Relevant to the recipient's role
Focused on one strong observation

Avoid:

Generic marketing language
Excessive praise
Unsupported claims
Fake familiarity
Multiple unrelated offers
Long explanations
Artificial urgency
28. Intelligence Does Not Decide Whether to Send

The intelligence layer can produce:

draft
pitch angle
personalization

It should not decide:

"Send this email."

Send eligibility belongs to outreach and policy layers.

Conceptually:

Intelligence
    ↓
Draft
    ↓
Outreach Policy
    ↓
Send / Do Not Send
29. Intelligence Failure

An LLM failure should not invalidate the lead.

Example:

Qualified Lead
      ↓
Intelligence
      ↓
   failure
      ↓
Lead remains qualified

The intelligence stage can become:

pending
failed
needs_review

and be retried later.

Do not destroy successful earlier ETL work because the LLM is unavailable.

30. Retry Policy

LLM requests may fail because of:

Temporary provider failure
Model unavailable
Timeout
Invalid response
Output validation failure

Possible handling:

temporary failure
    ↓
retry with backoff


malformed structured output
    ↓
retry/repair


repeated failure
    ↓
mark intelligence step failed
    ↓
manual review or later retry

Do not retry indefinitely.

31. Prompt Design

Prompts should be treated as application assets.

Keep product-specific prompts separate.

Example:

app/intelligence/prompts/
    webartsy.py
    autply.py

Prompts should define:

Role
Product context
Available evidence
Output requirements
Restrictions
Tone
Desired structure

Do not scatter prompt strings throughout business logic.

32. Prompt Inputs

Provide only relevant structured context.

Example:

Product:
WebArtsy


Company:
Example Business


Relevant observations:
- WordPress detected
- mobile performance: 31
- missing meta description


Relevant signals:
- poor_mobile_performance
- SEO opportunity


Contact:
John Doe
Founder

Avoid dumping the entire database record into the prompt.

33. Prompt Safety Against Unsupported Claims

Prompts should explicitly instruct the model:

Use only supplied evidence.
Do not invent facts.
Distinguish observations from hypotheses.
Do not claim a problem exists without evidence.
Do not fabricate personalization.
If evidence is insufficient, say so.

This is an important defense against hallucinated sales copy.

34. Prompt Versioning

Prompt behavior will evolve.

When prompt changes become important enough to affect reproducibility, record a prompt version.

Conceptually:

prompt_name
prompt_version
model
input_context
output

Do not implement a complete prompt management platform prematurely.

A simple version identifier is sufficient initially.

35. Model Selection

The intelligence layer should not hard-code a specific model everywhere.

Provider configuration may eventually determine:

provider = Ollama
model = chosen local model

The intelligence code should depend on the LLM provider protocol.

This allows model changes without rewriting the pipeline.

36. Cost and Performance

Local LLM inference is not financially expensive in the same way as a paid API, but it still has resource costs.

Consider:

CPU
RAM
GPU/VRAM
Inference time
Queue length
Context size

Do not run LLM processing on every discovered company.

Prefer:

Discovery
    ↓
Cheap qualification
    ↓
Signals
    ↓
High-value candidates
    ↓
LLM intelligence

This keeps the intelligence stage focused.

37. Intelligence Caching

If the exact same intelligence context is processed repeatedly, caching may eventually be useful.

Potential cache identity:

company
relevant observations
signals
product
prompt version
model

Do not implement intelligence caching before repeated processing becomes a measurable problem.

38. Intelligence Reprocessing

When evidence changes, intelligence may need to be regenerated.

Example:

Old observations
    ↓
Old intelligence


New observations
    ↓
New signals
    ↓
Re-run intelligence

Do not automatically regenerate intelligence every time any company field changes.

Only relevant changes should trigger reprocessing.

39. Intelligence Provenance

An intelligence result should eventually be traceable to:

company
product
observations
signals
prompt version
model
provider
generated_at

This makes it possible to understand why a particular draft was generated.

40. Intelligence and Historical Results

Do not automatically overwrite historical intelligence if historical reproducibility matters.

For example:

2026-08-01
Intelligence v1


2026-09-01
New observations
Intelligence v2

Whether both versions are retained should be decided when actual use cases require it.

Do not build a full version-history system prematurely.

41. Intelligence Quality Evaluation

Do not evaluate intelligence only by whether the text sounds good.

Evaluate:

Factual accuracy

Does the draft contain only supported facts?

Relevance

Does the pitch relate to the actual lead?

Specificity

Is it based on meaningful evidence?

Product fit

Does the offer match the product?

Usefulness

Would a salesperson actually use it?

Outcome

Does it improve replies or meetings?

42. Human Review

Early intelligence output should be reviewed by a human.

Review for:

Factual accuracy
Unsupported assumptions
Relevance
Tone
Product fit
Personalization
Potential compliance issues

Human feedback should eventually inform prompt and policy improvements.

43. Feedback Loop

Intelligence should improve based on outcomes.

Conceptually:

Lead evidence
    ↓
Intelligence
    ↓
Outreach
    ↓
Reply
    ↓
Positive / negative outcome
    ↓
Evaluation
    ↓
Better prompts / rules

Do not jump directly to machine learning.

Start by analyzing successful and unsuccessful outputs.

44. Intelligence Metrics

Track useful metrics such as:

intelligence jobs
successful generations
failed generations
validation failures
average generation time
manual rejection rate
manual edit rate
positive reply rate
meetings generated

Break down where useful by:

product
prompt version
model
provider
signal
lead score range
45. Testing
Unit Tests

Test:

Context construction
Evidence selection
Product routing
Prompt construction
Output validation
Deterministic intelligence rules
Provider Contract Tests

Verify the LLM provider conforms to the protocol.

Integration Tests

Test Ollama or another provider when appropriate.

End-to-End Tests

Use a fake LLM provider:

FakeLLMProvider
    ↓
deterministic response
    ↓
IntelligenceResult
    ↓
pipeline

This makes tests deterministic.

46. Fake LLM Provider

The application should be testable without running a real LLM.

Example:

class FakeLLMProvider:
    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        return LLMResponse(...)

This allows tests to verify intelligence orchestration independently of model availability.

47. Intelligence Pipeline Example

A WebArtsy intelligence flow:

Company
    ↓
Website observations
    ↓
Technology observations
    ↓
Signals
    ↓
WebArtsy score
    ↓
Qualified
    ↓
Relevant evidence selection
    ↓
WebArtsy knowledge
    ↓
LLM
    ↓
IntelligenceResult
    ↓
Human review
    ↓
Outreach
48. Autply Intelligence Example

An Autply intelligence flow:

Company
    ↓
Support observations
    ↓
Technology observations
    ↓
Competitor signals
    ↓
Autply score
    ↓
Qualified
    ↓
Relevant evidence selection
    ↓
Autply knowledge
    ↓
LLM
    ↓
IntelligenceResult
    ↓
Human review
    ↓
Outreach
49. What Intelligence Should Not Become

Do not turn the intelligence layer into:

A second scraper
A database layer
A provider registry
A scoring engine
A compliance engine
An outreach sender
A generic autonomous agent
A giant prompt framework

Its primary responsibility is:

Structured evidence
      ↓
Business interpretation
      ↓
Actionable intelligence
50. Future Agentic Capabilities

Autlead may eventually use agentic workflows for complex research.

For example:

Company
   ↓
Research task
   ↓
Search
   ↓
Website
   ↓
Reviews
   ↓
Job postings
   ↓
Evidence synthesis
   ↓
Intelligence

However, this should only be introduced when deterministic ETL plus structured intelligence is insufficient.

Do not make the entire pipeline an autonomous agent.

The default architecture should remain explicit and predictable.

51. Adding a New Intelligence Capability

Before adding a new intelligence feature:

Determine whether deterministic logic can solve it.
Identify the required evidence.
Identify the product.
Define the output.
Decide whether an LLM is actually required.
Define the Pydantic output schema if needed.
Add the provider capability if necessary.
Add tests.
Validate against real leads.
Measure outcomes.

Do not start by writing a prompt.

Start by defining the problem and evidence.

52. Golden Rule

The Intelligence layer should turn:

Facts
   ↓
Evidence
   ↓
Signals
   ↓
Context
   ↓
Reasoning
   ↓
Useful action

The LLM is a tool inside that process, not the intelligence system itself.

Autlead should always know:

What was observed.

What was inferred.

Why the inference was made.

Which product it applies to.

What action the intelligence recommends.

The system should become more useful as its evidence and outcome history improve, without becoming dependent on an opaque autonomous agent.