Autlead — Revised Project Execution Plan
1. Immediate Goal

The first version of Autlead should do only this:

Search / Discovery Provider
        ↓
Raw Business Data
        ↓
Normalize
        ↓
Deduplicate
        ↓
Store in PostgreSQL
        ↓
Export / Display Lead List

The output should be something like:

Company
Website
Domain
Phone
Location
Category
Source
Collected At

That is the first definition of success.

No intelligence.

No LLM.

No knowledge system.

No Celery.

No Redis.

No events.

No outreach.

No complex pipeline state.

No autonomous decision-making.

2. Architecture for the Base Version

The initial architecture is:

                         AUTLEAD
                            │
                            ▼
                       PIPELINES
                            │
                            ▼
                         EXTRACT
                            │
                   ┌────────┴────────┐
                   │                 │
              Discovery          Crawling
              Provider           Provider
                   │
                   ▼
                TRANSFORM
                   │
          ┌────────┼─────────┐
          │        │         │
     Normalize  Deduplicate  Basic Analysis
          │        │
          └────────┴─────────┘
                   │
                   ▼
                  LOAD
                   │
              PostgreSQL
                   │
                   ▼
               Lead List

Even the crawling provider should be introduced only when the first discovery flow is working.

3. What Is Explicitly Deferred

These are future phases, not current architecture requirements:

❌ Intelligence
❌ Ollama
❌ Knowledge
❌ Events
❌ Celery
❌ Redis
❌ Checkpoints
❌ Distributed locks
❌ Recovery
❌ Retry infrastructure
❌ Automatic provider routing
❌ Complex provider registry
❌ Outreach
❌ Suppression
❌ Metrics dashboard
❌ ML scoring
❌ RAG

They can be added later without changing the fundamental ETL architecture.

4. Phase 0 — Development Foundation

Already largely established.

Use:

Python 3.12
uv
Pydantic
Pydantic Settings
SQLAlchemy
Alembic
PostgreSQL
asyncpg
HTTPX
Playwright
Pytest
Ruff
Mypy
Pre-commit

Do not add dependencies simply because they may be useful later.

The rule is:

A dependency enters the project when an implemented feature needs it.

5. Phase 1 — Repository Foundation

Make sure the repository itself is clean.

Initial important structure:

autlead/
├── app/
│   ├── core/
│   ├── extract/
│   ├── load/
│   ├── models/
│   ├── pipelines/
│   ├── policies/
│   ├── providers/
│   └── transform/
│
├── migrations/
├── scripts/
├── tests/
├── exports/
├── logs/
│
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── main.py
├── pyproject.toml
├── README.md
└── AGENTS.md

Don't expand this structure until the implementation requires it.

6. Phase 2 — Minimal Configuration

Start with only what the base system needs.

For example:

class Settings(BaseSettings):
    app_name: str
    app_env: str
    debug: bool
    database_url: str

Potential future settings such as:

REDIS_URL
CELERY_BROKER_URL
OLLAMA_BASE_URL
OLLAMA_MODEL

do not belong yet.

When Celery is introduced, add its configuration.

When Ollama is introduced, add its configuration.

This keeps configuration from becoming a dumping ground.

7. Phase 3 — PostgreSQL Foundation

Set up:

app/core/
└── database/
    ├── __init__.py
    ├── engine.py
    ├── session.py
    └── base.py

Responsibilities:

engine.py

Create the SQLAlchemy async engine.

session.py

Create the async session factory.

base.py

Define the SQLAlchemy declarative base.

Use:

SQLAlchemy 2.x
asyncpg

At this stage, nothing else.

8. Phase 4 — Alembic

Configure:

Alembic
    ↓
PostgreSQL

Then create the first migration.

Do not create tables for the entire future system.

Only create what the lead-discovery MVP requires.

9. Phase 5 — First Core Model: Company

Start with the most important entity:

Company

Initial fields:

id
name
normalized_name
website
domain
phone
country
city
address
category
created_at
updated_at

Keep it deliberately small.

