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

Autlead is a modular monolith with asynchronous workers.

                         AUTLEAD
                            │
              ┌─────────────┴─────────────┐
              │                           │
           WebArtsy                    Autply
           Pipeline                   Pipeline
              │                           │
              └─────────────┬─────────────┘
                            │
                       Shared ETL
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
      Extract            Transform             Load
        │                   │                   │
        │          ┌────────┼─────────┐         │
        │          │        │         │         │
        │      Normalize  Analyze   Score        │
        │          │        │         │          │
        └──────────┴────────┴─────────┴──────────┘
                            │
                       PostgreSQL
                            │
                     Celery + Redis
                            │
                      External Providers
Architectural principles
ETL is the primary organization model.
External providers are replaceable.
Protocols define capabilities, not implementations.
PostgreSQL is the source of truth.
Celery and Redis handle asynchronous execution.
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
autlead/
│   │   ├── deduplication/
│   │   ├── entity_resolution/
│   │   ├── analysis/
│   │   ├── enrichment/
│   │   ├── signal_extraction/
│   │   ├── scoring/
│   │   └── qualification/
│   │
│   ├── load/
│   │   ├── postgres/
│   │   ├── events/
│   │   ├── exports/
│   │   └── webhooks/
│   │
│   ├── intelligence/
│   │   ├── rules/
│   │   ├── heuristics/
│   │   ├── scoring/
│   │   ├── reasoning/
│   │   ├── personalization/
│   │   ├── prompts/
│   │   ├── schemas/
│   │   └── llm/
│   │
│   ├── providers/
│   │   ├── discovery/
│   │   ├── search/
│   │   ├── crawling/
│   │   ├── technology/
│   │   ├── contacts/
│   │   ├── verification/
│   │   ├── llm/
│   │   ├── email/
│   │   └── reviews/
│   │
│   ├── pipelines/
│   │   ├── common/
│   │   ├── webartsy/
│   │   └── autply/
│   │
│   ├── state/
│   │   ├── pipeline.py
│   │   ├── checkpoints.py
│   │   ├── transitions.py
│   │   ├── retries.py
│   │   ├── locks.py
│   │   └── recovery.py
│   │
│   ├── events/
│   ├── policies/
│   └── notifications/
│
├── workers/
│   ├── celery_app.py
│   ├── queues.py
│   ├── routing.py
│   ├── schedules.py
│   └── tasks/
│
├── bootstrap/
│
├── knowledge/
│   ├── webartsy/
│   ├── autply/
│   └── system/
│
├── migrations/
│   └── versions/
│
├── scripts/
├── exports/
├── logs/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── e2e/
│
├── .github/
│   └── workflows/
│
├── main.py
├── pyproject.toml
├── alembic.ini
├── docker-compose.yml
├── .env.example
└── README.md

The structure is intentionally modular, but the project avoids unnecessary layers such as a generic ports/ directory, excessive factories, or one-file-per-abstraction.

Protocols live close to the capability they define.

For example:

providers/
└── discovery/
    ├── protocol.py
    └── google_maps.py
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

Celery is introduced for expensive or long-running operations.

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

Autlead is currently in the foundation/setup phase.

Completed:

Python 3.12 environment
uv
Project structure
Pydantic
SQLAlchemy
Alembic
PostgreSQL tooling
Celery dependencies
Redis dependencies
Playwright
Pytest
Ruff
Mypy
Pre-commit

Next:

PostgreSQL connection
        ↓
SQLAlchemy foundation
        ↓
Alembic
        ↓
Company model
        ↓
Source model
        ↓
First discovery provider
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