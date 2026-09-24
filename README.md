Autlead

Autlead is a self-hosted, modular B2B lead intelligence and generation engine built with Python.

It is designed to support multiple products and ICPs while reusing the same underlying ETL, enrichment, analysis, scoring, intelligence, and outreach infrastructure.

The initial products are:

WebArtsy — web development, SEO, ERP, software development, and digital services.
Autply — AI-powered unified inbox and customer-support automation.
Goals

Autlead is designed to:

Discover potential B2B companies from multiple sources.
Analyze websites, technologies, and publicly available business signals.
Enrich companies with relevant decision-maker information.
Verify contact information.
Generate evidence-based lead signals.
Score and qualify leads for different products.
Generate personalized intelligence and outreach using local LLMs.
Maintain complete data provenance and pipeline state.
Support multiple providers for the same capability.
Run processing asynchronously using Celery workers.
Store authoritative data in PostgreSQL.
Remain self-hosted and minimize dependence on paid SaaS platforms.
Core Philosophy

Autlead does not attempt to reinvent existing extraction technology.

When a capable open-source project already exists, Autlead integrates it.

Examples include:

Google Maps / business discovery
Website crawling
Technology detection
Search
Email verification
LLM inference

These become providers behind Autlead-defined contracts.

Open-source project
        ↓
Provider adapter
        ↓
Autlead protocol
        ↓
Normalized data
        ↓
ETL pipeline

The external project is replaceable.

The Autlead data model and business logic are not tied to it.

Architecture

Autlead is a modular monolith organized around three independent generic flows:

    Acquisition
        ↓
    PostgreSQL
        ↓
    Enrichment
        ↓
    PostgreSQL
        ↓
    Outreach

PostgreSQL is the source of truth and the durable boundary between flows.

The intended application entry points are:

    run_acquisition(...)
    run_enrichment(...)
    run_outreach(...)

The flows are not product-specific. WebArtsy and Autply reuse acquisition and enrichment infrastructure while keeping product-specific signals, scoring, qualification, intelligence, messaging, and outreach strategy separate.

Architectural principles
ETL is the primary organization model.
External providers are replaceable.
Protocols define capabilities, not implementations.
PostgreSQL is the source of truth.
Asynchronous infrastructure such as Celery and Redis should be introduced only when demonstrated workload requirements justify it.
Workers execute work; they do not contain business logic.
Important conclusions must be backed by evidence.
Configuration and abstractions are added only when required.
Existing open-source technology should be reused instead of rewritten.
Avoid premature microservices and infrastructure complexity.
Technology Stack
Core
Python 3.12
uv
Pydantic
Pydantic Settings
SQLAlchemy 2.x
Alembic
PostgreSQL
asyncpg
Async Processing
Celery
Redis
HTTP / Browser
HTTPX
Playwright
Open-source crawler/analyzer providers
Intelligence
Ollama
Local open-source LLMs
Development
Pytest
Ruff
Mypy
Pre-commit
Project Structure

The current pipeline structure is intentionally explicit:

    app/
    ├── cli/
    │   ├── acquisition.py
    │   └── enrichment.py
    ├── pipelines/
    │   ├── acquisition/
    │   │   ├── business_discovery.py
    │   │   ├── models.py
    │   │   └── pipeline.py
    │   └── enrichment/
    │       ├── core/
    │       │   ├── pipeline.py
    │       │   ├── company.py
    │       │   ├── lifecycle.py
    │       │   ├── models.py
    │       │   └── work_items.py
    │       └── stages/
    │           ├── homepage.py
    │           ├── business_pages.py
    │           ├── technology_detection.py
    │           ├── website_performance.py
    │           ├── contacts.py
    │           ├── people.py
    │           └── person_email.py
    ├── providers/
    ├── policies/
    ├── state/
    ├── models/
    ├── load/
    ├── extract/
    └── transform/

Pipeline-specific logic should not be hidden in a generic `pipelines/common/` package. Truly generic execution infrastructure may remain shared.

