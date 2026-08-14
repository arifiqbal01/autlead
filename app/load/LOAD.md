# Autlead — Load Guide

## 1. Purpose

The Load layer is the final part of the ETL flow.

Its responsibility is simple:

> Take validated, transformed Autlead data and persist or export it to a destination.

The initial destinations are:

- PostgreSQL
- File exports

The Load layer does not:

- Extract data
- Analyze websites
- Discover contacts
- Calculate lead scores
- Generate intelligence
- Decide whether a lead is qualified

Those responsibilities belong to other parts of Autlead.

Conceptually:

    EXTRACT
       ↓
    TRANSFORM
       ↓
    LOAD
       ↓
    Destination


# 2. Current Load Structure

The current structure is:

    app/
    └── load/
        ├── __init__.py
        ├── postgres/
        │   └── __init__.py
        └── exports/
            └── __init__.py

There is intentionally no webhook loader.

Do not add additional load destinations until the project actually requires them.


# 3. PostgreSQL

PostgreSQL is the primary durable destination for Autlead data.

The typical flow is:

    Provider
       ↓
    Extracted data
       ↓
    Transform
       ↓
    Pydantic validation
       ↓
    Application model
       ↓
    PostgreSQL


# 4. What `load/postgres/` Does

`load/postgres/` contains code specifically concerned with loading ETL results into PostgreSQL.

For example:

    BusinessRecord
          ↓
    Transform
          ↓
    Company
          ↓
    PostgreSQL

Possible future modules may include:

    load/postgres/
        companies.py
        contacts.py
        observations.py
        signals.py
        intelligence.py

Do not create these files until their corresponding loading operations actually exist.


# 5. PostgreSQL Is the Source of Truth

PostgreSQL should contain the durable state of Autlead.

Redis, Celery, temporary files, provider caches, and in-memory objects should not become the authoritative source of lead data.

Conceptually:

    PostgreSQL
        ↓
    authoritative application state

    Redis
        ↓
    temporary task/broker infrastructure


# 6. SQLAlchemy

Autlead uses SQLAlchemy for PostgreSQL persistence.

The Load layer should work with the application's SQLAlchemy models and persistence abstractions rather than writing raw SQL throughout the ETL pipeline.

Typical flow:

    Transformed data
          ↓
    SQLAlchemy
          ↓
    PostgreSQL


# 7. Async PostgreSQL

Autlead uses asynchronous Python.

Database operations should therefore use SQLAlchemy's async support where the surrounding operation is asynchronous.

Conceptually:

    async pipeline
          ↓
    AsyncSession
          ↓
    PostgreSQL


# 8. Transactions

Database writes should use explicit transaction boundaries.

A successful load should result in a consistent database state.

Conceptually:

    begin transaction
          ↓
    write data
          ↓
    commit

If the operation fails:

    rollback


# 9. Idempotency

Loading should be idempotent where practical.

A retry should not blindly create duplicate records.

For example:

    Provider
       ↓
    BusinessRecord
       ↓
    Load
       ↓
    Company already exists
       ↓
    update/reuse

Database constraints should enforce important uniqueness rules.

Do not rely only on Python checks for data integrity.


# 10. Upsert

Some ETL operations naturally require upsert behavior.

Example:

    Existing company
          +
    newly extracted information
          ↓
    update existing record

rather than:

    insert duplicate company


Use upsert behavior when the business operation requires it.

Do not use upserts everywhere automatically.


# 11. Load vs Transform

The boundary should remain clear.

Transform:

    "What should this data look like inside Autlead?"

Load:

    "How do I persist this data?"


Example:

    Provider:
        "https://WWW.Example.com/"

        ↓

    Transform:
        domain = "example.com"

        ↓

    Load:
        save domain to PostgreSQL


The Load layer should not contain extensive normalization logic.


# 12. Load vs Models

`models/` defines the application's data structures.

`load/postgres/` handles persistence of those structures into the database.

Conceptually:

    models/
        ↓
    application data model

    load/postgres/
        ↓
    persistence operation

Keep those responsibilities separate.


# 13. Load vs Database Infrastructure

The Load layer should not become the entire database subsystem.

Database infrastructure may include:

- Engine creation
- Session management
- Connection configuration
- Transaction infrastructure
- Base model configuration

Those are database infrastructure concerns.

The Load layer deals with:

- What ETL data should be persisted
- Which persistence operation should occur
- How an ETL result is written to PostgreSQL


# 14. Load vs Repository

If repositories are used elsewhere in Autlead, do not automatically duplicate them inside `load/postgres/`.