If a field isn't required by the first lead pipeline, don't add it yet.

10. Phase 6 — Source / Provenance

Autlead will eventually use many providers, so provenance matters from the beginning.

Introduce a minimal source concept.

For example:

Source
    id
    name
    type

And/or source information associated with extracted records.

The system should be able to answer:

Where did this company come from?
Which provider produced it?
When was it collected?

This becomes particularly important when multiple providers discover the same company.

11. Phase 7 — First Provider: Business Discovery

This is the first major implementation.

Use an existing open-source project.

For example:

Google Maps / Business extraction
        ↓
existing open-source repository
        ↓
Autlead provider adapter

Do not write a custom Google Maps scraper unless there is a genuine reason later.

Provider structure:

app/providers/discovery/
├── __init__.py
├── protocol.py
└── <provider>.py

The exact provider name should reflect the implementation actually selected.

12. Phase 8 — Discovery Contract

Define what Autlead needs from a business-discovery provider.

For example:

class BusinessDiscoveryProvider(Protocol):
    async def discover(
        self,
        query: DiscoveryQuery,
    ) -> list[BusinessRecord]:
        ...

The important point is that the pipeline knows:

"I need businesses."

It does not know:

"Call this particular scraping repository."
13. Phase 9 — Provider Adapter

The provider adapter translates external output into Autlead's own schema.

Open-source repository
        ↓
External response
        ↓
Provider adapter
        ↓
BusinessRecord

For example:

BusinessRecord
├── name
├── website
├── domain
├── phone
├── address
├── city
├── country
└── category

This is one of the most important architectural boundaries in Autlead.

14. Phase 10 — First ETL Vertical Slice

Now build the first complete path:

Discovery Provider
        ↓
BusinessRecord
        ↓
Normalize
        ↓
Deduplicate
        ↓
Company
        ↓
PostgreSQL

This is the first real Autlead milestone.

Example:

autlead discover \
    --query "ecommerce stores" \
    --location "Amsterdam"

Result:

Found: 37 businesses


New:
    29


Duplicates:
     8


Stored:
    29

At this point, Autlead is already useful.

15. Phase 11 — Normalization

Build only deterministic normalization.

Initial functions:

normalize_company_name()
normalize_url()
normalize_domain()
normalize_phone()
normalize_country()
normalize_address()

Example:

HTTPS://WWW.Example.COM/
        ↓
example.com

Keep raw values where useful.

Don't destroy source information just to normalize it.

16. Phase 12 — Deduplication

Once real records enter PostgreSQL, duplicates become a real problem.

Start simple.

Priority:

Source external ID
        ↓
Normalized domain
        ↓
Phone
        ↓
Name + location

Do not build sophisticated AI entity resolution yet.

The first question is simply:

Have we already seen this business?

17. Phase 13 — Lead List Output

This should be part of the first milestone.

The user needs to actually see the leads.

Possible outputs:

PostgreSQL
    +
CSV export

Example:

exports/
└── leads.csv

Containing:

company_name
website
domain
phone
city
country
category
source
created_at

This is much more important initially than an elaborate dashboard.

18. MVP-0 Definition

At this point, Autlead should be able to:

Query
  ↓
Discovery provider
  ↓
Business records
  ↓
Normalize
  ↓
Deduplicate
  ↓
PostgreSQL
  ↓
CSV / lead list
MVP-0 is DONE when:
PostgreSQL works
Alembic works
Discovery provider works
Provider adapter works
Pydantic validation works
Normalization works
Deduplication works
Companies are persisted
Leads can be exported
Tests pass

That's it.

Stop here and use it.

19. Phase 14 — Multiple Discovery Providers

Only after MVP-0 works should we expand discovery.

Potentially:

providers/discovery/


    provider_a
    provider_b
    provider_c

All implement:

BusinessDiscoveryProvider

The pipeline remains:

DiscoveryProvider
      ↓
BusinessRecord
      ↓
Transform
      ↓
Company

This gives Autlead provider independence without building a complicated routing framework.

