# Autlead — Agent Development Guide

## 1. Purpose

Autlead is a modular Python ETL application for collecting, transforming, enriching, qualifying, and eventually generating B2B leads.

The project is intentionally being developed incrementally.

The current objective is not to build the complete future Autlead architecture.

The immediate objective is to establish a reliable base lead-collection system:

    Provider
        ↓
    Extract
        ↓
    Normalize
        ↓
    Deduplicate
        ↓
    PostgreSQL
        ↓
    Lead List

Future capabilities such as workers, Redis, Celery, intelligence, knowledge, state management, and outreach are introduced only when the project reaches the stage where they are actually required.

---

# 2. Documentation Is Part of the Architecture

Autlead has detailed documentation next to the corresponding code.

Agents MUST read the relevant documentation before modifying a subsystem.

Do not treat these files as optional notes.

They define the intended architecture and development rules for that part of the project.

---

# 3. Documentation Map

## Project execution

Before deciding what to implement next, read:

    app/execution_plan.md

This is the primary implementation roadmap.

It defines:

- Current project phase
- Development order
- Deferred functionality
- Major milestones
- What should not be built yet

Do not implement future phases simply because their directories already exist.

---

## Models

Before modifying anything under:

    app/models/

read:

    app/models/MODELS.md

This defines:

- Domain models
- Persistence models
- Pydantic schemas
- Model boundaries
- Database responsibilities
- Relationships
- Validation rules

Do not invent a second model architecture without first checking `MODELS.md`.

---

## Extraction

Before modifying:

    app/extract/

read:

    app/extract/EXTRACT.md

Extraction is responsible for obtaining data from external sources through providers.

Typical flow:

    External Source
        ↓
    Provider
        ↓
    Extracted Record
        ↓
    Pydantic validation

Autlead should integrate existing open-source extraction technology rather than unnecessarily rebuilding it.

---

## Transformation

Before modifying:

    app/transform/

read:

    app/transform/TRANSFORM.md

Transformation is responsible for turning extracted data into useful, normalized Autlead data.

It may contain:

    normalization
    deduplication
    entity resolution
    analysis
    enrichment
    signal extraction
    scoring
    qualification

Do not assume every transformation exists in the current implementation.

Implement only what the current execution phase requires.

---

## Loading

Before modifying:

    app/load/

read:

    app/load/LOAD.md

Loading is responsible for persisting transformed data into the application's destinations.

For the current base version, PostgreSQL is the primary destination.

Exports such as CSV/JSON are secondary outputs and should not become the authoritative data store.

---

## Providers

Before modifying:

    app/providers/

read:

    app/providers/PROVIDERS.md

Providers integrate external capabilities.

Current/future provider categories may include:

    discovery
    search
    crawling
    technology
    contacts
    verification
    reviews
    email
    LLM

Providers are replaceable implementations.

The rest of Autlead should depend on Autlead-defined contracts and normalized structures rather than provider-specific APIs.

---

## Pipelines

Before modifying:

    app/pipelines/

read:

    app/pipelines/PIPELINES.md

Pipelines compose extraction, transformation, and loading operations.

A pipeline should coordinate application capabilities.

It should not become a dumping ground for:

- Provider-specific scraping logic
- Database implementation details
- Business rules that belong in policies
- Large transformation functions

---

## Policies

Before modifying:

    app/policies/

read:

    app/policies/POLICIES.md

Policies contain business/application decisions.

Examples may include:

- Qualification rules
- Scoring rules
- Product-specific rules
- Filtering rules
- Outreach policies
- Compliance-related decisions

Providers should not contain product-specific policies.

---

## State

Before modifying:

    app/state/

read:

    app/state/STATE.md

State infrastructure is intentionally a later concern.

It may eventually handle:

- Pipeline execution state
- Checkpoints
- Retries
- Locks
- Recovery
- State transitions

Do not expand the state system merely because the directory exists.

State infrastructure should be introduced when asynchronous/distributed execution requires it.

