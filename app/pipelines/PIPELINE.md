# Autlead — Pipeline Guide

## 1. Purpose

This document defines how Autlead pipelines are designed, implemented, executed, and evolved.

Autlead is an ETL-driven lead intelligence system.

A pipeline coordinates capabilities such as:

- Business discovery
- Website analysis
- Technology detection
- Contact discovery
- Email verification
- Signal generation
- Scoring
- Qualification
- Intelligence
- Outreach

The pipeline determines **what happens and in what order**.

It does not own the implementation of external capabilities.

---

# 2. Pipeline Philosophy

Autlead pipelines should be:

- Modular
- Explicit
- Resumable
- Observable
- Testable
- Idempotent where practical
- Provider-independent
- Product-aware where necessary
- Incremental

The pipeline should compose existing capabilities rather than reimplement them.

Conceptually:

    Provider
        ↓
    Capability
        ↓
    Pipeline stage
        ↓
    Normalized data
        ↓
    Next stage

---

# 3. ETL as the Primary Pipeline Model

The fundamental Autlead pipeline is:

    EXTRACT
       ↓
    TRANSFORM
       ↓
    LOAD

In practice, lead generation expands this into:

    DISCOVER
       ↓
    NORMALIZE
       ↓
    DEDUPLICATE
       ↓
    ANALYZE
       ↓
    OBSERVE
       ↓
    SIGNAL
       ↓
    ENRICH
       ↓
    VERIFY
       ↓
    SCORE
       ↓
    QUALIFY
       ↓
    INTELLIGENCE
       ↓
    OUTREACH

Not every pipeline must execute every stage.

A product pipeline should use only the stages required for its purpose.

---

# 4. Pipeline vs Provider

The pipeline should not know how a provider performs its work.

Bad:

    Pipeline
        ↓
    Google Maps scraper internals
        ↓
    Parse HTML
        ↓
    Extract cards

Correct:

    Pipeline
        ↓
    BusinessDiscoveryProvider
        ↓
    Google Maps adapter
        ↓
    External open-source project

The pipeline requests a capability.

The provider supplies the implementation.

---

# 5. Pipeline vs Policy

Pipelines determine:

> What happens and in what sequence?

Policies determine:

> Whether an action should happen?

Example:

    Pipeline
        ↓
    analyze company
        ↓
    enrichment policy
        ↓
    should enrich?
       ├── yes → enrich
       └── no  → continue/park

Do not put every business decision directly into pipeline orchestration code.

---

# 6. Pipeline vs Worker

A pipeline is application/business orchestration.

A Celery worker is execution infrastructure.

Preferred:

    Pipeline operation
         ↓
    Celery task
         ↓
    Application capability
         ↓
    Provider

Do not make a Celery task the pipeline itself.

Workers should execute pipeline work rather than define the entire business workflow.

---

# 7. Shared vs Product Pipelines

Autlead supports multiple products.

Current products:

- WebArtsy
- Autply

They share infrastructure but have different qualification strategies.

Shared:

- Company model
- Source model
- Normalization
- Deduplication
- Website analysis
- Contact enrichment
- Verification
- Pipeline execution
- Persistence
- Worker infrastructure

Product-specific:

- ICP
- Signals
- Scoring
- Qualification
- Intelligence prompts
- Messaging
- Outreach strategy

Conceptually:

    Shared ETL capabilities
             │
       ┌─────┴─────┐
       │           │
    WebArtsy     Autply
    strategy    strategy

---

# 8. First Pipeline

The first pipeline should be intentionally small.

    Business Discovery Provider
              ↓
       BusinessRecord
              ↓
        Normalization
              ↓
        Deduplication
              ↓
           Company
              ↓
         PostgreSQL

This is the first vertical slice.

Do not add:

- Celery
- Redis
- LLM
- Email
- Scoring
- Outreach

until the basic ETL path works correctly.

The purpose is to validate:

- Provider integration
- Pydantic schemas
- Normalization
- Deduplication
- SQLAlchemy
- PostgreSQL
- Error handling
- Testing

