# Autlead — Transform Guide

## 1. Purpose

The Transform layer is where raw extracted information becomes useful, consistent, application-level data.

The basic ETL flow is:

    EXTRACT
       ↓
    TRANSFORM
       ↓
    LOAD

Extraction asks:

> What did the external source give us?

Transformation asks:

> What does this information mean and how should Autlead represent it?

Loading asks:

> Where should the resulting data be persisted?


# 2. Current Structure

The current Transform layer is:

    app/
    └── transform/
        ├── analysis/
        ├── deduplication/
        ├── enrichment/
        ├── entity_resolution/
        ├── normalization/
        ├── qualification/
        ├── scoring/
        └── signal_extraction/


These are different transformation responsibilities.

They should remain independent rather than becoming one large transformation module.


# 3. Transform Philosophy

Transformations should be:

- Explicit
- Testable
- Deterministic where possible
- Evidence-based
- Composable
- Independent from external providers
- Independent from database infrastructure

The preferred flow is:

    External provider
          ↓
    Provider schema
          ↓
    Transform
          ↓
    Autlead model
          ↓
    Load


# 4. Transform Does Not Extract

The Transform layer should not call external providers to obtain missing information.

Bad:

    normalization
        ↓
    call Google Maps
        ↓
    fetch missing address


Correct:

    provider
        ↓
    extracted data
        ↓
    normalization


If more information is required, the pipeline should execute another extraction/enrichment stage.


# 5. Transform Does Not Load

Transformation should not directly write to PostgreSQL.

Bad:

    normalization
        ↓
    SQLAlchemy
        ↓
    PostgreSQL


Correct:

    normalization
        ↓
    transformed model
        ↓
    load
        ↓
    PostgreSQL


This keeps transformations easy to test.


# 6. Transform Does Not Mean "One Transformation"

The Transform layer contains several different kinds of processing.

Current categories:

    normalization
    deduplication
    entity resolution
    analysis
    signal extraction
    enrichment
    scoring
    qualification


They should not all be treated as the same type of operation.


# 7. Normalization

Normalization converts inconsistent external data into a consistent representation.

Examples:

    "HTTPS://WWW.Example.com/"
             ↓
        example.com


    "Example Business Ltd."
             ↓
        normalized company name


    "+31 (0)20..."
             ↓
        normalized phone representation


Normalization should be predictable and repeatable.


# 8. Normalization Rules

Normalization may include:

- URL normalization
- Domain normalization
- Company-name normalization
- Phone normalization
- Country normalization
- Address normalization
- Text cleanup

Do not aggressively alter information if doing so can destroy useful source data.

Prefer keeping:

    raw value

and deriving:

    normalized value

when the distinction matters.


# 9. Normalization Should Be Deterministic

Given the same input, normalization should normally produce the same result.

Example:

    normalize_domain(
        "HTTPS://WWW.Example.com/"
    )

should consistently produce:

    example.com


Avoid LLMs for basic normalization tasks.


# 10. Deduplication

Deduplication determines whether multiple extracted records represent the same underlying entity.

Example:

    Google Maps
        ↓
    Example Business

    Directory
        ↓
    Example Business Ltd.

    Website
        ↓
    example.com


These may all represent one company.


# 11. Deduplication vs Entity Resolution

These concepts are related but different.

### Deduplication

Usually answers:

> Is this record already present?

Example:

    same external ID
    same normalized domain


### Entity Resolution

Answers:

> Do these different records actually represent the same real-world entity?


Entity resolution can involve more evidence and reasoning.


# 12. Deduplication

Start with deterministic identifiers.

Possible identifiers:

1. Source + external ID
2. Normalized domain
3. Phone
4. Other stable identifiers


Do not begin with complex fuzzy matching.


# 13. Entity Resolution

`entity_resolution/` is for cases where deterministic matching is insufficient.

Possible evidence:

- Company name
- Domain
- Address
- Phone
- Location
- Website
- Other source identifiers


Example:

    "ABC Dental Amsterdam"

and:

    "ABC Dental Clinic"


may require additional evidence before deciding they represent the same entity.


# 14. Entity Resolution Confidence

Entity resolution may eventually produce:

    same_entity
    different_entity
    uncertain


Do not force uncertain matches into a definitive result.

An incorrect merge can be more damaging than a duplicate.


# 15. Analysis

`analysis/` interprets extracted data into structured observations.

Example:

    Website HTML
        ↓
    Analysis
        ↓
    missing_meta_description = true


Another example:

    Technology extraction
        ↓
    Analysis
        ↓
    ecommerce_stack_detected


Analysis should produce evidence or structured observations.


# 16. Analysis vs Signal Extraction

Analysis:

> What does the extracted data tell us?

Signal extraction:

> Which observations represent a meaningful business signal?

Example:

    Analysis:
        mobile performance = 31


    Signal extraction:
        poor_mobile_performance


Keep these separate.


# 17. Signal Extraction

`signal_extraction/` converts observations into business-relevant signals.