For example, if the application already has a reliable:

    CompanyRepository

there is no reason for ETL loading to create a second competing:

    PostgresCompanyLoader

unless their responsibilities are genuinely different.

The architecture should avoid duplicate persistence abstractions.


# 15. First PostgreSQL Load

The first vertical slice should be deliberately small.

Example:

    Business Discovery
          ↓
    BusinessRecord
          ↓
    Transform
          ↓
    Company
          ↓
    PostgreSQL


Success means:

- Provider works
- Output is validated
- Transformation works
- Database connection works
- Company is persisted
- Duplicate handling works
- Tests exist


# 16. Loading Companies

A company load may eventually perform operations such as:

    create company
    update company
    find existing company
    associate source
    update timestamps


The exact implementation should be determined by the database model and actual pipeline requirements.


# 17. Loading Contacts

Contact data should only be persisted after it has passed the relevant transformation and validation stages.

Conceptually:

    ContactCandidate
          ↓
    Transform
          ↓
    Contact
          ↓
    PostgreSQL


A discovered contact should not automatically be treated as a verified contact.


# 18. Loading Observations

Observations are evidence collected by Autlead.

Example:

    Website analysis
          ↓
    Observation
          ↓
    PostgreSQL


An observation should retain useful provenance where appropriate:

    provider
    source
    observed_at


This allows Autlead to understand where information came from.


# 19. Loading Signals

Signals are derived from observations.

Example:

    Observations
          ↓
    Signal generation
          ↓
    Signal
          ↓
    PostgreSQL


The Load layer stores the signal.

It should not decide whether the signal should exist.


# 20. Loading Intelligence

Generated intelligence may eventually be persisted.

Example:

    IntelligenceResult
          ↓
    PostgreSQL


Useful metadata may include:

    product
    model
    provider
    prompt version
    generated_at


Only persist information that is actually useful for the application.


# 21. File Exports

`load/exports/` is for exporting Autlead data into external files.

Possible formats:

- CSV
- JSON
- Other formats when required

Example:

    PostgreSQL
        ↓
    Export loader
        ↓
    leads.csv


Exports are useful for:

- Manual inspection
- Analysis
- Backup
- Importing into another tool
- Sharing selected datasets


# 22. Exports Are Not the Primary Database

Files should not become the authoritative source of Autlead state.

The normal relationship is:

    PostgreSQL
        ↓
    Export
        ↓
    CSV / JSON


not:

    CSV
        ↓
    manually edited
        ↓
    primary application database


# 23. Export Scope

Exports should be explicit.

For example:

    export qualified leads

rather than:

    dump the entire database

This helps control:

- Data size
- Privacy
- Accidental exposure
- Processing time


# 24. Export Models

Exports should use application-level schemas or explicit export models.

Do not blindly serialize SQLAlchemy objects into CSV/JSON.

Example:

    Company
       ↓
    CompanyExport
       ↓
    CSV


This allows the exported structure to remain independent from the internal database representation.


# 25. Export Privacy

Exports may contain personal information.

Potentially sensitive fields include:

- Contact names
- Work email addresses
- Phone numbers
- LinkedIn URLs
- Other personal information

Exports should therefore be intentional and controlled.

Do not automatically export every field simply because it exists in PostgreSQL.


# 26. Load Errors

Load failures should be explicit.

Possible failures:

    database unavailable
    transaction failure
    constraint violation
    invalid transformed data
    serialization error
    disk write failure


The pipeline should know whether the operation can safely be retried.


# 27. Retry Safety

A database load may be retried when the operation is designed to be idempotent.

Example:

    Worker
       ↓
    PostgreSQL write
       ↓
    temporary failure
       ↓
    retry
       ↓
    same logical record


This is another reason to establish database constraints and deterministic identities.


# 28. Partial Loading

For batches, avoid assuming that every record succeeds.

Example:

    100 businesses
        ↓
    97 loaded
     3 failed


The pipeline should retain enough information to retry the failed records without unnecessarily repeating successful work.


# 29. Batch Loading

Batch operations may eventually improve performance.

Example:

    500 transformed companies
           ↓
       batch insert
           ↓
       PostgreSQL


Do not optimize for large batch operations before the normal single-record path is correct.

Correctness comes first.


# 30. Load Performance

Potential performance improvements include:

- Batch inserts
- Bulk operations
- Efficient upserts
- Appropriate indexes
- Connection pooling
- Avoiding unnecessary queries


Measure before optimizing.

Do not sacrifice maintainability for hypothetical performance problems.