---

# 9. Pipeline Stages

## 9.1 Discovery

Purpose:

Find candidate businesses or companies.

Input:

    DiscoveryQuery

Output:

    BusinessRecord[]

Possible providers:

- Google Maps/business discovery
- Directories
- Search
- Public datasets
- Product-specific sources

Discovery should not perform product-specific scoring.

---

## 9.2 Normalization

Purpose:

Convert inconsistent source data into a consistent Autlead representation.

Examples:

    HTTP://WWW.EXAMPLE.COM/
             ↓
         example.com

Normalize:

- Company names
- URLs
- Domains
- Phone numbers
- Country
- Addresses where practical

Normalization should be deterministic.

---

## 9.3 Deduplication

Purpose:

Prevent repeated source records from creating duplicate companies.

Start with deterministic matching.

Possible identity signals:

1. Source external identifier
2. Normalized domain
3. Phone
4. Business name
5. Address

Do not introduce AI entity resolution unless real data demonstrates the need.

---

## 9.4 Website Discovery

Purpose:

Determine whether a useful website exists and identify the canonical website.

Possible outcomes:

    website found
    website not found
    website unreachable
    website ambiguous

Do not assume a website exists simply because a source contains a URL.

---

## 9.5 Website Analysis

Purpose:

Extract useful website information.

Potential outputs:

- HTTP status
- Title
- Meta description
- HTML
- Website content
- SSL status
- Redirects
- Performance information

The crawler is provided by an external provider.

Autlead consumes normalized results.

---

## 9.6 Technology Detection

Purpose:

Determine technologies relevant to the pipeline.

Examples:

- WordPress
- Shopify
- WooCommerce
- Intercom
- Zendesk
- Gorgias
- Other support technologies

Technology detection produces observations.

Example:

    technology_detected
        value: WordPress
        provider: technology-provider

It should not directly produce a lead score.

---

## 9.7 Observations

Purpose:

Persist factual discoveries.

Example:

    Company
       ↓
    Website analysis
       ↓
    Observation:
        performance_score = 32

Observations should retain provenance when practical.

---

## 9.8 Signals

Purpose:

Transform observations into meaningful business signals.

Example:

    performance_score = 32
             ↓
    Signal:
        poor_mobile_performance

Another example:

    Zendesk detected
             ↓
    Signal:
        existing_support_platform

Signals should be explainable.

---

## 9.9 Enrichment

Purpose:

Collect additional information about promising companies.

Possible enrichment:

- Decision maker
- Role
- Business email
- LinkedIn URL
- Company information
- Support information

Enrichment should generally happen progressively.

Do not perform expensive enrichment on every raw discovery result.

---

## 9.10 Verification

Purpose:

Determine whether contact information is sufficiently trustworthy for the intended use.

Example:

    Contact
       ↓
    Email verification provider
       ↓
    VerificationResult

Verification results should include provenance and timestamp.

Verification is not permanent.

---

## 9.11 Scoring

Purpose:

Prioritize leads.

Example:

    ICP fit
       +
    Relevant signals
       +
    Contact quality
       +
    Business opportunity
       ↓
    LeadScore

Scoring is product-specific.

---

## 9.12 Qualification

Purpose:

Determine whether a lead is suitable for the next stage.

Possible states:

    qualified
    needs_review
    parked
    rejected

Qualification is not identical to scoring.

A high score does not automatically mean a lead can be contacted.

---

## 9.13 Intelligence

Purpose:

Turn structured evidence into useful business interpretation.

Input:

- Company
- Observations
- Signals
- Score
- Product knowledge

Output may include:

- Summary
- Pain hypothesis
- Strongest signal
- Pitch angle
- Personalization
- Draft

LLMs should interpret evidence rather than invent factual observations.

---

## 9.14 Outreach

Purpose:

Deliver approved communication.

Early pipeline:

    Qualified Lead
          ↓
    Intelligence
          ↓
    Draft
          ↓
    Human Review
          ↓
    Approval
          ↓
    Send