Example:

    Observation:
        mobile performance = 31

        ↓

    Signal:
        poor_mobile_performance


Another example:

    Observation:
        Zendesk detected

        ↓

    Signal:
        existing_support_platform


Signals should be explainable.


# 18. Signals Must Have Evidence

A signal should be traceable to observations.

Bad:

    signal = "needs_new_website"


with no evidence.


Better:

    Signal:
        website_modernization_opportunity

    Evidence:
        outdated technology
        poor mobile performance
        missing metadata


The signal can still represent an interpretation, but its supporting evidence should be known.


# 19. Enrichment

`enrichment/` adds useful information derived from existing records or additional enrichment operations.

Examples:

- Company information
- Contact information
- Decision-maker information
- Domain information
- Additional business metadata


Important distinction:

Extraction obtains information from a provider.

Enrichment is the process of improving an existing entity with additional information.


# 20. Enrichment May Use Providers

Enrichment may require external providers.

For example:

    Company
       ↓
    enrichment stage
       ↓
    Contact Provider
       ↓
    ContactCandidate


The provider remains in `providers/`.

The enrichment transformation decides how the returned information should become part of the Autlead entity.


# 21. Enrichment Should Be Progressive

Do not enrich every discovered company with every available source.

Prefer:

    Discovery
       ↓
    Cheap filtering
       ↓
    Website analysis
       ↓
    Qualification potential
       ↓
    Contact enrichment
       ↓
    Verification


This reduces unnecessary external calls.


# 22. Scoring

`scoring/` converts relevant evidence into a lead priority score.

Example:

    ICP fit
       +
    relevant signals
       +
    business characteristics
       +
    contact quality
       ↓
    LeadScore


Scoring is product-specific.


# 23. Scoring Is Not Qualification

A score answers:

> How strong does this lead appear to be?

Qualification answers:

> Should this lead proceed to the next stage?


Example:

    Score = 87
        ↓
    Qualification policy
        ↓
    qualified


Another:

    Score = 42
        ↓
    Qualification
        ↓
    parked


Do not collapse these concepts.


# 24. Scoring Must Be Explainable

A score should ideally be explainable.

For example:

    WebArtsy score = 82

    Factors:
        strong ICP match
        poor website performance
        ecommerce detected
        decision maker found


This is much more useful than:

    score = 82


# 25. Product-Specific Scoring

The same company can have different scores for different products.

Example:

    Company
       ├── WebArtsy score
       └── Autply score


WebArtsy may care about:

- Website quality
- SEO
- Ecommerce
- Technology modernization


Autply may care about:

- Support channels
- Existing support platform
- Competitor presence
- Support complexity


Do not create one universal score that tries to serve every product.


# 26. Qualification

`qualification/` determines whether a lead is suitable for the next stage.

Possible outcomes:

    qualified
    needs_review
    parked
    rejected


Qualification should use explicit policies.


# 27. Qualification Is Not Intelligence

Qualification:

> Is this lead worth continuing with?

Intelligence:

> Why is this lead relevant and what should we say/do?


Example:

    Score = 85
        ↓
    Qualified
        ↓
    Intelligence
        ↓
    "The strongest opportunity appears to be..."


Keep the boundaries clear.


# 28. Transformation Order

A typical WebArtsy flow may be:

    Extract
       ↓
    Normalize
       ↓
    Deduplicate
       ↓
    Entity Resolution
       ↓
    Analysis
       ↓
    Signal Extraction
       ↓
    Enrichment
       ↓
    Scoring
       ↓
    Qualification
       ↓
    Load


Not every pipeline must execute every stage.


# 29. Autply Transformation Flow

A typical Autply flow may be:

    Extract
       ↓
    Normalize
       ↓
    Deduplicate
       ↓
    Entity Resolution
       ↓
    Website/Support Analysis
       ↓
    Signal Extraction
       ↓
    Enrichment
       ↓
    Scoring
       ↓
    Qualification
       ↓
    Load


The product-specific differences should live in the appropriate transformation policies and rules.


# 30. Transformation Inputs

Transformations should accept explicit models.

For example:

    BusinessRecord
    WebsiteContent
    TechnologyObservation
    ContactCandidate


Avoid passing arbitrary dictionaries between transformation stages.


# 31. Transformation Outputs

Transformation outputs should also be explicit.

Examples:

    NormalizedBusiness
    CompanyMatch
    Observation
    Signal
    EnrichedCompany
    LeadScore
    QualificationResult


Pydantic models should be used at meaningful boundaries.


# 32. Transformation Composition

Transformations can be composed.

Example:

    BusinessRecord
        ↓
    normalize_business()
        ↓
    NormalizedBusiness
        ↓
    deduplicate()
        ↓
    CompanyMatch
        ↓
    resolve_entity()
        ↓
    Company


Keep each transformation focused.


# 33. Pure Transformations

Prefer pure functions for transformations that do not require external state.

Example:

```python
def normalize_domain(value: str) -> str:
    ...