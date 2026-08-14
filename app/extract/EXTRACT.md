# Autlead — Extraction Guide

## 1. Purpose

The Extraction layer is responsible for obtaining raw information from external sources.

Its responsibility is intentionally narrow:

> Get useful data from an external source and return it in a known format.

Extraction does not decide:

- Whether a company is a good lead
- Whether a signal is important
- Whether a contact should be contacted
- How a lead should be scored
- What message should be written

Those decisions belong to other parts of Autlead.

Conceptually:

    External Source
          ↓
      Provider
          ↓
      Extraction
          ↓
    Pydantic Schema
          ↓
    Normalization
          ↓
    Persistence / Pipeline

---

# 2. Extraction Philosophy

Autlead should not reinvent extraction logic when a reliable open-source implementation already exists.

The project should prefer:

    Existing open-source project
              ↓
        Provider adapter
              ↓
          Autlead schema

instead of:

    Autlead
       ↓
    Reimplement scraper/API/client/parser
       ↓
    Maintain it forever

The extraction layer is primarily an **integration layer around useful existing capabilities**.

---

# 3. Use Existing Open-Source Providers

For individual extraction capabilities, search for mature open-source projects first.

Examples of potential capabilities:

- Business discovery
- Google Maps/business extraction
- Website crawling
- Search
- Technology detection
- Contact discovery
- Email verification
- Review extraction
- Job-posting discovery

A provider may internally use:

- Playwright
- HTTP clients
- browser automation
- HTML parsing
- APIs
- third-party libraries
- another open-source repository

Autlead does not need to reproduce those internals.

---

# 4. Provider Adapter

Autlead should isolate external implementations behind provider interfaces/protocols.

Conceptually:

    Pipeline
       ↓
    Capability
       ↓
    Provider Protocol
       ↓
    Provider Adapter
       ↓
    Open-source implementation
       ↓
    External Source

For example:

    BusinessDiscoveryProvider
          ↓
    GoogleMapsProvider
          ↓
    open-source Maps extractor

The rest of Autlead should not depend directly on the underlying repository.

---

# 5. One Capability, Multiple Providers

Autlead should not depend on a single provider when multiple useful implementations exist.

Example:

    Business Discovery
          │
      ┌───┼──────────────┐
      │   │              │
    Maps  Directory   Search
      │   │              │
 Provider A              Provider B

All providers should eventually produce the same normalized capability output.

For example:

    BusinessDiscoveryProvider
             ↓
        BusinessRecord

The pipeline does not need to know which implementation produced the record.

---

# 6. Do Not Build Provider Abstraction Prematurely

Provider independence does not mean building a huge provider framework on day one.

Start with:

    Protocol
       ↓
    One real provider

Add another implementation only when there is a real reason:

- Better coverage
- Provider failure
- Geographic limitations
- Rate limits
- Data quality
- Different source
- Different extraction method

Avoid building:

- Generic provider registries
- Dynamic plugin systems
- Automatic provider marketplaces
- Complex routing engines

before they are necessary.

---

# 7. Extraction vs Normalization

Extraction returns what the provider found.

Normalization converts it into Autlead's canonical representation.

Example:

    Provider
       ↓
    "Example Business"
    "https://www.example.com/"
    "+31 ..."
       ↓
    BusinessRecord
       ↓
    Normalization
       ↓
    normalized domain = example.com

Do not mix extensive normalization logic into provider adapters.

---

# 8. Extraction vs Analysis

Extraction obtains information.

Analysis interprets or derives information from that information.

Example:

    Website crawler
         ↓
    HTML
         ↓
    Extraction

Then:

    HTML
      ↓
    Technology detection
      ↓
    Observation

Or:

    HTML
      ↓
    SEO analysis
      ↓
    Observation

The crawler should not decide that a company is a good WebArtsy lead.

---

# 9. Extraction Output

Provider outputs should be converted into explicit Pydantic schemas at the application boundary.

Example:

```python
class BusinessRecord(BaseModel):
    name: str
    website: str | None = None
    phone: str | None = None
    address: str | None = None
    country: str | None = None
    external_id: str | None = None


The exact fields should evolve from actual provider requirements.

Do not create a universal business schema containing every field imaginable.

10. Raw Provider Data

Sometimes the provider returns information that does not fit the canonical model.

Do not immediately discard useful raw data.

Conceptually:

Provider
   ↓
Raw Provider Record
   ↓
Canonical Pydantic Model
   ↓
PostgreSQL

Raw provider data can be useful for:

Debugging
Reprocessing
Provider comparison
Data-quality investigation
Future extraction improvements

However, raw data should not automatically be persisted forever.

Retention should be based on actual requirements and privacy considerations.

11. Provider-Specific Models

Provider-specific schemas may be appropriate when the external structure is complex.

Example:

providers/
    google_maps/
        models.py
        adapter.py

Provider model:

GoogleMapsBusiness

can then be converted into:

BusinessRecord

This keeps external provider structures isolated.

Do not expose GoogleMapsBusiness throughout the application.

12. Extraction Protocols

Protocols define capabilities rather than implementations.

Example:

from typing import Protocol


class BusinessDiscoveryProvider(Protocol):
    async def search(
        self,
        query: DiscoveryQuery,
    ) -> list[BusinessRecord]:
        ...

The protocol answers:

What can this provider do?

It does not answer:

How does this provider do it?

13. Suggested Capability Protocols

Potential protocols may include:

BusinessDiscoveryProvider
WebsiteCrawlerProvider
TechnologyDetectionProvider
SearchProvider
ContactDiscoveryProvider
EmailVerificationProvider
ReviewDiscoveryProvider
JobDiscoveryProvider
LLMProvider

Do not implement all protocols immediately.

Add a protocol when the corresponding capability is introduced.

14. Async Extraction

Autlead uses asynchronous Python for I/O-heavy extraction.

Typical operations include:

HTTP requests
Browser automation
Website crawling
Search
Provider APIs
DNS/network operations

Use:

async def ...

where the underlying operation is asynchronous.

Do not force asynchronous wrappers around inherently synchronous code without a reason.

15. Blocking Libraries

Some open-source extraction repositories may be synchronous.

Do not rewrite a mature library simply to make it async.

If necessary, isolate blocking work.

Conceptually:

Async Pipeline
      ↓
Provider Adapter
      ↓
Blocking library
      ↓
Thread/process boundary

The blocking implementation should remain isolated from the rest of the async pipeline.

16. Concurrency

Extraction often benefits from controlled concurrency.

Example:

100 websites
      ↓
worker pool
      ↓
5–10 concurrent requests
      ↓
results

Do not launch unlimited concurrent requests.

Concurrency should respect:

Provider limits
Target website limits
Local resources
Network capacity
Browser resource usage
17. Rate Limiting

Each provider may have different limitations.

The extraction layer should support controlled request rates when required.

Do not assume:

async = unlimited concurrency

Instead:

async
  +
bounded concurrency
  +
rate limiting
  =
controlled extraction

Provider-specific rate limits belong close to the provider implementation.

Global business decisions do not.

18. Timeouts

Every network extraction operation should have a reasonable timeout.

Avoid:

await provider.search(...)

with no protection against indefinite waiting.

Timeouts should produce a controlled failure that the pipeline can handle.

19. Retries

Retry only failures that are plausibly temporary.

Good retry candidates:

Timeout
Connection reset
HTTP 429
Temporary 5xx
Temporary provider outage

Do not repeatedly retry:

Invalid URL
Invalid query
Unsupported operation
Permanent 404
Malformed input

Use bounded retries with backoff.

20. Extraction Errors

Extraction errors should be classified where practical.

Conceptually:

ExtractionError
├── Timeout
├── RateLimited
├── ProviderUnavailable
├── InvalidInput
├── NotFound
└── ParseError

The exact hierarchy should remain small.

Do not build a huge custom exception framework unless actual provider diversity requires it.

21. Partial Results

Providers may return partial data.

Example:

Company name ✓
Website ✓
Phone ✗
Address ✓

Do not automatically discard the entire record.

Return the useful information and preserve the missing fields as missing.

Partial data is often valuable during ETL.

22. Provider Failure

A provider failure should not necessarily fail the entire pipeline.

Example:

Company A → extracted
Company B → provider timeout
Company C → extracted

Company B can be retried later.

The pipeline should continue processing other independent records where appropriate.

23. Provider Fallback

When multiple providers exist:

Provider A
    ↓
failure
    ↓
Provider B

may be used.

However, fallback should be controlled by a policy rather than arbitrary provider-specific logic.

The provider layer reports capability/failure.

The application/pipeline decides whether another provider should be attempted.

24. Extraction Provenance

Every meaningful extracted record should ideally be traceable to:

source
provider
external ID
collected_at

Example:

Source:
    Google Maps


Provider:
    google_maps_provider


External ID:
    abc123


Collected:
    2026-08-14T...

This is important for debugging and data quality.

25. External IDs

When a provider supplies a stable external identifier, preserve it.

Examples:

Google Maps place ID
Directory business ID
Review-site company ID

External IDs can help with:

Deduplication
Repeated extraction
Provider synchronization
Tracking source records

Do not assume every provider has a stable identifier.

26. URL Handling

URLs should be treated carefully.

Extraction may return:

http://example.com
https://example.com/
https://www.example.com/about

The extraction layer should preserve the provider's URL accurately.

Canonicalization belongs in normalization.

Do not silently mutate provider output inside the extractor unless required to make the provider work.

27. Website Extraction

Website extraction may include:

HTML
Text
Markdown
Links
Metadata
HTTP information

The crawler should return structured extraction output.

Example:

WebsiteContent
    url
    status_code
    html
    text
    links
    title

Only add fields when actual downstream processing requires them.

28. Browser-Based Extraction

Some sources require browser automation.

Potential tools:

Playwright
Existing open-source browser extractors
Other specialized repositories

Browser providers should encapsulate:

Browser startup
Context creation
Navigation
Waiting
Extraction
Browser cleanup

The pipeline should not manage browser internals.

29. Browser Resource Management

Browser extraction is expensive.

Providers should ensure:

Browser contexts are closed
Pages are closed where appropriate
Exceptions do not leak resources
Concurrency is bounded
Browser processes are not unnecessarily recreated

Prefer reusable browser infrastructure when the actual workload justifies it.

Do not optimize browser lifecycle prematurely.

30. Search Extraction

Search providers may be used for:

Company discovery
Contact discovery
Public professional information
Supporting evidence

Search results should be normalized into a common representation.

Example:

SearchResult
    title
    url
    snippet
    source

Do not let search-engine-specific response formats leak into application code.

31. Contact Extraction

Contact extraction should produce candidates, not automatically trusted contacts.

Flow:

Search / Website
       ↓
ContactCandidate
       ↓
Validation
       ↓
Verification
       ↓
Contact

The extractor should report what it found.

Qualification and verification happen later.

32. Email Extraction

Email extraction and email verification are different capabilities.

Extraction:

What email addresses can we find or infer?

Verification:

Is this address likely deliverable?

Do not combine them into one provider.

Conceptually:

Email Discovery
      ↓
candidate email
      ↓
Email Verification
      ↓
verification result
33. Email Permutations

Generating likely email patterns can be treated as deterministic transformation logic.

Example:

john.doe@example.com
john@example.com
jdoe@example.com
johndoe@example.com

Do not treat generated permutations as verified emails.

They remain candidates until verification.

34. Technology Extraction

Technology detection should be treated as an extraction/analysis capability.

Possible providers:

Wappalyzer-based implementations
BuiltWith-compatible open-source approaches
Custom fingerprint databases
Other open-source detectors

Output should be normalized.

Example:

TechnologyObservation
    technology = WordPress
    category = CMS
    confidence = ...

The technology detector should not decide whether WordPress is good or bad for a lead.

35. Extraction and Signals

Extraction:

WordPress detected

Signal generation:

Potential WordPress modernization opportunity

Keep the boundary clear.

36. Extraction and Scoring

Extraction should never directly calculate the lead score.

Bad:

GoogleMapsProvider
    → score = 72

Correct:

GoogleMapsProvider
    ↓
BusinessRecord
    ↓
Observation
    ↓
Signal
    ↓
Scoring Policy
    ↓
LeadScore
37. Extraction and Intelligence

Extraction provides evidence.

Intelligence interprets it.

Bad:

Crawler
    → "This business needs a new website."

Correct:

Crawler
    → HTML / content


Analyzer
    → observations


Signal layer
    → opportunity signal


Intelligence
    → business interpretation
38. Extraction and Persistence

Providers should not directly manage the application's database.

Bad:

GoogleMapsProvider
    ↓
SQLAlchemy session
    ↓
Company

Prefer:

GoogleMapsProvider
    ↓
BusinessRecord
    ↓
Pipeline/application logic
    ↓
Repository/persistence
    ↓
PostgreSQL

This keeps extraction reusable and testable.

39. Extraction and Celery

Providers should not depend on Celery.

Bad:

GoogleMapsProvider
    ↓
Celery task

inside the provider implementation.

Prefer:

Pipeline
    ↓
Celery task
    ↓
Provider

Celery executes the operation.

The provider remains a normal capability implementation.

40. Extraction Package Organization

The exact directory structure may evolve, but the conceptual organization should remain modular.

Example:

providers/
    business/
        protocol.py
        google_maps.py
        directory.py


    website/
        protocol.py
        crawl4ai.py


    technology/
        protocol.py
        wappalyzer.py


    search/
        protocol.py
        duckduckgo.py


    contacts/
        protocol.py
        ...


    verification/
        protocol.py
        ...

Do not create a directory for a capability until that capability actually exists.

41. Provider Adapter Responsibilities

A provider adapter should:

Accept a known input.
Call the external implementation.
Handle provider-specific behavior.
Convert output into Autlead schemas.
Raise meaningful errors.
Return structured results.

It should not:

Score leads
Send emails
Decide qualification
Modify unrelated database records
Generate sales pitches
42. Provider Adapter Example

Conceptually:

class GoogleMapsProvider:
    async def search(
        self,
        query: DiscoveryQuery,
    ) -> list[BusinessRecord]:


        raw_results = await self.client.search(
            query=query.query,
            location=query.location,
        )


        return [
            self._to_business_record(result)
            for result in raw_results
        ]

The important boundary is:

raw provider data
        ↓
BusinessRecord
43. Extraction Configuration

Only configuration required by the provider should be introduced.

Examples may include:

timeout
concurrency
provider-specific credentials
browser settings

Do not put unrelated application configuration into extraction providers.

Follow the project's principle of adding configuration only when required.

44. Secrets

Provider credentials must not be hard-coded.

Use environment/configuration management.

Do not put:

API keys
passwords
tokens
cookies

in source code.

Do not commit secrets to Git.

45. Provider Dependencies

External open-source projects should be evaluated before adoption.

Consider:

License
Maintenance activity
Python compatibility
Dependency quality
Community adoption
Extraction quality
Resource usage
Known limitations
Terms of use of the target source

Do not adopt a repository solely because it has many GitHub stars.

46. Forking Open-Source Projects

Prefer consuming an existing project through its supported interface.

Fork only when necessary.

Reasons may include:

Required bug fix
Unsupported feature
Important performance problem
Project abandonment
Security issue

If a fork becomes necessary, document:

Original repository
Commit/version
Reason for fork
Local modifications

Do not silently maintain an unknown copy of an external project.

47. Provider Evaluation

Before integrating a provider, test it against real examples.

Evaluate:

coverage
accuracy
stability
speed
resource usage
failure behavior
output quality

Use a small test dataset.

Do not build the entire pipeline around a provider before validating it.

48. Multiple Providers

If multiple providers implement the same capability, compare them using the same input dataset.

Example:

Provider A
    ↓
100 businesses


Provider B
    ↓
100 businesses


Compare:
    coverage
    duplicates
    accuracy
    execution time

Provider selection should be based on evidence.

49. Extraction Quality

Track extraction quality.

Useful metrics:

records requested
records returned
records valid
records incomplete
duplicates
provider errors
timeouts
average duration

For specific capabilities:

website discovery success rate
contact discovery success rate
technology detection accuracy
email candidate quality
50. Extraction Observability

Log meaningful provider events.

Example:

provider=google_maps
operation=search
query="ecommerce stores"
location="Amsterdam"
results=48
duration=12.3
status=success

Avoid logging unnecessary sensitive information.

Do not log complete contact records or email addresses by default.

51. Extraction Testing

Every provider should have tests at appropriate levels.

Unit tests

Test:

Input conversion
Output conversion
Normalization helpers
Error mapping
Contract tests

Verify the provider implements its protocol correctly.

Integration tests

Run against the actual open-source provider when practical.

Pipeline tests

Use fake providers.

52. Fake Extraction Providers

Example:

class FakeBusinessDiscoveryProvider:
    async def search(
        self,
        query: DiscoveryQuery,
    ) -> list[BusinessRecord]:
        return [
            BusinessRecord(
                name="Example Business",
                website="https://example.com",
            )
        ]

This lets the pipeline be tested without external websites or services.

53. Extraction Caching

Caching may become useful for expensive extraction.

Potential examples:

Website pages
Search results
Technology scans
Provider responses

However, caching introduces freshness and invalidation problems.

Do not add a generic extraction cache until repeated work is measurable.

54. Extraction Scheduling

Extraction can be scheduled through Celery.

Examples:

Daily discovery
Weekly website re-analysis
Periodic contact verification

Scheduling belongs to orchestration infrastructure.

The provider itself should not contain scheduling logic.

55. Extraction Reprocessing

A previous extraction should be repeatable where useful.

Example:

Company
    ↓
Website extraction v1
    ↓
New crawler/provider
    ↓
Website extraction v2

The pipeline should be able to re-run a specific capability without rebuilding unrelated company data.

56. Extraction Freshness

Not every source needs to be extracted at the same frequency.

Examples:

Company identity
    → relatively stable


Website technology
    → periodically refreshed


Contact role
    → may become stale


Email verification
    → refresh when necessary

Freshness policies belong to pipeline/policy layers.

The extractor only performs the requested extraction.

57. Compliance and Source Restrictions

Extraction must respect the legal and technical constraints applicable to the source and use case.

Before integrating a source, consider:

Terms of service
Robots/access restrictions where relevant
Rate limits
Authentication requirements
Data protection requirements
Licensing
Permitted downstream use

Open-source extraction code does not automatically mean the target source permits every use of the extracted data.

The engineering team should document important source-specific risks.

58. Do Not Depend on Scraping Alone

Autlead should support multiple acquisition mechanisms.

Possible sources:

Open datasets
Directories
Public APIs
Business discovery
Search
Websites
Review sources
Job sources

A provider should be selected based on the required capability and source.

Do not force every source through browser scraping.

59. Extraction Roadmap

Recommended implementation order:

Phase 1

Business discovery.

BusinessDiscoveryProvider
        ↓
BusinessRecord
Phase 2

Website extraction.

WebsiteCrawlerProvider
        ↓
WebsiteContent
Phase 3

Technology detection.

TechnologyProvider
        ↓
TechnologyObservation
Phase 4

Search/contact discovery.

SearchProvider
        ↓
ContactCandidate
Phase 5

Email verification.

VerificationProvider
        ↓
VerificationResult

Additional providers should be added according to actual pipeline requirements.

60. What Not to Build

Do not prematurely build:

Custom Google Maps scraper if a suitable open-source provider exists
Custom browser automation framework
Custom HTML parser
Generic scraping framework
Generic provider marketplace
Universal extraction DSL
Complex proxy manager
Distributed crawling cluster
Custom search engine
Custom email verification engine

Build the missing parts.

Reuse mature open-source extraction capabilities where appropriate.

61. Extraction Decision Process

When a new extraction requirement appears:

New capability needed
        ↓
Search existing open-source solutions
        ↓
Evaluate candidates
        ↓
Test against real examples
        ↓
Select provider
        ↓
Create adapter
        ↓
Map output to Pydantic schema
        ↓
Integrate with pipeline

Only write custom extraction logic when:

No suitable provider exists
Existing providers fail the requirement
The required logic is genuinely small
Maintaining custom logic is justified
62. Golden Rule

Autlead should own the contracts and orchestration, not unnecessarily own every extraction implementation.

The preferred architecture is:

External Source
      ↓
Open-source implementation
      ↓
Autlead Provider Adapter
      ↓
Protocol
      ↓
Pydantic Schema
      ↓
ETL Pipeline
      ↓
PostgreSQL

Autlead's engineering effort should focus on the parts that create its actual value:

Normalization
Evidence
Signals
Qualification
Intelligence
Product-specific strategy
Provider composition
Reliable ETL orchestration

Do not reinvent wheels when a good wheel already exists.