20. Phase 15 — Website Crawling

Now introduce crawling because it gives us more useful lead information.

Company
   ↓
Website URL
   ↓
Crawler Provider
   ↓
Website data

Potential implementation:

Crawl4AI

through a provider adapter.

Structure:

app/providers/crawling/
├── protocol.py
└── <provider>.py
21. Phase 16 — Basic Website Analysis

Initially, don't build a giant website-audit system.

Collect useful information:

HTTP status
title
meta description
HTML
SSL
redirects
CMS
technology

Only add additional analysis when the lead-generation process demonstrates that it is useful.

22. Phase 17 — Technology Detection

Add technology detection through an existing open-source provider.

For example:

Wappalyzer-compatible implementation

Flow:

Website
   ↓
Technology Provider
   ↓
Technology observations

Examples:

WordPress
Shopify
WooCommerce
Intercom
Zendesk
Tawk

Again, the provider only detects technology.

It doesn't decide whether the company is a good lead.

23. Phase 18 — Observations

Now introduce structured observations.

Example:

Company: 123


Observation:
    type = technology
    value = WordPress
    provider = wappalyzer
    observed_at = ...

Another:

Observation:
    type = website
    value = missing_meta_description

Observations are evidence.

They are not yet sales conclusions.

24. Phase 19 — First Signals

Only after observations exist should we introduce signals.

Observation
     ↓
Signal rule
     ↓
Signal

Example:

WordPress
+
poor performance
+
outdated design indicators
        ↓
website_modernization_opportunity

Start with a handful of useful signals.

25. Phase 20 — Contact Discovery

Now we enrich the lead.

Potential providers:

Website
Search
Open-source contact tools

Flow:

Company
   ↓
Contact Provider
   ↓
ContactCandidate

Don't assume a discovered contact is verified.

26. Phase 21 — Email Verification

Introduce a verification provider.

Possible implementations:

Reacher
SMTP/DNS verification
other open-source verifier

Flow:

ContactCandidate
        ↓
Verification Provider
        ↓
VerificationResult

Only then should the system mark an email as sufficiently verified for the relevant pipeline.

27. Phase 22 — Scoring

Now scoring becomes useful because we have actual evidence.

Start deterministic:

ICP fit
+
signals
+
website opportunity
+
contact quality
=
score

Don't use AI.

Don't use machine learning.

Don't make scoring unnecessarily complicated.

28. Phase 23 — Qualification

Then introduce:

qualified
parked
rejected
needs_review

Example:

score >= threshold
+
appropriate contact
+
relevant signal
        ↓
qualified

Qualification belongs to the product/policy layer, not providers.

29. At This Point: Real Lead Engine

Now the system becomes:

Discovery
    ↓
Normalization
    ↓
Deduplication
    ↓
Website Crawling
    ↓
Technology Detection
    ↓
Observations
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
PostgreSQL
    ↓
Qualified Lead List

This is the real first Autlead system.

30. Only After This: Celery + Redis

Now ask:

Which operations are actually slow enough to require workers?

Probably:

website crawling
technology detection
contact discovery
email verification

Only then introduce:

Celery
Redis
workers

Architecture becomes:

Pipeline
    ↓
Celery Task
    ↓
Application operation
    ↓
Provider

Not:

Celery task containing the entire application
31. Then: State

After asynchronous workers exist, introduce:

pipeline state
checkpoints
retries
locks
recovery
transitions

These solve actual problems created by distributed execution.

They should not be implemented just because they look good architecturally.

32. Then: Intelligence

Only after Autlead can reliably produce good leads should intelligence be introduced.

Company
+
Observations
+
Signals
+
Score
+
ICP
        ↓
LLM
        ↓
Lead intelligence

Potential output:

summary
pain hypothesis
opportunity
personalization angle
offer angle
draft

Ollama becomes a provider:

providers/llm/
└── ollama.py

The rest of Autlead does not depend directly on Ollama.

33. Then: Knowledge

After intelligence is useful, introduce:

knowledge/
├── webartsy/
└── autply/