Protocols live close to the capability they define. Avoid generic registries, excessive factories, and one-file-per-abstraction.

ETL Pipeline

The general pipeline is:

EXTRACT
   ↓
NORMALIZE
   ↓
DEDUPLICATE
   ↓
ANALYZE
   ↓
OBSERVATIONS
   ↓
SIGNALS
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

Not every pipeline needs every stage.

Individual products can configure their own strategy while sharing the underlying infrastructure.

Providers

Providers integrate external capabilities into Autlead.

Examples:

Business Discovery
    ├── Google Maps provider
    ├── Directory provider
    └── Public dataset provider


Website Crawling
    ├── Crawl4AI
    ├── HTTP crawler
    └── Browser crawler


Technology Detection
    ├── Wappalyzer-compatible provider
    └── Other fingerprint provider


Search
    ├── DuckDuckGo
    ├── SearXNG
    └── Other search provider


Email Verification
    ├── Reacher
    ├── SMTP verification
    └── DNS/MX verification


LLM
    └── Ollama

A capability has a protocol:

class BusinessDiscoveryProvider(Protocol):
    async def discover(
        self,
        query: DiscoveryQuery,
    ) -> list[BusinessRecord]:
        ...

A provider implements that protocol.

This allows one provider to be replaced without changing the rest of the pipeline.

Data Model

Autlead is evidence-driven.

Important concepts include:

Company
Domain
Website


Source
SourceRecord


Observation
Signal


Contact
VerificationResult


LeadScore
PipelineRun
PipelineStep
Observation

An observation represents something actually discovered.

Example:

Technology detected
    WordPress
    confidence: 0.96
    source: website
    provider: technology-provider
Signal

A signal represents an interpretation of observations.

Observation
    ↓
Rule
    ↓
Signal

Example:

mobile performance = 32
        ↓
poor_mobile_performance

Signals provide the foundation for lead scoring and intelligence.

Current Operational Flows

Acquisition

    DiscoveryQuery
        ↓
    BusinessDiscoveryProvider
        ↓
    Discover
        ↓
    Normalize
        ↓
    Deduplicate
        ↓
    Persist Company / Source / SourceRecord
        ↓
    Commit
        ↓
    STOP

Acquisition is independently runnable with the `acquisition` CLI command. It does not crawl websites, enrich contacts/people, qualify leads, or perform outreach.

Enrichment

    Persisted Company
        ↓
    Technology Detection
        ↓
    Performance / SEO
        ↓
    Homepage Analysis
        ↓
    Business Page Collection
        ↓
    Contact Analysis
        ↓
    People Analysis / Persistence
        ↓
    Person Email Discovery / Verification
        ↓
    PostgreSQL

Enrichment is independently runnable with the `enrichment` CLI command.

Enrichment uses persisted checkpoints so successful stages do not need to be repeated unnecessarily. Normal stages mark running, execute, and mark completed with transaction boundaries around state changes. Failures are rolled back, recorded as failed, and re-raised.

Homepage and business-page processing are rehydrating stages: downstream work still needs page content even when their enrichment checkpoint is complete.

Website crawl freshness is separate from enrichment checkpoint completion. A completed crawl may be started again after its retention period expires:

    COMPLETED -> RUNNING -> COMPLETED

This supports retention-based refresh without rediscovering the company.

People enrichment combines deterministic extraction, optional LLM refinement, policy classification, deterministic normalization/entity resolution/ranking, and persistence. LLM failure falls back to deterministic candidates.

Person-email enrichment loads persisted people for a company, generates candidate addresses, verifies them sequentially, persists verification evidence, and selects the first qualified email.

Outreach

Outreach remains the next major generic flow:

    Enriched Company
        ↓
    Campaign Candidate
        ↓
    Suitable Contact
        ↓
    Generate / Select Message
        ↓
    Send
        ↓
    Persist Status

Initial campaign persistence should remain minimal:

    Campaign
        id
        name
        status
        created_at
        updated_at

    CampaignLead
        id
        campaign_id
        company_id
        status
        created_at
        updated_at

