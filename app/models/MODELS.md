# Autlead — Data Models Guide

## 1. Purpose

This document defines how data models should be designed and evolved in Autlead.

Autlead is an ETL-driven lead intelligence system. Its models should represent:

- Real business entities
- Extracted source data
- Observations and evidence
- Derived signals
- Contacts and verification
- Lead qualification
- Pipeline execution
- Provider provenance

The model layer should remain **small, explicit, and evidence-driven**.

Do not create models speculatively.

A model should exist because the system has a real need to persist, validate, exchange, or reason about that concept.

---

# 2. Model Categories

Autlead has several different kinds of models.

They should not automatically be treated as the same thing.

```text
                    MODELS
                       │
       ┌───────────────┼────────────────┐
       │               │                │
    Domain         Persistence       Schemas
       │               │                │
   Business        PostgreSQL       Boundaries
   concepts        models           / DTOs


The primary categories are:

Domain models

Represent concepts the application reasons about.

Examples:

Company
Contact
Observation
Signal
Lead
Persistence models

Represent how those concepts are stored in PostgreSQL using SQLAlchemy.

Pydantic schemas

Represent data crossing boundaries.

Examples:

Provider input
Provider output
ETL records
Configuration
LLM output

Do not automatically create all three versions for every object.

Create separate representations when there is a real boundary or behavioral reason.

3. Source of Truth

PostgreSQL is Autlead's persistent source of truth.

Redis and Celery are execution infrastructure.

External providers are sources of information, not sources of truth for the internal data model.

External Provider
       ↓
Raw Provider Data
       ↓
Validation
       ↓
Normalization
       ↓
Autlead Model
       ↓
PostgreSQL
4. Core Model Philosophy

Models should answer:

What information does Autlead actually need to retain and reason about?

Avoid creating fields because:

A provider happens to expose them.
They might be useful someday.
Another CRM has them.
A theoretical future feature may need them.

Prefer:

minimum useful model
        ↓
real data
        ↓
real requirements
        ↓
model expansion

This is intentional.

Autlead should evolve its schema from actual pipeline requirements rather than speculative design.

5. Core Entities

The initial conceptual model includes:

Company
Source
SourceRecord
Observation
Signal
Contact
VerificationResult
LeadScore
PipelineRun
PipelineStep

Not all of these need to be implemented immediately.

The first implementation should begin with the entities required for the first vertical slice.

6. Company

Company is the central business entity.

It represents the normalized business that Autlead knows about.

Initial conceptual fields:

id
name
normalized_name
website
domain
country
city
phone
created_at
updated_at

Example:

Company
────────────────────────────
id: 123
name: Example Digital Ltd
normalized_name: example digital ltd
website: https://example.com
domain: example.com
country: Netherlands
city: Amsterdam
phone: +31...

Keep the initial Company model small.

Additional information should be represented by appropriate models rather than continuously expanding Company into a giant record.

For example:

Company
    │
    ├── Observations
    ├── Contacts
    ├── Sources
    ├── Signals
    └── Lead scores
7. Company Identity

Company identity and company observations are different concepts.

The Company model should contain relatively stable identity information.

Examples:

name
domain
website
location
phone

Dynamic or externally observed information should generally be represented separately.

For example:

Company
    +
Observation:
    WordPress detected

rather than:

Company.wordpress = true

This preserves provenance and allows observations to change over time.

8. Normalized Company Data

Provider data is rarely consistent.

Examples:

Example.com
www.example.com
https://example.com/
HTTP://WWW.EXAMPLE.COM

should generally normalize to:

example.com

Normalization should happen before persistence and deduplication.

Use deterministic normalization functions.

Examples:

normalize_company_name()
normalize_domain()
normalize_url()
normalize_phone()
normalize_country()

Do not use an LLM for deterministic normalization.

9. Source

A Source represents where information comes from.

Examples:

Google Maps
Business directory
Website
Search engine
Review platform
Job board

A source should allow Autlead to answer:

Where did this information originate?
Which source produced it?
Which provider accessed it?
When was it collected?

Source information is important for provenance and debugging.

10. SourceRecord

A SourceRecord represents the raw or provider-specific information collected from a source.

Conceptually:

Source
   ↓
SourceRecord
   ↓
Normalization
   ↓
Company

Example:

Source:
    Google Maps


SourceRecord:
    provider: google_maps_provider
    external_id: abc123
    raw_data: {...}
    collected_at: ...

Do not discard raw provider information immediately if it is useful for:

Debugging
Reprocessing
Provenance
Provider comparison
Data-quality analysis

Raw data should still be handled carefully when it contains personal information.

11. Raw Data vs Normalized Data

Keep the distinction clear.

Raw

What the provider actually returned.

provider output
Normalized

What Autlead understands after validation and normalization.

BusinessRecord
Company
ContactCandidate

Example:

Google Maps
     ↓
raw provider record
     ↓
BusinessRecord
     ↓
Company

Never allow provider-specific structures to leak throughout the application.

12. Observation

An Observation represents something Autlead discovered about an entity.

It is evidence, not necessarily a business conclusion.

Example:

Company: 123


Observation:
    type: technology_detected
    value: WordPress
    provider: technology-provider
    confidence: 0.95
    observed_at: ...

Other examples:

page_title
meta_description
technology_detected
chat_provider_detected
ssl_status
performance_score
website_status

Observations should preserve enough provenance to understand where they came from.

13. Observation vs Company Field

Use a Company field when the value is part of the company's core identity.

Use an Observation when the value is:

Discovered externally
Time-sensitive
Provider-dependent
Evidence for another conclusion
Potentially changing

Example:

Company.domain

is an identity attribute.

But:

WordPress detected
Intercom detected
PageSpeed score = 42

are observations.

This distinction prevents the Company model from becoming an unmanageable collection of every possible external signal.

14. Observation Provenance

An observation should be traceable.

Conceptually:

Observation
├── company/entity
├── type
├── value
├── source
├── provider
├── confidence
├── observed_at
└── evidence

The exact fields should be introduced as required by implementation.

Do not create a massive generic evidence schema before the first observation pipeline exists.

15. Signal

A Signal is a derived interpretation of one or more observations.

Conceptually:

Observation
      ↓
     Rule
      ↓
   Signal

Example:

Observation:
    mobile performance = 32


Rule:
    performance < 40


Signal:
    poor_mobile_performance

A signal should be explainable.

The system should be able to answer:

Why did this lead receive this signal?

16. Observation vs Signal

This distinction is fundamental.

Observation

Something was detected.

WordPress detected.
Signal

That observation has business relevance.

Potential website modernization opportunity.

Another example:

Observation:
    Zendesk detected.


Signal:
    Existing customer-support platform.

The observation is evidence.

The signal is interpretation.

17. Signal Evidence

Signals should preserve their supporting evidence.

Conceptually:

Signal
    ↓
Evidence
    ↓
Observation
    ↓
Source

Avoid opaque signals such as:

score = 87

without knowing why.

Prefer a system where the score can ultimately be explained through:

Signal A
Signal B
Signal C
Contact quality
ICP fit
18. Contact

A Contact represents a person associated with a company who may be relevant to a lead.

Initial information may include:

id
company_id
name
role
email
linkedin_url
created_at
updated_at

Only store information actually required by the pipeline.

Do not automatically store every piece of personal information exposed by a provider.

19. Contact Candidate

Before a contact is trusted as a usable lead contact, it may exist as a candidate.

Conceptually:

Provider
   ↓
ContactCandidate
   ↓
Validation
   ↓
Verification
   ↓
Contact

This prevents unverified enrichment results from being treated as authoritative.

20. Contact Discovery

Contact discovery can come from multiple providers.

Examples:

Website
Search
Directory
Open-source enrichment tool

All provider outputs should be normalized into a common Autlead representation.

The pipeline should not care whether a contact came from a particular search engine or enrichment repository.

21. VerificationResult

Email verification should be represented separately from the Contact itself.

A verification result answers:

What did the verification process determine at a particular time?

Conceptually:

Contact
   ↓
Verification
   ↓
VerificationResult

Possible information:

status
provider
confidence
checked_at
reason

Do not reduce verification to a permanent boolean such as:

email_verified = true

without considering that verification can become stale.

22. Lead Score

A LeadScore represents the result of evaluating a company/contact against a product's qualification strategy.

Conceptually:

Company
   ↓
Observations
   ↓
Signals
   ↓
Scoring strategy
   ↓
LeadScore

A score should ideally retain enough information to explain its result.

Example:

ICP fit: 30
Website opportunity: 25
Signal strength: 20
Contact quality: 15


Total: 90

The exact scoring model should remain product-specific.

23. Product-Specific Scoring

WebArtsy and Autply should not necessarily use the same scoring logic.

Example:

WebArtsy
    website opportunity
    SEO signals
    ecommerce signals
    technology signals

Autply:

Autply
    support complexity
    competitor detected
    support-channel signals
    customer-service growth

Shared infrastructure should support both strategies without forcing them into identical scoring rules.

24. Qualification

Qualification represents a business decision based on the available evidence.

Possible states:

qualified
parked
rejected
needs_review

Qualification should not be confused with raw score.

Example:

Score = 82
+
Verified decision maker
+
Relevant ICP
    ↓
Qualified

Qualification rules belong to product strategy/application logic, not providers.

25. PipelineRun

A PipelineRun represents an execution of an ETL pipeline.

It should eventually allow Autlead to answer:

Which pipeline ran?
For which product?
When?
What was its status?
What data did it process?
Did it succeed or fail?

Possible conceptual states:

pending
running
completed
failed
cancelled

Implement this when pipeline execution becomes sufficiently complex to require persisted state.

26. PipelineStep

A PipelineStep represents an individual stage within a pipeline run.

Example:

PipelineRun
    │
    ├── discovery
    ├── normalization
    ├── analysis
    ├── enrichment
    ├── verification
    └── scoring

A step can track:

status
started_at
completed_at
attempts
error

Do not create detailed pipeline-state models before asynchronous execution actually requires them.

27. Model Relationships

The conceptual relationship is:

                    Company
                       │
        ┌──────────────┼──────────────┐
        │              │              │
     Sources      Observations     Contacts
        │              │              │
   SourceRecord       │        Verification
                       │
                    Signals
                       │
                   LeadScore
                       │
                 Qualification

Pipeline execution exists around these entities:

PipelineRun
    ↓
PipelineStep
    ↓
ETL operations
    ↓
Company / observations / signals / contacts
28. Model Lifecycle

A typical company lifecycle is:

Provider record
      ↓
Raw source record
      ↓
Normalized company
      ↓
Website analysis
      ↓
Observations
      ↓
Signals
      ↓
Contact candidates
      ↓
Verified contacts
      ↓
Lead score
      ↓
Qualification

The model layer should support this lifecycle without coupling entities directly to a specific provider.

29. Pydantic Schemas

Pydantic schemas should be used at important boundaries.

Examples:

DiscoveryQuery
BusinessRecord
WebsiteAnalysis
ContactCandidate
VerificationResult
Signal
LeadScore
LLM output

Example:

class BusinessRecord(BaseModel):
    name: str
    website: str | None = None
    phone: str | None = None
    country: str | None = None

Provider-specific data should be converted into these schemas before entering the rest of Autlead.

30. Do Not Use Generic Dictionaries Everywhere

Avoid passing structures such as:

dict[str, Any]

through the entire application.

Use explicit models at important boundaries.

Bad:

result["company"]["website"]["data"]

Prefer:

business.website

This improves:

Type checking
Validation
IDE support
Refactoring
Documentation
Provider isolation

However, raw provider payloads may legitimately remain dictionaries when the external structure is intentionally preserved.

31. Database Models vs Pydantic Models

Do not automatically make a Pydantic model and SQLAlchemy model for every concept.

Use SQLAlchemy when persistence is required.

Use Pydantic when validation or a boundary requires it.

Example:

External Provider
       ↓
Pydantic BusinessRecord
       ↓
Normalization
       ↓
SQLAlchemy Company
       ↓
PostgreSQL

This is a useful boundary because provider output and persistent database representation have different responsibilities.

32. Database Constraints

Use PostgreSQL constraints where they protect real invariants.

Examples may include:

Required fields
Foreign keys
Unique normalized domains
Valid relationships
Appropriate indexes

Do not rely exclusively on application-level checks for database invariants.

However, do not add speculative constraints before understanding the actual data.

33. Indexing

Indexes should be based on actual query patterns.

Likely candidates may eventually include:

domain
normalized_name
company_id
source_id
pipeline status
created_at

Do not index every column.

An index is a performance optimization with a maintenance cost.

Add it when the access pattern justifies it.

34. Timestamps

Persistent entities that require lifecycle tracking should generally have timestamps such as:

created_at
updated_at

Observation-like entities should also preserve when the information was observed.

Distinguish:

created_at

from:

observed_at

They answer different questions.

35. Historical Data

Autlead is an intelligence system, so some information changes over time.

Do not blindly overwrite every observation.

For example:

2026-08-01
Zendesk detected


2026-09-01
Zendesk not detected

may both be useful.

Whether historical observations should be retained, superseded, or periodically cleaned should be decided based on actual requirements.

Do not build a full temporal database model prematurely.

36. Provenance

Important data should be traceable to:

source
provider
observation time
processing step

When possible, the system should be able to answer:

Why does Autlead believe this?

For example:

Lead Signal
    ↓
Supporting Observation
    ↓
Website
    ↓
Crawler Provider
    ↓
Observed at timestamp

This is important for debugging, scoring, and future intelligence.

37. Model Evolution

When a model needs a new field:

Confirm the feature actually requires it.
Check whether an existing model already represents the information.
Add the smallest useful change.
Update the SQLAlchemy model.
Create an Alembic migration.
Update Pydantic schemas if required.
Update tests.
Check existing ETL/provider behavior.

Do not redesign the entire schema for one new field.

38. Avoid Model Bloat

Do not turn Company into:

Company
├── 100 provider fields
├── SEO fields
├── support fields
├── marketing fields
├── contact fields
├── scoring fields
├── LLM fields
└── outreach fields

Instead, keep concerns separated:

Company
Observations
Signals
Contacts
Scores
Pipeline state
Outreach

This keeps the model understandable as Autlead grows.

39. First Models to Implement

Do not implement every model in this document immediately.

The first vertical slice should require only the minimum necessary models.

Recommended starting order:

1. Company
2. Source
3. SourceRecord
4. BusinessRecord Pydantic schema
5. DiscoveryQuery Pydantic schema

Then, as the pipeline grows:

6. Observation
7. Signal
8. Contact
9. VerificationResult
10. LeadScore
11. PipelineRun
12. PipelineStep

This follows Autlead's incremental architecture principle.

40. First Vertical Slice

The first complete model flow should be:

Open-source Discovery Provider
          ↓
BusinessRecord
          ↓
Normalization
          ↓
Company
          ↓
Source / SourceRecord
          ↓
PostgreSQL

Once this works against real data, expand the model layer.

Do not implement the entire future data model before the first ETL path is operational.

41. Model Design Rules

When adding a model, ask:

What real concept does this represent?
Does it need persistence?
Who owns its lifecycle?
What data is actually required?
Is this raw data, normalized data, evidence, or a conclusion?
Does provenance matter?
Is this product-specific?
Could an existing model represent it?
Does it need a separate Pydantic schema?
Does the database need a new migration?

If these questions cannot be answered clearly, the model may be premature.

42. Golden Rule

Autlead models should make the system easier to understand, not more impressive.

Prefer:

small models
clear relationships
explicit schemas
strong provenance
real constraints
incremental evolution

Avoid:

speculative fields
giant entities
generic abstractions
provider-specific database columns
duplicated schemas
premature historical models

The model layer should grow with the ETL system, not ahead of it.



This follows the existing Autlead execution plan and its principle of incremental model creation rather than designing the entire future schema upfront. :contentReference[oaicite:0]{index=0}