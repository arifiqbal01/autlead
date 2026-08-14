# Autlead — State Guide

## 1. Purpose

The `state/` layer manages the runtime state of Autlead pipelines.

Autlead is not a simple linear script.

A pipeline may:

- Process thousands of records
- Run through Celery workers
- Execute asynchronously
- Fail partway through
- Be retried
- Resume after interruption
- Run concurrently
- Encounter temporary provider failures
- Need to continue from the last successful stage

The State layer exists to make those situations manageable.

Its fundamental responsibility is:

> Know where pipeline work is, what has completed, what is safe to retry, and how execution can recover.


# 2. Current Structure

The current structure is:

    app/
    └── state/
        ├── checkpoints/
        ├── locks/
        ├── pipeline/
        ├── recovery/
        ├── retries/
        ├── transitions/
        │
        ├── __init__.py
        ├── checkpoints.py
        ├── locks.py
        ├── pipeline.py
        ├── recovery.py
        ├── retries.py
        └── transitions.py


There are two levels:

    state/
        public coordination modules

    state/<category>/
        detailed implementations


The exact implementation should grow only when the corresponding requirement appears.


# 3. Why State Exists

Without explicit state management, a failed pipeline can become difficult to recover.

Example:

    Extract 1000 companies
          ↓
    Transform
          ↓
    Process record 437
          ↓
    worker crashes


Without state:

    "Where were we?"

With state:

    pipeline run
        ↓
    record 437
        ↓
    last successful stage
        ↓
    retry/resume


# 4. State Is Not Business Data

State should not replace the application's domain data.

For example:

    Company
    Contact
    Signal
    LeadScore

are application data.

Whereas:

    PipelineRun
    PipelineStep
    Checkpoint
    RetryState

are execution state.


Keep the distinction clear.


# 5. State Is Not Celery

Celery manages task execution.

State manages Autlead's durable understanding of pipeline execution.

Celery may know:

    task is queued
    task is running
    task failed


Autlead may need to know:

    pipeline run
    company being processed
    current stage
    completed stages
    checkpoint
    retry count
    recovery status


Do not rely exclusively on Celery's internal task state for application recovery.


# 6. PostgreSQL as Durable State

Important pipeline state should eventually be persisted durably.

Example:

    Celery
       ↓
    worker
       ↓
    state update
       ↓
    PostgreSQL


Redis can support Celery execution, but Redis should not automatically become the authoritative source for long-lived pipeline state.


# 7. Pipeline State

`pipeline/` represents the state of a pipeline execution.

A pipeline run may have states such as:

    pending
    running
    paused
    completed
    failed
    cancelled


The exact state machine should be defined explicitly rather than allowing arbitrary strings throughout the application.


# 8. Pipeline Run

A pipeline run represents one execution of a pipeline.

Example:

    WebArtsy Discovery
    Run #1024


It may contain:

    pipeline name
    pipeline version
    start time
    end time
    status
    configuration
    counters
    failure information


The exact fields belong to the application's models.


# 9. Pipeline Stages

A pipeline may contain stages such as:

    discovery
    normalization
    deduplication
    analysis
    enrichment
    scoring
    qualification
    loading


A run should be able to determine which stage is currently being executed.


# 10. State Transitions

`transitions/` defines valid movement between states.

Example:

    pending
       ↓
    running
       ↓
    completed


Failure:

    running
       ↓
    failed


Retry:

    failed
       ↓
    retrying
       ↓
    running


Invalid transitions should be rejected.

For example:

    completed
       ↓
    running

should not happen accidentally.


# 11. State Machine

State transitions should be explicit.

Conceptually:

    PENDING
       │
       ▼
    RUNNING
      /   \
     /     \
    ▼       ▼
 FAILED   COMPLETED
    │
    ▼
 RETRYING
    │
    ▼
 RUNNING


The actual state graph should reflect the real pipeline lifecycle.


# 12. Transition Rules

A transition should have a clear reason.

Example:

    RUNNING → FAILED
        reason:
        unrecoverable pipeline error


or:

    FAILED → RETRYING
        reason:
        retry policy allows another attempt


Do not modify state directly from arbitrary application code when a controlled transition is required.


# 13. Checkpoints

`checkpoints/` allows Autlead to record meaningful progress.

A checkpoint answers:

> What work has safely completed up to this point?


Example:

    Company 123

    discovery       ✓
    normalization   ✓
    analysis        ✓
    enrichment      ✗