Knowledge can contain:

ICP
products
services
positioning
competitors
objections
messaging

The LLM then receives:

Lead evidence
+
Product knowledge
+
ICP
        ↓
Intelligence
34. Then: Autply

Only after WebArtsy's lead engine has been proven should Autply become a major implementation target.

Reuse:

Discovery
Normalization
Deduplication
Crawling
Technology detection
Contacts
Verification
Scoring infrastructure
Qualification infrastructure
PostgreSQL
Provider architecture

Change:

Signals
Policies
Scoring
ICP
Intelligence

rather than duplicating the whole system.

35. Then: Additional Autply Signals

Potentially:

support platform detected
multiple support channels
competitor detected
negative support reviews
support hiring

But each should be added because it improves lead quality—not simply because the architecture allows it.

36. Then: Outreach

Only after lead quality is demonstrated:

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

Start with human approval.

Automation can increase later.

37. Then: Suppression

Before meaningful automated outreach:

suppression
unsubscribe
bounce
complaint
manual exclusion

WebArtsy and Autply should share suppression logic.

38. Then: Metrics

Measure what matters:

discovered
analyzed
enriched
verified
qualified
sent
replied
positive replies
meetings
customers

Break it down by:

product
source
provider
country
signal
score

Only now do we have enough data to determine which parts of the engine actually work.

39. Final Development Sequence

The revised sequence is:

PHASE 1
Repository + Configuration
        ↓
PHASE 2
PostgreSQL + SQLAlchemy + Alembic
        ↓
PHASE 3
Company + Source models
        ↓
PHASE 4
Business Discovery Provider
        ↓
PHASE 5
Provider Adapter
        ↓
PHASE 6
Normalization
        ↓
PHASE 7
Deduplication
        ↓
PHASE 8
PostgreSQL persistence
        ↓
PHASE 9
CSV / Lead List export
        ↓
=========================
     MVP-0 COMPLETE
=========================
        ↓
PHASE 10
Additional Discovery Providers
        ↓
PHASE 11
Website Crawling
        ↓
PHASE 12
Technology Detection
        ↓
PHASE 13
Observations
        ↓
PHASE 14
Signals
        ↓
PHASE 15
Contact Discovery
        ↓
PHASE 16
Email Verification
        ↓
PHASE 17
Scoring
        ↓
PHASE 18
Qualification
        ↓
=========================
   LEAD ENGINE COMPLETE
=========================
        ↓
PHASE 19
Celery + Redis
        ↓
PHASE 20
Workers
        ↓
PHASE 21
State / Checkpoints / Retry
        ↓
PHASE 22
Provider Health / Routing
        ↓
PHASE 23
Ollama / Intelligence
        ↓
PHASE 24
Knowledge
        ↓
PHASE 25
Autply Pipeline
        ↓
PHASE 26
Outreach
        ↓
PHASE 27
Suppression
        ↓
PHASE 28
Metrics + Feedback
40. The Critical Milestones

There are really only three major milestones initially:

Milestone 1 — Lead Collector
Provider
 ↓
Normalize
 ↓
Deduplicate
 ↓
PostgreSQL
 ↓
CSV

Goal: Get a reliable list of companies.

Milestone 2 — Lead Engine
Company
 ↓
Website
 ↓
Technology
 ↓
Observations
 ↓
Signals
 ↓
Contact
 ↓
Verification
 ↓
Score
 ↓
Qualification

Goal: Get a reliable list of qualified leads.

Milestone 3 — Sales Intelligence
Qualified Lead
 ↓
Knowledge
 +
Evidence
 ↓
LLM
 ↓
Personalized intelligence
 ↓
Outreach

Goal: Turn qualified leads into actionable prospects.

This is a much better progression for Autlead. It keeps the initial system small enough to finish, while preserving the provider/ETL architecture needed to evolve it into the larger system later.

The immediate target is therefore not "build Autlead." It is:

Build MVP-0: discover businesses → normalize → deduplicate → persist → produce a usable lead list.