Do not begin with fully autonomous outreach.

---

# 10. WebArtsy Pipeline

Initial WebArtsy pipeline:

    Business Discovery
          ↓
    Normalization
          ↓
    Deduplication
          ↓
    Website Discovery
          ↓
    Website Analysis
          ↓
    Technology Detection
          ↓
    Web/SEO Signals
          ↓
    Contact Discovery
          ↓
    Email Verification
          ↓
    WebArtsy Scoring
          ↓
    Qualification
          ↓
    Intelligence
          ↓
    Outreach

Potential signals:

- No website
- Poor website
- Poor mobile performance
- Missing metadata
- Outdated technology
- Ecommerce opportunity
- Weak conversion structure

These are initial hypotheses and should be validated against real outcomes.

---

# 11. Autply Pipeline

Initial Autply pipeline:

    Company Discovery
          ↓
    Normalization
          ↓
    Deduplication
          ↓
    Website Analysis
          ↓
    Technology Detection
          ↓
    Support Signals
          ↓
    Competitor Signals
          ↓
    Contact Discovery
          ↓
    Email Verification
          ↓
    Autply Scoring
          ↓
    Qualification
          ↓
    Intelligence
          ↓
    Outreach

Potential signals:

- Support platform detected
- Competitor detected
- Multiple support channels
- Live chat
- Support hiring
- Customer-service growth
- Support-related complaints

---

# 12. Stage Contracts

Each significant stage should have a clear input and output.

Example:

    DiscoveryQuery
        ↓
    BusinessDiscoveryProvider
        ↓
    BusinessRecord[]

Then:

    BusinessRecord
        ↓
    Normalizer
        ↓
    NormalizedBusiness

Then:

    NormalizedBusiness
        ↓
    Persistence
        ↓
    Company

The exact model names can evolve.

The important principle is that stage boundaries are explicit.

---

# 13. Pydantic at Stage Boundaries

Use Pydantic schemas when data crosses meaningful boundaries.

Examples:

    DiscoveryQuery
    BusinessRecord
    WebsiteAnalysis
    ContactCandidate
    VerificationResult
    Signal
    LeadScore
    IntelligenceResult

This prevents provider-specific dictionaries from flowing through the entire application.

---

# 14. Stage Idempotency

Where practical, stages should be safe to repeat.

Example:

    Discovery
       ↓
    Company normalization
       ↓
    Existing company
       ↓
    update/reuse

A retry should not produce uncontrolled duplicates.

Database constraints should help enforce important invariants.

---

# 15. Pipeline Checkpoints

Long-running pipelines should eventually have checkpoints.

Example:

    DISCOVERED
        ↓
    ANALYZED
        ↓
    ENRICHED
        ↓
    VERIFIED
        ↓
    SCORED
        ↓
    QUALIFIED

If a worker fails during verification, Autlead should not need to repeat discovery and analysis unnecessarily.

Persisted state should allow the pipeline to resume.

---

# 16. Pipeline Run

A `PipelineRun` represents one execution of a pipeline.

Conceptually:

    PipelineRun
        ├── pipeline name
        ├── product
        ├── status
        ├── started_at
        ├── completed_at
        └── steps

Possible statuses:

    pending
    running
    completed
    failed
    cancelled

Do not implement all pipeline execution state infrastructure before asynchronous processing requires it.

---

# 17. Pipeline Steps

A pipeline run may contain multiple steps.

Example:

    PipelineRun
        │
        ├── discovery
        ├── normalization
        ├── analysis
        ├── enrichment
        ├── verification
        └── scoring

A step may eventually track:

- Status
- Attempts
- Start time
- Completion time
- Error
- Provider
- Result metadata

Only persist information that is useful for recovery, debugging, or observability.

---

# 18. Celery Integration

Celery should execute work that is:

- Slow
- Network-bound
- Retryable
- Resource-intensive
- Independent enough to process asynchronously

Examples:

- Website crawling
- Technology detection
- Contact discovery
- Email verification
- LLM processing