A checkpoint may allow processing to resume at:

    enrichment


instead of starting again from:

    discovery


# 14. Checkpoints Are Not Every Function Call

Do not checkpoint every line of code.

Checkpoints should represent meaningful recovery boundaries.

Good:

    discovery completed
    website analysis completed
    contact enrichment completed
    loading completed


Bad:

    function_a completed
    function_b completed
    loop_iteration_17 completed


Too many checkpoints create unnecessary complexity.


# 15. Checkpoint Granularity

Checkpoint granularity depends on the cost of the operation.

Cheap operation:

    process again


Expensive operation:

    save checkpoint


For example, if crawling a website is expensive, completing the crawl may be a useful checkpoint.


# 16. Idempotent Stages

Checkpoints work best when stages are idempotent.

Example:

    analyze website
        ↓
    same input
        ↓
    same logical result


If a stage can safely run twice, recovery becomes much simpler.


# 17. Non-Idempotent Operations

Some operations may not be safe to repeat.

Examples may include:

    sending an email
    creating an external resource
    charging money


These require stronger state and idempotency protections.

Autlead should be particularly careful before retrying operations with external side effects.


# 18. Locks

`locks/` protects shared resources from conflicting concurrent operations.

Example:

    Worker A
       ↓
    process company 123


At the same time:

    Worker B
       ↓
    process company 123


Without coordination, both workers may perform the same operation.

A lock can prevent that.


# 19. Lock Scope

Locks should be as narrow as practical.

Possible scopes:

    company
    pipeline run
    pipeline stage
    provider resource


Avoid global locks unless absolutely necessary.

A global lock can destroy concurrency.


# 20. Lock Lifetime

Locks should have a controlled lifetime.

A lock should not remain permanently held if a worker crashes.

Where appropriate, use:

    lease
    timeout
    expiration


This allows another worker to recover abandoned work.


# 21. Lock Ownership

A lock should identify its owner where necessary.

For example:

    worker/task ID


This helps diagnose:

    who currently owns the lock?


and:

    which worker abandoned it?


# 22. Redis Locks

Redis may be useful for short-lived distributed locks.

However, lock semantics must be carefully designed.

Do not use a simple:

    SET key

and assume the problem is solved.

Consider:

- Ownership
- Expiration
- Release safety
- Worker crashes
- Race conditions


# 23. PostgreSQL Locks

Some state operations may instead use PostgreSQL transaction/locking mechanisms.

The choice should depend on the operation.

Do not force every lock through Redis.


# 24. Recovery

`recovery/` handles situations where execution does not complete normally.

Examples:

    worker crash
    process restart
    provider outage
    database connection failure
    task timeout
    partial pipeline failure


Recovery should determine what can safely continue.


# 25. Recovery Principle

Recovery should prefer:

    resume from known-safe state


rather than:

    start everything from zero


when doing so is safe.


# 26. Recovery Example

Suppose:

    discovery ✓
    normalization ✓
    analysis ✓
    enrichment ✗


After a worker crash:

    recovery
        ↓
    inspect checkpoint
        ↓
    resume enrichment


The previous completed work does not need to be repeated unnecessarily.


# 27. Recovery Must Be Conservative

Never assume a stage completed merely because a worker started it.

For example:

    enrichment started
        ↓
    worker crashed
        ↓
    state = completed   ❌


Completion should only be recorded after the operation has reached its defined success point.


# 28. Atomic State Updates

Where practical, important state updates should occur atomically with the operation they describe.

For example:

    write data
       +
    mark stage completed


should be coordinated so the system does not incorrectly believe the data exists when it does not.


# 29. Recovery After Database Failure

If a database transaction fails:

    database write
        ↓
    rollback
        ↓
    stage not completed


The worker may then retry according to the applicable retry policy.


# 30. Recovery After Provider Failure

If an external provider temporarily fails:

    provider
       ↓
    timeout
       ↓
    retry policy
       ↓
    retry


If the provider remains unavailable:

    retry limit reached
       ↓
    stage failed
       ↓
    recovery/inspection


Do not endlessly retry.


# 31. Retries

`retries/` defines retry behavior for recoverable failures.

Not every failure should be retried.

Typical retryable failures:

    timeout
    temporary network failure
    HTTP 429
    temporary HTTP 5xx
    temporary database connectivity issue


Typical non-retryable failures:

    invalid input
    invalid configuration
    authentication failure
    malformed permanent data
    unsupported operation