Initial CampaignLead statuses are `pending`, `sent`, and `failed`.

Do not add campaign-message, event, scheduling, template, or workflow models until real requirements justify them.

WebArtsy Pipeline

WebArtsy targets businesses that may have opportunities in:

Web development
SEO
Ecommerce
ERP
Custom software
Website modernization

Initial pipeline:

Business Discovery
        ↓
Company Normalization
        ↓
Website Discovery
        ↓
Website Analysis
        ↓
Technology Detection
        ↓
Web/SEO Signals
        ↓
Decision Maker Discovery
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

Potential signals include:

No website
Poor website
Poor mobile performance
Missing metadata
Outdated technology
Ecommerce opportunity
Weak conversion structure

Signals will be validated and refined using real-world results rather than assumptions.

Autply Pipeline

Autply targets businesses with customer-support complexity.

Potential signals include:

Support platform detected
Competitor detected
Multiple support channels
Live chat
Support hiring
Customer-service growth
Support-related complaints

Pipeline:

Company Discovery
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
Outreach
Intelligence

Autlead uses deterministic logic wherever possible.

Facts       → deterministic systems
Signals     → rules/heuristics
Scoring     → deterministic strategies
Reasoning   → LLM
Writing     → LLM

LLM output is structured and validated using Pydantic.

The LLM should receive evidence rather than raw, uncontrolled data.

Example:

Company
    ↓
Observations
    ↓
Signals
    ↓
Score
    ↓
LLM
    ↓
Business interpretation
    ↓
Personalized message
Product Knowledge

Product-specific knowledge lives separately from application code.

knowledge/
├── webartsy/
│   ├── icp.md
│   ├── services.md
│   ├── positioning.md
│   ├── objections.md
│   └── messaging.md
│
├── autply/
│   ├── icp.md
│   ├── product.md
│   ├── competitors.md
│   ├── positioning.md
│   └── messaging.md
│
└── system/

This allows product strategy and messaging to evolve without changing the core pipeline.

Async Processing

This remains a future scaling option rather than a requirement of the current three-flow architecture.

Celery may be introduced for expensive or long-running operations when real workloads justify it.

Potential queues:

extract
analysis
enrichment
verification
intelligence
outreach
maintenance

Workers should remain thin:

Celery Task
    ↓
Application operation
    ↓
Provider

Workers should not contain the business logic themselves.

PostgreSQL stores pipeline state.

Redis handles Celery execution infrastructure and short-lived coordination.

State and Reliability

Processing must be resumable.

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

Failed stages can be retried without unnecessarily repeating successful work.

Operations should be:

Idempotent
Retryable where appropriate
Observable
Traceable to a provider and source
Development Strategy

Autlead will be developed incrementally.

We do not build the entire architecture before writing useful functionality.

The first vertical slice is:

Open-source business discovery provider
        ↓
Raw business record
        ↓
Pydantic validation
        ↓
Normalization
        ↓
Deduplication
        ↓
Company
        ↓
PostgreSQL

Once that works, the next capability is added.

Development Order
1. Development environment
2. Repository configuration
3. Pydantic Settings
4. PostgreSQL
5. SQLAlchemy
6. Alembic
7. Company model
8. Source / raw-record model
9. Business discovery protocol
10. First open-source discovery provider
11. First ETL vertical slice
12. Normalization
13. Deduplication
14. Website crawler provider
15. Website analysis
16. Observations
17. Technology detection provider
18. Signals
19. WebArtsy signals
20. Contact discovery
21. Email verification
22. Scoring
23. Qualification
24. Celery + Redis
25. Pipeline state/checkpoints
26. Retry/idempotency
27. Complete WebArtsy pipeline
28. Real-world validation
29. Ollama intelligence
30. Product knowledge
31. Autply signals
32. Autply pipeline
33. Additional providers
34. Outreach
35. Suppression
36. Metrics
37. Feedback loop
38. Optimization
What Autlead Will Not Do

Autlead will not initially build its own:

Google Maps scraper
Search engine
Web crawler
Wappalyzer replacement
Email verification service
LLM
Distributed infrastructure platform

Existing open-source projects will be evaluated and integrated where appropriate.

Autlead's value is in combining these capabilities into a reliable, evidence-driven lead intelligence pipeline.

Testing

Testing is divided into four levels.

Unit

Test pure business logic:

Normalization
Deduplication
Signals
Scoring
Qualification
Policies
Integration

Test:

PostgreSQL
SQLAlchemy
Redis
Celery
Contract

Ensure every provider conforms to its protocol.

End-to-End

Use fake providers to test complete pipelines without relying on external services.

Fake Discovery
      ↓
Fake Analyzer
      ↓
Fake Enrichment
      ↓
Fake Verifier
      ↓
Fake LLM
      ↓
Expected Lead
Development Commands

Install dependencies:

uv sync

Run tests:

uv run pytest

Lint:

uv run ruff check .

Format:

uv run ruff format .

Type check:

uv run mypy app

Run all checks:

uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
Current Status

Autlead is beyond the foundation/setup phase.

Completed or working:

- Python 3.12 / uv project foundation.
- PostgreSQL, SQLAlchemy, Alembic, and persistence infrastructure.
- Company/source persistence and provenance.
- Business discovery provider integration.
- Acquisition flow with normalization and deduplication.
- Generic acquisition CLI.
- Website crawling with Crawl4AI.
- Technology detection.
- Website performance / SEO analysis.
- Homepage and business-page crawling.
- Contact extraction.
- People extraction, refinement, classification, and persistence.
- Person-email candidate generation and verification.
- Persisted enrichment stage checkpoints and retry/resume behavior.
- Generic enrichment CLI.
- Resend email sending has been tested successfully.
- A single-company end-to-end enrichment run completed successfully.

Current scaling issues identified by the single-company enrichment test:

1. LLM refinement payloads must be bounded. A request can exceed the configured provider token/rate limit; an inherently oversized request should be reduced rather than repeatedly retried.
2. Person-email target selection must be validated before a large run. The stage currently operates on persisted people for the company, which can include historical people in addition to people found in the current run.

Immediate next work:

    Finish generic enrichment refactor
        ↓
    Validate persisted-person selection
        ↓
    Bound LLM refinement payloads
        ↓
    Run controlled multi-company enrichment
        ↓
    Validate persisted results and provider cost/rate behavior
        ↓
    Build minimal Campaign / CampaignLead outreach flow

Current refactoring rules:

- Refactor one flow at a time.
- Keep PostgreSQL as the source of truth and boundary between flows.
- Do not change the database schema merely to reorganize pipeline code.
- Preserve existing persistence, transaction, and state semantics during structural refactors.
- Keep providers free of product scoring, qualification, messaging, and outreach decisions.
- Keep orchestration explicit and readable.
- Avoid generic workflow engines, registries, premature abstractions, Celery/Redis expansion, or other infrastructure without demonstrated need.
- Keep generic acquisition/enrichment separate from WebArtsy/Autply strategy.

Long-Term Vision

Autlead should eventually become a reusable lead intelligence platform where adding a new data source or product does not require rebuilding the system.

             DATA SOURCES
                  │
       ┌──────────┼──────────┐
       ↓          ↓          ↓
     Maps    Directories   Search
       │          │          │
       └──────────┼──────────┘
                  ↓
             AUTLEAD ETL
                  │
       ┌──────────┼──────────┐
       ↓          ↓          ↓
   Analysis    Signals    Enrichment
       │          │          │
       └──────────┼──────────┘
                  ↓
               Scoring
                  ↓
            Qualification
                  ↓
             Intelligence
                  ↓
              Outreach
                  ↓
              Outcomes
                  ↓
              Feedback
                  ↓
             Optimization

The long-term asset is not any individual scraper or LLM.

It is the normalized data, evidence, signals, scoring logic, provider architecture, pipeline history, and accumulated outcome data that Autlead builds over time.