Preferred structure:

    Pipeline
       ↓
    Task
       ↓
    Application operation
       ↓
    Provider

Do not put the complete pipeline inside one giant Celery task.

---

# 19. Task Granularity

Avoid both extremes.

Bad:

    One task for the entire pipeline

Also bad:

    One Celery task for every tiny function

Prefer tasks around meaningful units of work.

Example:

    analyze_company
    enrich_contact
    verify_email
    generate_intelligence

The exact task boundaries should emerge from real workload characteristics.

---

# 20. Celery Queues

Queues can eventually be separated by workload.

Possible queues:

    discovery
    analysis
    enrichment
    verification
    intelligence
    outreach

Do not create all queues before they are needed.

Start with a simple configuration and split workloads when operational requirements justify it.

---

# 21. Redis

Redis supports Celery execution.

Do not store authoritative lead state only in Redis.

The durable state belongs in PostgreSQL.

Example:

    PostgreSQL
        ↓
    authoritative lead/pipeline state

    Redis
        ↓
    task broker / execution coordination

---

# 22. Retry Behavior

Pipeline stages should distinguish retryable and permanent failures.

Example:

    timeout
        ↓
    retry

    HTTP 429
        ↓
    retry with backoff

    invalid URL
        ↓
    permanent failure

    invalid input
        ↓
    permanent failure

Retry limits must exist.

Do not retry indefinitely.

---

# 23. Failure Isolation

A failure for one company should not unnecessarily terminate the entire discovery or enrichment batch.

Prefer:

    Company A → success
    Company B → failure
    Company C → success

rather than:

    Company B → failure
                  ↓
             entire pipeline fails

Batch-level failure behavior should be explicit.

---

# 24. Partial Success

Pipelines should support partial completion.

Example:

    Company
       ↓
    Website analysis ✓
       ↓
    Technology detection ✓
       ↓
    Contact discovery ✗
       ↓
    Company remains stored
       ↓
    Contact stage can retry later

Do not discard useful work because a later stage failed.

---

# 25. Provider Failover

When multiple providers exist for the same capability, failover may eventually be introduced.

Example:

    Google Maps Provider A
             ↓
          failure
             ↓
    Google Maps Provider B

However, do not implement automatic provider routing before there are multiple real providers and a demonstrated need.

Initially, use explicit provider selection.

---

# 26. Provider Independence

A pipeline should not contain provider-specific branching like:

    if provider == "google_maps":
        ...
    elif provider == "directory":
        ...

unless the difference is genuinely part of the capability contract.

Provider-specific behavior belongs in the provider adapter.

---

# 27. Pipeline Policies

Policies may determine whether a stage should execute.

Examples:

    Should this company be analyzed?

    Should this company be enriched?

    Should this contact be verified?

    Should this lead be qualified?

    Can this lead be sent?

Pipeline orchestration calls the policy.

The policy makes the decision.

---

# 28. Progressive Enrichment

Use cheap operations before expensive operations where practical.

Example:

    Discovery
        ↓
    Basic ICP filtering
        ↓
    Website analysis
        ↓
    Stronger qualification
        ↓
    Contact enrichment
        ↓
    Verification
        ↓
    Intelligence

This reduces unnecessary provider calls.

---

# 29. Pipeline Cost Awareness

Even when providers are open-source or self-hosted, operations have costs:

- CPU
- RAM
- bandwidth
- proxy usage
- provider rate limits
- execution time
- storage
- LLM inference time

Pipeline design should avoid expensive processing for obviously irrelevant records.

Do not optimize prematurely, but measure expensive stages.

---

# 30. Pipeline Observability

Important pipeline operations should be observable.

Useful information:

    pipeline_run_id
    company_id
    stage
    provider
    task_id
    attempt
    duration
    result
    error

Structured logs should make it possible to trace a company through the pipeline.

---

# 31. Pipeline Logging

Prefer structured logging.

Example conceptual event:

    stage=website_analysis
    company_id=123
    provider=crawl4ai
    status=success
    duration=4.8s

Avoid excessive debug logging of complete provider payloads, especially when they contain personal information.