# 32. Exponential Backoff

Repeated retries should normally use backoff.

Example:

    attempt 1 → 1 second
    attempt 2 → 2 seconds
    attempt 3 → 4 seconds
    attempt 4 → 8 seconds


Add jitter where appropriate to avoid many workers retrying simultaneously.


# 33. Retry Limits

Retries must have limits.

Example:

    max_attempts = 3


After the limit:

    retrying
       ↓
    failed


The exact limit should depend on the operation.


# 34. Provider-Specific Retry

Different providers may require different retry policies.

Example:

    Search provider
        rate limit → longer backoff


    Local database
        connection failure → shorter retry


Do not assume one global retry policy is correct for everything.


# 35. Celery Retries

Celery can perform task retries.

That is useful for task execution.

However, the application should still understand the logical state of the work.

Conceptually:

    Celery retry
        +
    Autlead retry state


Celery handles task mechanics.

Autlead state handles business/pipeline recovery semantics.


# 36. Retry Idempotency

Before retrying, ask:

> If this operation runs twice, what happens?


Safe:

    normalize company


Potentially dangerous:

    send email


Potentially dangerous:

    create external resource


For side-effecting operations, use an idempotency key or another mechanism to prevent duplicate effects.


# 37. Pipeline State vs Record State

There may be multiple levels of state.

Pipeline:

    PipelineRun
        ↓
    running


Record:

    Company 123
        ↓
    enrichment completed


Task:

    Celery task
        ↓
    running


These should not be confused.


# 38. State Hierarchy

Conceptually:

    Pipeline Run
         │
         ├── Stage
         │     │
         │     ├── Record A
         │     ├── Record B
         │     └── Record C
         │
         └── Stage


The exact data model should only be created when the application requires it.


# 39. Pipeline Counters

Pipeline state may eventually track:

    discovered
    processed
    succeeded
    failed
    skipped
    retried


These counters are useful operationally.

Do not treat counters as the only source of truth.

For example:

    processed = 100


does not explain which records were processed.


# 40. State Persistence

Important state should survive process restarts.

A worker can disappear.

The state should not.

Prefer:

    PostgreSQL
        ↓
    durable state


over:

    Python memory
        ↓
    process exits
        ↓
    state disappears


# 41. State and Redis

Redis is appropriate for temporary coordination.

Examples:

    Celery broker
    Celery result backend
    short-lived locks
    temporary coordination


Redis should not automatically become the permanent record of pipeline history.


# 42. State and PostgreSQL

PostgreSQL is appropriate for durable execution state.

Examples:

    pipeline runs
    checkpoints
    recovery information
    retry history
    important transitions


This allows the system to inspect historical execution.


# 43. State History

Important state transitions may eventually be recorded.

Example:

    PENDING → RUNNING
    RUNNING → FAILED
    FAILED → RETRYING
    RETRYING → RUNNING
    RUNNING → COMPLETED


This is useful for debugging and auditing.


# 44. Transition History

A transition record may contain:

    previous_state
    new_state
    reason
    timestamp
    worker/task
    error information where appropriate


Do not store enormous exception traces in every state record unless required.


# 45. Error Information

State should distinguish between:

    state

and:

    error


Example:

    status = failed

    error_type = ProviderTimeout


Do not use:

    status = "ProviderTimeout"


State and error semantics are different.


# 46. Recovery Classification

Failures should eventually be classified into categories such as:

    retryable
    non_retryable
    needs_review


This makes recovery decisions explicit.


# 47. Manual Recovery

Some failures may require human intervention.

Example:

    provider authentication expired


The system should be able to represent:

    needs_review


rather than endlessly retrying.


# 48. Recovery Actions

Possible recovery actions include:

    retry
    resume
    skip
    restart stage
    restart pipeline
    cancel


The appropriate action depends on the failure and checkpoint state.


# 49. Resume vs Restart

Resume:

    Continue from the last safe checkpoint.


Restart:

    Start the relevant stage again.


A complete pipeline restart should be the last resort when partial state cannot safely be reused.


# 50. Checkpoint Validity

A checkpoint should remain valid only while its underlying assumptions remain valid.

For example:

    website analysis completed


may become stale after enough time has passed.

The pipeline may therefore decide:

    checkpoint exists
        +
    checkpoint still valid
        ↓
    reuse


otherwise:

    re-run analysis


