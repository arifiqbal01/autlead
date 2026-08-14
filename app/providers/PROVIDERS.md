# Autlead — Providers Guide

## 1. Purpose

The `providers/` layer contains implementations of external capabilities used by Autlead.

Autlead should not reinvent extraction, search, crawling, verification, or LLM infrastructure when suitable open-source implementations already exist.

The provider architecture exists to isolate those external implementations from the rest of the application.

The core idea is:

    Autlead capability
          ↓
    Provider protocol
          ↓
    Provider implementation
          ↓
    External library / open-source repository / service


# 2. Current Provider Structure

The current structure is:

    app/
    └── providers/
        ├── contacts/
        ├── crawling/
        ├── discovery/
        ├── email/
        ├── llm/
        ├── reviews/
        ├── search/
        ├── technology/
        ├── verification/
        │
        ├── health.py
        ├── registry.py
        └── routing.py


These categories represent capabilities, not specific vendors.

For example:

    discovery/
        Google Maps provider
        directory provider
        other discovery provider

rather than:

    google_maps/
        ...

at the top level.

This keeps the application organized around what Autlead needs to do rather than around individual vendors.


# 3. Provider Philosophy

A provider is an implementation of a capability.

For example:

    Capability:
        Business Discovery

    Implementation:
        Google Maps open-source extractor

Another implementation may be:

    Capability:
        Business Discovery

    Implementation:
        Directory provider

Both should satisfy the same provider contract.

The pipeline should care about:

    "I need business discovery."

It should not care about:

    "I need Google Maps."


# 4. Providers Are Replaceable

A provider should be replaceable without rewriting the pipeline.

Example:

    Pipeline
       ↓
    BusinessDiscoveryProvider
       ↓
    GoogleMapsProvider

Later:

    Pipeline
       ↓
    BusinessDiscoveryProvider
       ↓
    DirectoryProvider


The pipeline remains unchanged.


# 5. Provider Protocols

Provider contracts should be defined using Python protocols where appropriate.

Example:

```python
from typing import Protocol

class BusinessDiscoveryProvider(Protocol):
    async def search(
        self,
        query: DiscoveryQuery,
    ) -> list[BusinessRecord]:
        ...

The protocol defines the capability.

It does not define the implementation.

6. Protocol Location

Protocols should live with the capability they describe or in the project's agreed protocol location.

For example:

providers/discovery/
    protocol.py
    google_maps.py

or, if the project later establishes a dedicated protocol convention:

protocols/
    discovery.py

Do not create protocol files merely for theoretical future providers.

A protocol should exist when the application needs a stable provider boundary.

7. Provider Categories

The current provider categories are:

contacts
crawling
discovery
email
llm
reviews
search
technology
verification

Each represents a different external capability.

8. Discovery Providers

providers/discovery/ handles discovering businesses or companies.

Possible implementations:

Google Maps/business extractor
Business directories
Public company datasets
Other suitable open-source discovery projects

Example:

DiscoveryQuery
      ↓
DiscoveryProvider
      ↓
BusinessRecord[]

The provider should return structured Autlead-compatible results.

It should not:

Score leads
Qualify companies
Generate sales messages
9. Crawling Providers

providers/crawling/ handles retrieving website content.

Possible implementations:

Crawl4AI
Playwright-based crawler
Other suitable open-source crawler

Potential output:

WebsiteContent

containing information such as:

URL
status code
HTML
text
links
metadata

The crawler obtains content.

Website analysis happens elsewhere.

10. Contact Providers

providers/contacts/ handles discovering potential contacts.

Possible sources:

Company websites
Public pages
Search results
Open-source contact discovery tools
Other suitable sources

Output should represent a candidate rather than automatically trusted contact information.

Example:

ContactCandidate

A candidate may later pass through verification.

11. Email Providers

providers/email/ handles email-related discovery or generation capabilities.

Examples may include:

Email pattern generation
Email discovery providers
Domain-based candidate generation

Keep email candidate generation separate from verification.

Example:

Contact
   ↓
email candidate
   ↓
verification provider
   ↓
verification result
12. Verification Providers

providers/verification/ handles verification capabilities.

The initial focus may be email verification.

Potential implementations:

Self-hosted open-source verifier
SMTP-based verification
Other verification provider

Output should be structured.

Example:

VerificationResult
    email
    status
    provider
    checked_at

Do not convert a provider's result directly into:

email_verified = True

without considering the verification result semantics.

13. Search Providers

providers/search/ handles search capabilities.

Possible implementations:

DuckDuckGo-based search
Search APIs
Other search engines
Self-hosted/open-source search implementations

Potential output:

SearchResult
    title
    url
    snippet
    source

The provider should hide search-engine-specific response formats.

14. Technology Providers

providers/technology/ handles technology detection.

Possible implementations:

Wappalyzer
Wappalyzer-compatible fingerprint databases
Other open-source technology detectors

Example:

Website
   ↓
TechnologyProvider
   ↓
TechnologyObservation

The provider detects technology.

It does not decide:

"WordPress means this is a good lead."

That belongs to signal/scoring logic.

15. Review Providers

providers/reviews/ handles discovery of public review information where a supported source and use case exist.

Possible sources may include:

Review platforms
Public review pages
Other permitted sources

The provider should return structured review information.

Example:

Review
    ├── source
    ├── rating
    ├── title
    ├── content
    └── observed_at

Review interpretation belongs to analysis/signals/intelligence.

16. LLM Providers

providers/llm/ provides access to language models.

The first implementation may be local Ollama.

Potential future implementations could include other local or remote models.

The intelligence layer should depend on:

LLMProvider

not directly on:

Ollama

Example:

class LLMProvider(Protocol):
    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        ...

The provider should handle model-specific details.

17. Provider vs Application Logic

Provider code should contain external-system concerns.

Good:

Google Maps response
    ↓
GoogleMapsProvider
    ↓
BusinessRecord

Bad:

GoogleMapsProvider
    ↓
calculate WebArtsy score
    ↓
generate pitch
    ↓
save lead

Keep the boundaries clear.

18. Provider vs Pipeline

The pipeline decides when a capability should execute.

Example:

Pipeline
   ↓
discover companies
   ↓
DiscoveryProvider

The provider decides how to execute the capability.

Example:

DiscoveryProvider
   ↓
open-source Maps extractor
   ↓
parse results
   ↓
return BusinessRecord
19. Provider vs Transform

Provider:

Convert external response into an initial Autlead-compatible result.

Transform:

Convert that result into the application's canonical representation and derive required fields.

Example:

Google Maps response
      ↓
GoogleMapsProvider
      ↓
BusinessRecord
      ↓
Transform
      ↓
normalized Company

Do not move all transformation logic into providers.

20. Provider vs Load

Providers should not directly own application persistence.

Avoid:

GoogleMapsProvider
    ↓
SQLAlchemy
    ↓
PostgreSQL

Prefer:

GoogleMapsProvider
    ↓
BusinessRecord
    ↓
Transform
    ↓
Load
    ↓
PostgreSQL

This keeps providers independently testable.

21. Provider Dependencies

Providers may depend on external open-source libraries.

For example:

GoogleMapsProvider
    ↓
open-source Maps extractor

or:

CrawlProvider
    ↓
Crawl4AI

The rest of Autlead should not import those external libraries directly unless there is a deliberate application-wide reason.

22. Open-Source First

Before writing a new provider implementation:

Search for existing open-source projects.
Check whether the project actually solves the required problem.
Evaluate maintenance status.
Check license compatibility.
Test output quality.
Check resource requirements.
Check Python compatibility.
Evaluate failure behavior.
Decide whether wrapping it is worthwhile.

The goal is not to collect repositories.

The goal is to use reliable components where they save development effort.

23. Provider Adapter

An adapter isolates the external implementation.

Example:

External library
      ↓
Provider adapter
      ↓
Autlead schema

The adapter may handle:

External API calls
Browser automation
Library-specific configuration
Provider-specific parsing
Provider-specific exceptions
Provider output conversion
24. Provider Output

Provider outputs should use explicit schemas.

Avoid returning arbitrary dictionaries throughout the application.

Prefer:

BusinessRecord(...)

over:

{
    "name": "...",
    "website": "...",
}

Pydantic should be used at important provider boundaries where validation provides value.

25. Provider-Specific Models

Provider-specific models are acceptable when external data is complex.

Example:

providers/discovery/google_maps/
    models.py
    provider.py

A provider-specific model can be converted into:

BusinessRecord

Do not allow provider-specific models to leak into unrelated application modules.

26. Provider Configuration

Provider configuration should contain only what that provider requires.

Examples:

timeout
API key
browser settings
provider-specific limits

Do not put unrelated application configuration inside provider modules.

27. Secrets

Secrets must never be hard-coded.

Examples:

API keys
Passwords
Tokens
Authentication cookies
Private credentials

Use application configuration/environment management.

28. Provider Health

providers/health.py is responsible for provider health checks.

A health check may answer:

Is the provider available?


Is the provider configured?


Is its required dependency installed?


Can a minimal operation succeed?

Example:

Google Maps provider
    ↓
health check
    ↓
available

Health checks should be lightweight.

Do not execute expensive discovery operations simply to determine provider health.

29. Provider Registry

providers/registry.py is responsible for managing known provider implementations when a registry is actually required.

Conceptually:

capability
    ↓
available providers

Example:

discovery
    ├── google_maps
    └── directory

The registry should remain simple.

Do not turn it into a complicated plugin framework.

30. Provider Routing

providers/routing.py determines which provider should be used when multiple implementations exist.

For example:

Business Discovery
      ↓
Routing
   ├── Provider A
   └── Provider B

Routing may eventually consider:

Capability
Provider availability
Geography
Source
Quality
Cost
Rate limits
Current provider health

Do not implement complex dynamic routing until multiple providers actually exist.

31. Explicit Provider Selection

Initially, explicit selection is preferable.

Example:

pipeline configuration
    ↓
discovery_provider = google_maps

This is easier to understand and debug than automatic provider routing.

32. Provider Fallback

Fallback can be introduced when multiple real providers exist.

Example:

Provider A
   ↓
temporary failure
   ↓
Provider B

Fallback should distinguish:

temporary provider failure

from:

valid empty result

An empty result does not necessarily mean the provider failed.

33. Provider Health and Routing

Health and routing should work together but remain separate.

Health:

Is this provider currently usable?

Routing:

Which provider should perform this operation?

This prevents routing logic from becoming a mixture of health checks, provider calls, and business logic.

34. Provider Retry

Retry behavior should be appropriate for the provider.

Retryable:

Timeout
Connection error
HTTP 429
Temporary 5xx

Usually not retryable:

Invalid query
Invalid configuration
Unsupported operation
Permanent 404

Provider-specific errors should be mapped into application-understandable error categories.

35. Provider Rate Limits

Different providers may have different limits.

Providers should expose or enforce appropriate constraints where required.

Do not assume all providers can handle the same concurrency.

36. Async Providers

Autlead uses asynchronous Python for I/O-heavy operations.

Prefer:

async def ...

when the underlying provider is asynchronous.

If an open-source implementation is synchronous, isolate it rather than rewriting the entire project.

For example:

async pipeline
      ↓
provider adapter
      ↓
thread/process boundary
      ↓
synchronous library
37. Provider Resource Management

Providers using browsers, network clients, or other expensive resources must manage them correctly.

Examples:

Close browser contexts
Close HTTP clients
Release connections
Avoid resource leaks
Bound concurrency

Resource lifecycle belongs to the provider implementation.

38. Provider Errors

Providers should expose meaningful errors.

Example conceptual hierarchy:

ProviderError
    ├── ProviderUnavailable
    ├── ProviderTimeout
    ├── ProviderRateLimited
    ├── ProviderInvalidRequest
    └── ProviderParseError

Keep the hierarchy small.

Do not create dozens of custom exceptions without a real need.

39. Provider Observability

Provider operations should produce structured logs where useful.

Example:

provider=google_maps
capability=discovery
operation=search
results=25
duration=8.4
status=success

Avoid logging unnecessary personal information.

Do not log complete contact records by default.

40. Provider Provenance

Provider results should preserve provenance when useful.

Potential metadata:

provider
source
external_id
collected_at

Example:

Company
   ├── source = google_maps
   ├── provider = google_maps_provider
   └── external_id = ...

This allows Autlead to understand where its data originated.

41. Provider Testing

Every provider should have appropriate tests.

Unit tests

Test:

Input conversion
Output conversion
Error mapping
Provider-specific parsing
Contract tests

Verify that the provider satisfies the expected capability protocol.

Integration tests

Run against the actual provider when practical.

Pipeline tests

Use fake providers so external services are not required.

42. Fake Providers

Fake providers are important for pipeline tests.

Example:

class FakeDiscoveryProvider:
    async def search(
        self,
        query: DiscoveryQuery,
    ) -> list[BusinessRecord]:
        return [...]

A complete pipeline can then be tested without:

Google Maps
Search engines
Websites
Email services
LLMs
43. Provider Contract Testing

If multiple providers implement the same capability, they should be tested against the same contract.

For example:

DiscoveryProvider Contract
      │
   ┌──┴───┐
   ↓      ↓
Maps    Directory
tests    tests

Both implementations should satisfy the same fundamental expectations.

44. Provider Quality

Provider selection should be based on measured quality.

Useful metrics:

coverage
accuracy
completeness
execution time
failure rate
rate-limit behavior
resource usage

Do not assume that an open-source provider is good simply because it exists.

45. Provider Replacement

Replacing a provider should ideally require changing:

provider registration/configuration

rather than:

pipeline logic
transformation logic
models
scoring
intelligence

This is one of the main reasons the provider boundary exists.

46. Adding a New Provider

When adding another implementation:

Identify the capability.
Search for suitable existing projects.
Evaluate the candidate.
Define/confirm the provider protocol.
Implement the adapter.
Map output to Autlead schemas.
Map provider-specific errors.
Add health behavior if necessary.
Add tests.
Register the provider if a registry is used.
Test against real examples.
Compare it with existing providers.

Do not modify unrelated pipeline logic.

47. Adding a New Capability

When Autlead needs a capability that does not currently exist:

Define the actual problem.
Search for existing open-source implementations.
Decide whether the capability belongs in providers/.
Define a small protocol.
Add the provider implementation.
Define the required Pydantic schemas.
Add tests.
Integrate it into the pipeline.

Do not build a provider abstraction before understanding the actual capability.

48. Provider Routing Evolution

The routing system should evolve gradually.

Stage 1

Explicit provider:

discovery → google_maps
Stage 2

Multiple providers:

discovery
   ├── google_maps
   └── directory
Stage 3

Basic routing:

preferred provider
   ↓
fallback provider
Stage 4

Measured routing:

provider health
+
source
+
geography
+
quality
↓
selected provider

Only reach later stages when actual requirements justify them.

49. Do Not Build a Provider Marketplace

The provider architecture is not intended to become a generic plugin marketplace.

Avoid prematurely implementing:

Dynamic package installation
Remote provider discovery
Provider marketplace
Automatic dependency installation
Generic plugin manifests
Complex provider lifecycle management

Autlead is an application, not a provider platform.

50. Do Not Put Business Logic in Providers

This is one of the most important rules.

A provider should answer:

How do we obtain this information?

It should not answer:

What does this information mean for the business?

For example:

Technology Provider
    ↓
WordPress detected

not:

Technology Provider
    ↓
WebArtsy opportunity = 80

Similarly:

Review Provider
    ↓
negative review found

not:

Autply lead score = 92
51. Do Not Couple Providers to Products

A provider should generally be reusable across products.

Bad:

GoogleMapsWebArtsyProvider
GoogleMapsAutplyProvider

Better:

GoogleMapsProvider

Then:

WebArtsy pipeline
      ↓
DiscoveryProvider


Autply pipeline
      ↓
DiscoveryProvider

Product-specific interpretation belongs in product pipelines, policies, signals, and intelligence.

52. Provider Lifecycle

A provider may have:

configuration
initialization
execution
cleanup
health check

Keep lifecycle management simple.

Use context managers or explicit lifecycle methods when resources require them.

53. Provider Dependencies

Keep provider-specific dependencies isolated where practical.

For example:

Crawl4AI
    ↓
crawling provider

The rest of Autlead should not need to import Crawl4AI directly.

This makes future replacement easier.

54. Provider Versioning

Track provider versions when they materially affect output.

For example:

provider = crawl4ai
provider_version = ...

Do not create a full provider version-management system unless reproducibility requires it.

55. Provider Data Freshness

Providers retrieve information at a point in time.

Important outputs may therefore have:

collected_at
observed_at

The pipeline/policy layer decides when data should be refreshed.

The provider simply performs the requested operation.

56. Provider Security

Treat provider output as untrusted external data.

Validate:

URLs
strings
identifiers
response structures
unexpected payloads

Do not execute arbitrary content returned by providers.

57. Provider Resource Costs

Even open-source providers have operational costs.

Examples:

CPU
RAM
browser processes
bandwidth
proxy usage
execution time
storage

Provider routing may eventually use resource/cost information.

Do not build cost optimization before there is enough real usage data.

58. Current Scope

The current provider architecture should support these capabilities:

Discovery
Crawling
Technology Detection
Search
Contact Discovery
Email Discovery
Email Verification
Reviews
LLM

The initial implementation should only activate capabilities required by the first working pipeline.

59. Recommended Implementation Order

Implement providers in the same order as the first useful ETL path.

1. Discovery
discovery/
    protocol
    first provider
2. Crawling
crawling/
    protocol
    first crawler
3. Technology Detection
technology/
    protocol
    first detector
4. Search
search/
    protocol
    first search provider
5. Contacts
contacts/
    protocol
    first contact provider
6. Verification
verification/
    protocol
    first verifier
7. LLM
llm/
    protocol
    Ollama provider
8. Reviews

Add when the Autlead pipeline actually needs review-based signals.

60. health.py

Keep health.py focused on checking provider availability.

Potential responsibilities:

provider configured
provider dependency available
provider reachable

Do not put provider routing or pipeline logic here.

61. registry.py

Keep registry.py focused on making available provider implementations discoverable by the application.

Conceptually:

capability
   ↓
provider implementations

Avoid turning the registry into a large dependency-injection framework.

62. routing.py

Keep routing responsible for provider selection.

It may eventually implement:

preferred provider
fallback provider
health-aware selection
capability-specific selection

Routing should not perform the actual extraction itself.

63. Golden Rule

The provider layer should make Autlead replaceable without making it complicated.

The desired architecture is:

Pipeline
   ↓
Capability
   ↓
Protocol
   ↓
Provider
   ↓
Open-source implementation
   ↓
External source

Autlead owns:

Capability contracts
Pydantic boundaries
Provider composition
Error handling
Provenance
Routing decisions
Pipeline integration

External projects own:

Specialized extraction
Crawling
Search
Detection
Verification
Model inference

The goal is not to build every tool ourselves.

The goal is to build a reliable system that can combine, replace, and evolve those tools without rewriting Autlead's core pipeline.