---

# 32. Pipeline Data Provenance

Whenever possible, preserve:

    source
    provider
    observed_at
    pipeline_stage

This allows later analysis such as:

    Which provider discovered this company?

    Which provider detected this technology?

    When was this observation made?

    Which pipeline produced this score?

---

# 33. Reprocessing

Autlead should eventually support reprocessing selected stages.

Example:

    Existing Company
          ↓
    New technology provider
          ↓
    Re-run technology detection
          ↓
    New observations
          ↓
    Recalculate signals

Do not require rediscovery of the company simply to rerun analysis.

---

# 34. Pipeline Versioning

Pipeline behavior may change over time.

If reproducibility becomes important, record relevant versions such as:

    pipeline version
    scoring policy version
    signal-rule version
    provider version/configuration

Do not build a complete pipeline-versioning framework prematurely.

Introduce it when historical reproducibility becomes a real requirement.

---

# 35. Pipeline Testing

## Unit tests

Test individual transformations and policies.

Examples:

    normalization
    deduplication
    signal rules
    scoring
    qualification

## Provider contract tests

Verify provider behavior against the expected protocol.

## Integration tests

Test:

    PostgreSQL
    SQLAlchemy
    Celery
    Redis

## Pipeline tests

Test multiple stages together.

## End-to-end tests

Use fake providers:

    FakeDiscovery
    FakeCrawler
    FakeTechnologyDetector
    FakeVerifier
    FakeLLM

This makes complete pipeline tests deterministic.

---

# 36. Fake Providers

Fake providers are useful for pipeline tests.

Example:

    FakeBusinessDiscoveryProvider
            ↓
    predetermined BusinessRecord
            ↓
    pipeline
            ↓
    expected Company

This allows testing pipeline logic without:

- Google Maps
- Search engines
- Websites
- Email providers
- Ollama

The pipeline should be testable without external services.

---

# 37. First Real Pipeline Milestone

The first production-like milestone is:

    Discovery provider
          ↓
    BusinessRecord
          ↓
    Validation
          ↓
    Normalization
          ↓
    Deduplication
          ↓
    Company
          ↓
    PostgreSQL

Success criteria:

- Real provider works.
- Output is validated.
- Data is normalized.
- Duplicate companies are controlled.
- Database persistence works.
- Errors are handled.
- Tests exist.

Only after this should the next ETL stage be introduced.

---

# 38. Second Milestone

Add website analysis:

    Company
       ↓
    Website Provider
       ↓
    WebsiteAnalysis
       ↓
    Observations
       ↓
    PostgreSQL

The objective is to establish the observation model.

---

# 39. Third Milestone

Add signals:

    Observations
        ↓
    Signal rules
        ↓
    Signals
        ↓
    WebArtsy score

The objective is to establish the intelligence foundation.

---

# 40. Fourth Milestone

Add contacts:

    Qualified candidate
        ↓
    Contact provider
        ↓
    ContactCandidate
        ↓
    Verification
        ↓
    Verified contact

The objective is to establish enrichment.

---

# 41. Fifth Milestone

Add asynchronous execution:

    Pipeline operation
          ↓
    Celery
          ↓
    Worker
          ↓
    Provider
          ↓
    PostgreSQL

Only introduce this once real workloads justify asynchronous execution.

---

# 42. Complete WebArtsy Pipeline

The first complete product pipeline should be:

    Discovery
        ↓
    Normalization
        ↓
    Deduplication
        ↓
    Website Analysis
        ↓
    Technology Detection
        ↓
    Signals
        ↓
    Contact Discovery
        ↓
    Verification
        ↓
    Scoring
        ↓
    Qualification
        ↓
    Intelligence
        ↓
    Human Review
        ↓
    Outreach

Run this against real data.

Measure quality before building large amounts of additional infrastructure.

---

# 43. Autply Pipeline