# 51. State Expiration

Not every state needs to live forever.

Temporary state may have a retention policy.

Durable historical state may have a longer retention period.

Retention should be driven by:

- Operational usefulness
- Storage
- Privacy
- Compliance
- Debugging needs


# 52. State and Privacy

Pipeline state may contain information associated with companies or contacts.

Do not store unnecessary personal information in:

    logs
    retry records
    state history
    error metadata


Keep state focused on execution.


# 53. State and Logging

Logs answer:

> What happened?

State answers:

> What is the current durable execution status?


They complement each other.

Do not attempt to reconstruct all application state from log files.


# 54. State and Events

Events may communicate state changes.

Example:

    PipelineCompleted


The event system should not become the only source of durable state.

Persist important state first when required.


# 55. State and Workers

Workers should interact with state through application-level operations.

Example:

    worker
       ↓
    execute stage
       ↓
    update checkpoint
       ↓
    transition state


Avoid scattering raw SQL and Redis commands throughout Celery tasks.


# 56. State Operations

`state/*.py` files should expose focused operations.

For example:

    start_pipeline()
    transition_pipeline()
    create_checkpoint()
    mark_checkpoint_complete()
    acquire_lock()
    release_lock()
    schedule_retry()
    recover_pipeline()


The exact API should evolve with implementation.


# 57. `pipeline.py`

`pipeline.py` should coordinate pipeline execution state.

Responsibilities may include:

- Starting runs
- Updating run status
- Tracking current stage
- Completing runs
- Failing runs
- Cancelling runs


It should not contain the actual business pipeline logic.


# 58. `checkpoints.py`

`checkpoints.py` should expose checkpoint operations.

Responsibilities may include:

- Create checkpoint
- Read checkpoint
- Mark checkpoint completed
- Determine resumable stage
- Validate checkpoint


It should not perform extraction itself.


# 59. `locks.py`

`locks.py` should provide application-level locking operations.

Responsibilities may include:

- Acquire
- Renew where necessary
- Release
- Detect ownership
- Handle expiration


It should hide implementation details such as Redis or PostgreSQL locking where practical.


# 60. `retries.py`

`retries.py` should define retry behavior.

Responsibilities may include:

- Determine retryability
- Calculate delay
- Track attempts
- Enforce limits
- Mark exhausted retries


It should not execute the task itself.


# 61. `recovery.py`

`recovery.py` should coordinate recovery decisions.

Responsibilities may include:

- Inspect failed state
- Determine resumable work
- Determine retry/restart behavior
- Recover abandoned execution
- Mark unrecoverable work


It should use the other state components rather than duplicating them.


# 62. `transitions.py`

`transitions.py` should define valid state transitions.

Responsibilities:

- Valid states
- Valid transitions
- Transition validation
- Transition reasons


This provides a central place to protect the state machine.


# 63. Subdirectories

The subdirectories:

    checkpoints/
    locks/
    pipeline/
    recovery/
    retries/
    transitions/


should contain detailed implementations only when the corresponding area becomes large enough to justify them.

Do not create multiple layers of files simply to make the tree look architectural.


# 64. State Testing

State is critical infrastructure and should be heavily tested.

Test:

- Valid transitions
- Invalid transitions
- Checkpoint creation
- Checkpoint recovery
- Retry limits
- Backoff
- Lock acquisition
- Lock expiration
- Concurrent execution
- Worker failure
- Recovery behavior


# 65. Concurrency Testing

At least some state tests should simulate:

    Worker A
       +
    Worker B
       ↓
    same resource


The system should behave deterministically according to the locking/idempotency rules.


# 66. Failure Testing

Important failure scenarios should be tested deliberately.

Examples:

    worker crashes
    database unavailable
    provider timeout
    Redis unavailable
    task timeout
    process restart


The goal is to verify that Autlead fails predictably rather than merely hoping failures do not occur.


# 67. Recovery Testing

A useful recovery test:

    Start pipeline
        ↓
    complete stages 1–3
        ↓
    fail stage 4
        ↓
    persist failure
        ↓
    restart worker
        ↓
    recover
        ↓
    resume stage 4


This should become one of the important integration tests for the pipeline engine.


# 68. State and ETL

The ETL relationship is:

    EXTRACT
       ↓
    TRANSFORM
       ↓
    LOAD