# 31. Database Constraints

Important data integrity rules should be enforced by PostgreSQL.

Examples may include uniqueness for:

    normalized domain
    external source + external ID
    other stable business identifiers


The exact constraints should follow the actual data model.

Application-level checks are useful, but the database should protect important invariants.


# 32. Provenance

Loaded records should preserve important source information.

For example:

    company
       ├── source
       ├── external_id
       └── observed_at


This helps answer:

- Where did this company come from?
- Which provider found it?
- When was it collected?
- Can it be refreshed?


# 33. Load and Pipeline State

Pipeline execution state should be durable.

For example:

    PipelineRun
        ↓
    PostgreSQL

    PipelineStep
        ↓
    PostgreSQL


This allows workers to recover from failures and continue processing.

Pipeline state is application state, not temporary Celery state.


# 34. Celery Workers

Celery workers may execute load operations.

Example:

    Celery task
        ↓
    transform result
        ↓
    PostgreSQL load


The worker should call the appropriate application operation.

The Load implementation should not depend on Celery directly.


# 35. Load and Redis

Redis is not the primary destination for ETL data.

Redis may support:

- Celery broker
- Task coordination
- Temporary execution state


Durable lead data belongs in PostgreSQL.


# 36. Testing PostgreSQL Loads

Load operations should have database tests.

Test cases should include:

- Insert
- Update
- Duplicate handling
- Constraint violations
- Transaction rollback
- Partial failure
- Upsert behavior where applicable


Use a real PostgreSQL test environment for integration tests where database behavior matters.


# 37. Fake Loaders

For higher-level pipeline tests, a fake loader can be useful.

Example:

    FakeCompanyLoader
          ↓
    captures Company objects


This allows pipeline tests to verify:

    extraction
        ↓
    transformation
        ↓
    loading


without requiring PostgreSQL for every unit test.


# 38. Load Testing Boundaries

Test the Load layer separately from:

- Providers
- Website crawlers
- Search engines
- LLMs
- Celery infrastructure


Then test the complete pipeline separately.

This keeps failures easy to diagnose.


# 39. Adding a New Load Destination

When a new destination is required:

1. Identify the actual requirement.
2. Define the destination contract.
3. Determine which Autlead models are exported.
4. Add the destination-specific implementation.
5. Validate the output.
6. Add tests.
7. Integrate it into the appropriate pipeline.


Do not add a destination merely because it might be useful someday.


# 40. Current Scope

For the initial Autlead implementation, Load should remain focused on:

    PostgreSQL
        +
    File exports


Do not add:

- Webhooks
- Kafka
- S3
- Elasticsearch
- Data warehouse
- External CRM loaders

unless the project develops a real requirement for them.


# 41. Recommended Implementation Order

Implement Load in this order:

### Step 1

Database infrastructure:

    PostgreSQL
    SQLAlchemy
    AsyncSession
    migrations


### Step 2

First persistence path:

    BusinessRecord
        ↓
    Company
        ↓
    PostgreSQL


### Step 3

Duplicate handling:

    external ID
    domain
    other appropriate identity


### Step 4

Observations:

    Website/technology observations
        ↓
    PostgreSQL


### Step 5

Contacts:

    Contact
        ↓
    PostgreSQL


### Step 6

Signals:

    Signal
        ↓
    PostgreSQL


### Step 7

Additional application data:

    Scores
    Qualification
    Intelligence


### Step 8

Exports:

    PostgreSQL
        ↓
    CSV / JSON


Only implement each step when the corresponding upstream pipeline stage exists.


# 42. What Not to Build

Do not turn Load into a generic data platform.

Avoid prematurely implementing:

- Generic destination registry
- Generic ETL framework
- Generic repository factory
- Universal bulk loader
- Distributed data warehouse
- Event streaming system
- Webhook framework
- Complex export framework


Autlead needs reliable persistence, not a data-engineering platform.


# 43. Golden Rule

The Load layer has one simple job:

> Take valid Autlead data and put it where it needs to persist or be consumed.

The primary flow is:

    EXTRACT
       ↓
    TRANSFORM
       ↓
    LOAD
       ↓
    PostgreSQL


And when an explicit file export is needed:

    PostgreSQL / Pipeline Data
              ↓
          load/exports
              ↓
          CSV / JSON


Keep Load boring.

That is a good thing.

The complexity and value of Autlead should live in its:

- Extraction capabilities
- Transformations
- Evidence
- Signals
- Qualification
- Intelligence
- Pipeline orchestration

The Load layer should reliably persist those results without becoming another application inside the application.