---

# 4. Current Project Phase

The current target is the base lead-collection system.

The immediate architecture is:

    Discovery Provider
          ↓
       Extract
          ↓
    Pydantic Record
          ↓
      Normalize
          ↓
     Deduplicate
          ↓
        Company
          ↓
     PostgreSQL
          ↓
      Lead Export

The first milestone is:

> Get a real list of businesses into PostgreSQL reliably.

---

# 5. Currently Deferred

Do not implement these unless the execution plan explicitly reaches the relevant phase:

    ❌ Celery
    ❌ Redis
    ❌ Workers
    ❌ Intelligence
    ❌ Ollama
    ❌ Knowledge system
    ❌ Event system
    ❌ Complex state management
    ❌ Checkpoints
    ❌ Distributed locks
    ❌ Recovery infrastructure
    ❌ Automated outreach
    ❌ ML scoring
    ❌ RAG
    ❌ Vector database
    ❌ Complex dashboard

The existence of directories for future functionality does not mean those features should currently be implemented.

---

# 6. Core Architecture

Autlead is a modular monolith.

The primary architectural model is:

    EXTRACT
        ↓
    TRANSFORM
        ↓
    LOAD

External capabilities are integrated through providers:

    Open-source project
        ↓
    Provider adapter
        ↓
    Autlead contract
        ↓
    Autlead schema
        ↓
    ETL pipeline

The application owns:

- Integration
- Validation
- Normalization
- Deduplication
- Provenance
- Persistence
- Transformation
- Business policies

External projects own the specialized extraction capabilities they already provide.

---

# 7. Do Not Reinvent Existing Open-Source Technology

Before implementing an external-data capability, check whether a suitable open-source project already exists.

Potential examples:

- Business discovery
- Google Maps extraction
- Website crawling
- Technology detection
- Search
- Contact discovery
- Email verification
- Reviews
- LLM inference

Prefer:

    Existing project
        ↓
    Provider adapter
        ↓
    Autlead

over:

    Existing project
        ↓
    Rewrite the entire thing ourselves

Only build custom extraction technology when there is a demonstrated reason.

---

# 8. Provider Independence

A pipeline should not be coupled directly to a specific external implementation.

Prefer:

    BusinessDiscoveryProvider
          ↑
          │
    ┌─────┴───────────────┐
    │                     │
Google Maps          Directory
Provider             Provider

The pipeline should operate against the capability.

Provider-specific implementation belongs inside the provider.

---

# 9. Protocols

Use Python `Protocol` when a capability needs an explicit contract.

Example:

```python
class BusinessDiscoveryProvider(Protocol):
    async def discover(
        self,
        query: DiscoveryQuery,
    ) -> list[BusinessRecord]:
        ...



Protocols should normally live close to their capability.

For example:

app/providers/discovery/
    protocol.py
    google_maps.py

Do not create a global ports/ directory simply to satisfy a theoretical architecture.

10. Avoid Premature Abstraction

Do not introduce abstractions without a concrete requirement.

Avoid speculative:

Provider registries
Provider factories
Provider managers
Generic repositories
Dependency injection containers
Service layers
Event buses
Workflow engines
Generic orchestration frameworks

Use a simple concrete implementation first.

Introduce an abstraction when:

A second implementation exists
A dependency needs to be replaceable
Testing benefits from the abstraction
The abstraction reduces real coupling
11. Pydantic

Use Pydantic at important data boundaries.

Examples:

Provider input
Provider output
Extracted records
Transformation records
Configuration
API data

Example:

class BusinessRecord(BaseModel):
    name: str
    website: str | None = None
    phone: str | None = None
    country: str | None = None

Prefer explicit schemas over unstructured dictionaries at important boundaries.

Do not create excessive duplicate schemas.

12. PostgreSQL

PostgreSQL is the authoritative persistence layer.

Use:

SQLAlchemy 2.x
asyncpg
Alembic

Database changes must go through Alembic migrations.

Do not use CSV or JSON files as the primary database.

Exports are outputs.

13. SQLAlchemy

Use modern SQLAlchemy 2.x patterns.

Use async database access.

Keep persistence concerns in the persistence layer.

Do not put:

Provider logic
Scraping logic
Product strategy
Lead scoring

inside SQLAlchemy models.

Do not automatically create repositories for every table.

14. Configuration

Configuration follows YAGNI.

Only configure what the current implementation needs.

For the base system this may be limited to:

app_name
app_env
debug
database_url

Do not add configuration for future systems simply because they are planned.

For example, do not add:

REDIS_URL
CELERY_BROKER_URL
OLLAMA_BASE_URL
OLLAMA_MODEL

until those features are actually being implemented.

15. ETL Rules

Every ETL stage should have a clear responsibility.

Extract

Get information from an external source.

Transform

Normalize, validate, deduplicate, analyze, enrich, score, or otherwise transform data.

Load

Persist data or produce an explicit output.

Avoid mixing all three responsibilities inside one large function.

16. Normalization

Prefer deterministic normalization.

Examples:

HTTPS://WWW.Example.COM/
        ↓
example.com

Potential normalization:

Company name
URL
Domain
Phone
Country
Address

Do not use an LLM for deterministic formatting problems.

17. Deduplication

Start with deterministic matching.

Potential identifiers:

Provider source ID
Domain
Phone
Name
Address

Prefer strong identifiers first.

Do not build sophisticated AI entity resolution before real data demonstrates that simple matching is insufficient.

18. Provenance

Important extracted data should retain source information.

The system should be able to answer:

Where did this record come from?
Which provider produced it?
When was it collected?

Do not throw away useful raw/provider information prematurely.

19. Errors

Handle errors at the appropriate boundary.

Provider-specific errors should be translated into application-understandable errors where necessary.

Do not silently swallow exceptions.

Do not use:

except Exception:
    pass

unless there is an explicit and documented reason.

20. Async Python

Use async operations for I/O-bound work where the underlying library supports it.

Typical candidates:

HTTP
Database
Crawling
External providers

Do not make everything async merely for stylistic reasons.

CPU-heavy work may require a different execution strategy later.

21. Testing

Test the behavior that matters.

Unit tests

Use for deterministic logic:

Normalization
Deduplication
Policies
Scoring
Qualification
Provider tests

Verify provider adapters and their contracts.

Integration tests

Verify:

PostgreSQL
SQLAlchemy
Alembic
ETL integration
End-to-end tests

Use fake providers where appropriate:

FakeDiscovery
FakeCrawler
FakeVerifier
FakeLLM

This keeps end-to-end tests deterministic.

22. Code Quality

Use:

uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest

Use Ruff for linting and formatting.

Use Mypy for type checking.

Use Pytest for tests.

Use pre-commit for repository checks.

Do not weaken typing or linting merely to make a check pass.

Fix the underlying issue where practical.

23. Adding a New Provider

Before adding a provider:

Read app/providers/PROVIDERS.md.
Check whether the capability already has a protocol.
Check whether another provider already exists.
Evaluate whether the new provider is actually needed.
Keep provider-specific code isolated.
Convert output into Autlead schemas.
Preserve provenance.
Handle provider-specific errors.
Add tests.
Test with real provider data.

Do not modify unrelated pipeline code simply to accommodate one provider.

24. Replacing a Provider

A provider should be replaceable without rewriting the pipeline.

Example:

BusinessDiscoveryProvider
        ↑
        │
   ┌────┴─────┐
   │          │
Google      Directory
Maps        Provider

Both implementations should produce the Autlead-defined structure expected by the pipeline.

25. Adding a New ETL Stage

Before adding a new transformation or extraction stage:

Read the relevant subsystem .md.
Check app/execution_plan.md.
Identify its input.
Identify its output.
Determine whether it belongs to Extract, Transform, or Load.
Check for an existing provider.
Define a schema if a new data boundary is required.
Add tests.
Keep the implementation focused.

Do not add an entire framework around a single operation.

26. Working on Models

Before modifying:

app/models/

read:

app/models/MODELS.md

Then determine whether the change belongs to:

domain/
persistence/
schemas/

Do not move models between these areas without understanding the model documentation.

27. Working on Transformations

Before modifying:

app/transform/

read:

app/transform/TRANSFORM.md

Then work within the appropriate transformation area.

Examples:

normalization/
deduplication/
entity_resolution/
analysis/
enrichment/
signal_extraction/
scoring/
qualification/

Do not implement future transformation stages simply because their folders already exist.

28. Working on Extraction

Before modifying:

app/extract/

read:

app/extract/EXTRACT.md

Extraction should focus on obtaining source data.

It should not become responsible for:

Lead scoring
Product strategy
Qualification
Outreach

Those belong elsewhere.

29. Working on Loading

Before modifying:

app/load/

read:

app/load/LOAD.md

Loading should focus on persistence and explicit outputs.

For the current base version:

PostgreSQL

is the primary load destination.

CSV/JSON exports can be generated from persisted data.

30. Working on Pipelines

Before modifying:

app/pipelines/

read:

app/pipelines/PIPELINES.md

A pipeline should compose capabilities.

Conceptually:

Pipeline
   ↓
Extract
   ↓
Transform
   ↓
Load

Keep provider implementations and transformation details outside the pipeline coordinator where practical.

31. Working on Policies

Before modifying:

app/policies/

read:

app/policies/POLICIES.md

Policies should contain business decisions rather than extraction mechanics.

Examples:

qualification
scoring rules
filtering
product-specific decisions

Do not bury these rules inside providers.

32. Working on State

Before modifying:

app/state/

read:

app/state/STATE.md

State infrastructure is a later phase.

Do not implement complex state management during the initial lead-collection phase.

When workers and asynchronous pipelines become necessary, state may be expanded to support:

pipeline state
checkpoints
retries
locks
recovery
transitions
33. Execution Plan Is Authoritative for Development Order

Before starting a new major feature, check:

app/execution_plan.md

The existence of a directory, module, or documentation file does not mean that feature is currently in scope.

For example, if:

app/intelligence/

or:

app/knowledge/

exists as a future area, do not implement it until the execution plan reaches that phase.

34. Current MVP

The first real milestone is:

Business Discovery Provider
        ↓
Extract
        ↓
Pydantic BusinessRecord
        ↓
Normalize
        ↓
Deduplicate
        ↓
Company
        ↓
PostgreSQL
        ↓
Lead Export

Success means Autlead can reliably produce a useful business/lead list.

Nothing more is required for MVP-0.

35. Future Expansion

After the base lead collector is reliable, the system can expand incrementally:

MVP-0
Discovery
 ↓
Normalize
 ↓
Deduplicate
 ↓
PostgreSQL
 ↓
Export


        ↓


Website Analysis
        ↓
Technology Detection
        ↓
Observations
        ↓
Signals
        ↓
Contacts
        ↓
Verification
        ↓
Scoring
        ↓
Qualification


        ↓


Celery
        ↓
Redis
        ↓
Workers
        ↓
State / Retry / Recovery


        ↓


Intelligence
        ↓
Knowledge
        ↓
Autply
        ↓
Outreach

Do not skip directly to the final architecture.

36. Agent Workflow

When beginning work:

Step 1 — Determine scope

Read:

app/execution_plan.md

Determine whether the requested work belongs to the current phase.

Step 2 — Read local documentation

If working in a subsystem, read its .md file.

Examples:

app/models/MODELS.md
app/extract/EXTRACT.md
app/load/LOAD.md
app/providers/PROVIDERS.md
app/transform/TRANSFORM.md
app/pipelines/PIPELINES.md
app/policies/POLICIES.md
app/state/STATE.md
Step 3 — Inspect existing implementation

Look for:

Existing provider
Existing schema
Existing model
Existing transformation
Existing tests
Existing conventions
Step 4 — Implement the smallest change

Do not redesign the subsystem unless the requirement genuinely requires it.

Step 5 — Test

Run the relevant tests first.

Then run:

uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
Step 6 — Update documentation when architecture changes

If the implementation changes the intended behavior or architecture of a subsystem, update its corresponding .md file.

37. Do Not Perform Unrelated Refactoring

While implementing a feature, do not automatically:

Rename unrelated files
Move directories
Introduce new architecture
Rewrite existing providers
Replace libraries
Create new abstractions
Clean up unrelated modules

Keep changes focused.

38. Dependency Rule

Before adding a dependency:

Ask:

Is it required by the current feature?
Is an existing dependency sufficient?
Does the project already have an open-source/provider solution?
Does it introduce unnecessary infrastructure?
Is it worth maintaining?

If the answer is unclear, do not add it yet.

Use uv for dependency management.

39. Data Safety

Autlead deals with business and potentially personal/contact information.

Do not collect or persist unnecessary personal information.

Preserve provenance.

Avoid putting sensitive or unnecessary personal information into logs.

Before automated outreach is introduced, compliance and suppression requirements must be implemented.

40. Architectural Decision Rule

When deciding whether to add an abstraction, ask:

Do we have a real need?

If there is:

one implementation
one use case
no foreseeable replacement
no testing benefit
no meaningful coupling problem

prefer the simpler implementation.

If there are:

multiple implementations
replaceable external dependencies
meaningful testing requirements
clear coupling problems

introduce the appropriate abstraction.

41. Golden Rules
Read the relevant .md before modifying a subsystem.
Read app/execution_plan.md before starting major work.
Follow the current project phase.
Do not implement future functionality early.
Use existing open-source projects for specialized extraction capabilities.
Keep providers replaceable.
Keep provider-specific code inside providers.
Use Pydantic at important data boundaries.
Keep ETL responsibilities clear.
PostgreSQL is the source of truth.
Prefer deterministic transformation where possible.
Preserve provenance.
Start with simple deduplication.
Do not introduce Celery/Redis until asynchronous execution is actually needed.
Do not introduce intelligence until the underlying lead data is reliable.
Do not build abstractions merely because they look architecturally sophisticated.
Prefer a modular monolith.
Make the smallest change that solves the actual requirement.
Test real behavior.
Update subsystem documentation when its intended architecture changes.
42. Final Mental Model

Autlead should evolve like this:

             CURRENT
                │
                ▼
       Reliable Lead Collector
                │
                ▼
        Reliable Lead Engine
                │
                ▼
       Asynchronous Processing
                │
                ▼
        Sales Intelligence
                │
                ▼
           Automation

The architecture should grow with the product.

Do not build the final system before the first useful system works.



### One important change from the previous `AGENTS.md`


I would **not** make `AGENTS.md` contain all the detailed rules for models, providers, transforms, state, etc. anymore.


Its job is primarily to tell an agent:


```text
"What am I working on?"
        ↓
"Which documentation must I read?"
        ↓
"What phase are we in?"
        ↓
"What architectural rules apply?"
        ↓
"Make the smallest correct change."

Then the specialized documentation owns the details:

app/
├── execution_plan.md       ← what to build / when
│
├── models/
│   └── MODELS.md           ← model architecture
│
├── extract/
│   └── EXTRACT.md          ← extraction
│
├── transform/
│   └── TRANSFORM.md        ← transformations
│
├── load/
│   └── LOAD.md             ← persistence/output
│
├── providers/
│   └── PROVIDERS.md        ← provider architecture
│
├── pipelines/
│   └── PIPELINES.md        ← pipeline composition
│
├── policies/
│   └── POLICIES.md         ← business rules
│
└── state/
    └── STATE.md            ← execution state

That is much more maintainable. AGENTS.md becomes the map; the subsystem .md files become the detailed manuals.