State surrounds the execution of those stages:

    ┌───────────────────────────────┐
    │            STATE              │
    │                               │
    │ checkpoint / retry / recovery │
    │ locks / transitions / runs    │
    │                               │
    │   EXTRACT                     │
    │      ↓                        │
    │   TRANSFORM                   │
    │      ↓                        │
    │   LOAD                        │
    │                               │
    └───────────────────────────────┘


State is therefore execution infrastructure, not another ETL stage.


# 69. Example End-to-End Run

A simplified run may look like:

    Create PipelineRun
          ↓
    PENDING
          ↓
    RUNNING
          ↓
    Discovery
          ↓
    checkpoint
          ↓
    Normalization
          ↓
    checkpoint
          ↓
    Analysis
          ↓
    checkpoint
          ↓
    Enrichment
          ↓
    temporary provider failure
          ↓
    RETRY
          ↓
    Enrichment succeeds
          ↓
    checkpoint
          ↓
    Scoring
          ↓
    Qualification
          ↓
    Load
          ↓
    COMPLETED


# 70. Example Worker Crash

Example:

    Worker starts enrichment
          ↓
    enrichment executes
          ↓
    worker crashes before checkpoint


After restart:

    Recovery
       ↓
    last safe checkpoint
       ↓
    enrichment not completed
       ↓
    execute enrichment again


This is why checkpoints must represent completed work, not merely started work.


# 71. Example Duplicate Workers

Example:

    Worker A → company 123
    Worker B → company 123


Lock:

    company:123
        ↓
    Worker A owns lock


Worker B:

    lock unavailable
        ↓
    wait / skip / retry


The exact behavior should be defined by the pipeline operation.


# 72. State Should Remain Boring

State is infrastructure.

Avoid putting business decisions into it.

Bad:

    state decides:
        "This company is a good WebArtsy lead."


Better:

    qualification decides:
        "qualified"


State records:

    qualification stage completed


# 73. Avoid a Generic Workflow Engine

Do not prematurely build:

- Universal workflow DSL
- Visual workflow engine
- Arbitrary state-machine builder
- Distributed saga framework
- Event-sourcing framework
- Generic job orchestration platform


Autlead already has Celery for task execution.

The State layer should solve Autlead's actual execution-state requirements.


# 74. Recommended Implementation Order

Build State incrementally.

### Phase 1 — Pipeline State

Implement:

    PipelineRun
    status
    current stage
    start/end timestamps


### Phase 2 — Transitions

Implement:

    valid state transitions
    transition validation


### Phase 3 — Checkpoints

Implement:

    stage checkpoints
    resumable state


### Phase 4 — Retry Policy

Implement:

    retryable errors
    attempts
    exponential backoff
    retry limits


### Phase 5 — Recovery

Implement:

    failed run recovery
    resume
    retry
    restart


### Phase 6 — Locks

Add locking when real concurrent processing requires it.

Do not build sophisticated distributed locking before multiple workers actually process the same resources concurrently.


### Phase 7 — Hardening

Add:

    failure tests
    concurrency tests
    recovery tests
    observability
    state history


# 75. Golden Rules

### Rule 1

State records execution state, not business meaning.

### Rule 2

Celery executes tasks; State records durable application execution state.

### Rule 3

Redis can provide temporary coordination; PostgreSQL should hold durable state.

### Rule 4

Checkpoint only meaningful recovery boundaries.

### Rule 5

Never retry blindly.

### Rule 6

Never assume a partially executed operation completed.

### Rule 7

Make important operations idempotent where possible.

### Rule 8

Use locks only where concurrency actually creates a problem.

### Rule 9

Prefer resume over full restart when safe.

### Rule 10

Keep the state machine explicit and small.


# 76. Final Mental Model

Think of the State layer as Autlead's memory of execution.

    Pipeline
       ↓
    "I am running."


    Stage
       ↓
    "Analysis completed."


    Checkpoint
       ↓
    "This work is safe to resume from here."


    Retry
       ↓
    "This failure may be temporary."


    Lock
       ↓
    "Another worker is currently handling this resource."


    Recovery
       ↓
    "The previous execution failed; this is how we continue."


    Transition
       ↓
    "This state change is valid."


Together:

    STATE
      ├── pipeline
      ├── transitions
      ├── checkpoints
      ├── retries
      ├── locks
      └── recovery


The objective is not to create a sophisticated workflow framework.

The objective is to make Autlead's asynchronous, distributed ETL pipelines **restartable, observable, recoverable, and safe under concurrency**.