Once the shared pipeline infrastructure is proven:

    Discovery
        ↓
    Normalization
        ↓
    Deduplication
        ↓
    Website Analysis
        ↓
    Technology Detection
        ↓
    Support Signals
        ↓
    Competitor Signals
        ↓
    Contact Discovery
        ↓
    Verification
        ↓
    Autply Scoring
        ↓
    Qualification
        ↓
    Intelligence
        ↓
    Human Review
        ↓
    Outreach

Reuse the shared stages.

Only the product-specific strategy should differ.

---

# 44. Outreach Pipeline

Outreach should be treated as a separate high-impact stage.

Preferred early flow:

    Qualified Lead
          ↓
    Intelligence
          ↓
    Draft
          ↓
    Human Review
          ↓
    Approval
          ↓
    Suppression Check
          ↓
    Send
          ↓
    Track
          ↓
    Outcome

Do not bypass suppression because a lead was previously qualified.

The send decision must be evaluated at send time.

---

# 45. Pipeline Metrics

Track meaningful pipeline metrics.

At minimum:

    discovered
    normalized
    deduplicated
    analyzed
    enriched
    verified
    scored
    qualified
    drafts generated
    approved
    sent
    replied
    positive replies
    meetings

Break down by:

    product
    country
    source
    provider
    signal
    score range

This allows Autlead to determine which parts of the pipeline actually create value.

---

# 46. Feedback Loop

The pipeline should eventually learn from outcomes.

Conceptually:

    Sources
        ↓
    Signals
        ↓
    Scores
        ↓
    Outreach
        ↓
    Replies
        ↓
    Meetings
        ↓
    Customers
        ↓
    Feedback
        ↓
    Improved policies/signals/scoring

Do not introduce machine learning automatically.

Start by analyzing outcomes and adjusting deterministic rules.

---

# 47. What Not to Build

Do not prematurely implement:

- Generic workflow engine
- Generic DAG framework
- Complex event bus
- Kafka
- Airflow
- Temporal
- Kubernetes
- Microservices
- Automatic provider marketplace
- AI pipeline planner
- ML pipeline optimizer

Celery plus explicit Python orchestration is sufficient for the initial system.

Introduce heavier workflow infrastructure only when actual pipeline complexity requires it.

---

# 48. Adding a New Pipeline Stage

Before adding a stage:

1. Identify the real problem it solves.
2. Identify its input.
3. Identify its output.
4. Determine whether a provider already exists.
5. Define a Pydantic schema if a boundary requires one.
6. Determine persistence requirements.
7. Determine retry behavior.
8. Determine whether it should be asynchronous.
9. Add tests.
10. Integrate it into the appropriate product pipeline.

Keep the stage focused.

---

# 49. Adding a New Product

When adding another product:

1. Reuse Company and shared data infrastructure.
2. Reuse common extraction/analysis/enrichment capabilities.
3. Define the new ICP.
4. Define product-specific signals.
5. Define product-specific scoring.
6. Define qualification rules.
7. Define product knowledge.
8. Define intelligence prompts/output.
9. Reuse outreach infrastructure where possible.
10. Keep product-specific strategy isolated.

Do not fork the entire pipeline.

---

# 50. Pipeline Design Rule

A pipeline should be understandable by reading it.

A developer should be able to see:

    discover
        ↓
    analyze
        ↓
    enrich
        ↓
    verify
        ↓
    score
        ↓
    qualify

without tracing through dozens of abstractions.

If understanding a pipeline requires navigating many factories, managers, registries, event handlers, and generic workflow objects, the architecture has probably become too complex.

---

# 51. Golden Rule

Autlead pipelines should remain:

**Explicit enough to understand.**

**Modular enough to change.**

**Asynchronous where useful.**

**Provider-independent.**

**Resumable.**

**Evidence-driven.**

**Incremental.**

The objective is not to build a sophisticated workflow framework.

The objective is to reliably move real business data through:

    Discovery
        ↓
    Analysis
        ↓
    Evidence
        ↓
    Signals
        ↓
    Enrichment
        ↓
    Qualification
        ↓
    Intelligence
        ↓
    Outcomes

and continuously improve the process using real-world results.