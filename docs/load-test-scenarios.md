# Zipp Load-Test Scenarios

This document defines the load and resilience scenarios for Zipp. It describes
test intent, traffic shape, expected outcomes, and evidence to collect. It does
not prescribe a test implementation.

## Existing scenarios

The repository already covers:

- Link creation across supported policy types
- Public redirect traffic
- Create, visit, and visit-limit/expiry workflows
- Ramp, constant, spike, step, and constant-rate load shapes

## Core performance scenarios

### 1. Redirect cache-hit baseline

**Purpose:** Measure the common, fastest redirect path.

- Pre-create one public link.
- Repeatedly call `GET /link/{short_code}`.
- Do not follow redirects.
- Expected response: `302`.
- Observe latency percentiles, Redis operations, PostgreSQL queries, Kafka event
  rate, CPU, and memory.

This is the primary baseline scenario.

### 2. Redirect cache-miss workload

**Purpose:** Measure database-backed redirect performance.

- Create a large pool of unique short codes.
- Avoid repeatedly using the same link.
- Call the public redirect endpoint.
- Expected response: `302`.
- Compare latency and PostgreSQL load with the cache-hit baseline.

### 3. Mixed redirect traffic

**Purpose:** Represent a realistic redirect workload.

Suggested distribution:

- 70% public links
- 15% password-protected links
- 10% IP-restricted links
- 5% visit-limited or expiring links

Track `302`, `401`, `403`, `404`, and `410` responses separately.

### 4. Authenticated link creation

**Purpose:** Measure write throughput and dependency impact.

- Authenticate one or more test users.
- Call `POST /link/`.
- Generate unique short codes or allow server-generated codes.
- Mix policy types.
- Expected response: `200`.
- Observe PostgreSQL write latency, Kafka publish behavior, collisions, and
  transaction errors.

### 5. Authenticated link-management browsing

**Purpose:** Represent the dashboard read workload.

Mix:

- `GET /links?limit=20&offset=0`
- `GET /links?limit=100&offset=0`
- Requests with increasing offsets
- `GET /links/{short_code}`

Expected response: `200`.

### 6. Link update workload

**Purpose:** Measure authenticated updates.

- Pre-create a pool of links.
- Call `PATCH /links/{short_code}` repeatedly.
- Use different destination URLs.
- Expected response: `200`.
- Observe lock contention, database latency, and stale-cache behavior.

### 7. Disable/delete workload

**Purpose:** Test link lifecycle changes.

- Pre-create links.
- Call `DELETE /links/{short_code}`.
- Verify subsequent redirect behavior.
- Expected responses: `204` for deletion and the documented unavailable status
  for later redirects.

Keep this separate from normal redirect traffic because it changes state.

## Policy and correctness scenarios

### 8. Password-protected links

Test separately:

- No password
- Correct password
- Incorrect password
- Repeated correct-password access

Measure response classes, latency, and cache behavior. Test the form-based
`/unlock` path separately from header-based access.

### 9. Visit-limit exhaustion

**Purpose:** Validate concurrent access correctness.

- Create links with limits such as 1, 5, and 10.
- Send concurrent visits.
- Verify successful visits do not exceed the configured limit.
- Verify the terminal response is `410`.

### 10. Link expiry

**Purpose:** Verify time-based lifecycle behavior.

- Create links with short TTLs.
- Visit before expiry.
- Visit after expiry.
- Repeat under light and concurrent load.

## Dependency and resilience scenarios

### 11. Kafka backpressure

- Generate sustained redirect traffic.
- Monitor producer errors, topic throughput, consumer lag, visit persistence
  delay, and API latency.
- In a disposable environment, slow or stop the consumer.
- Determine whether redirects remain available while visit recording falls
  behind.

### 12. Redis degradation

Run separate tests with Redis:

- Healthy
- Unavailable
- Deliberately delayed

Measure redirect latency, PostgreSQL load, errors, and recovery behavior.

### 13. PostgreSQL degradation

- Pause or stop PostgreSQL in a disposable environment.
- Test public redirects and authenticated management requests separately.
- Observe readiness status, request failures, and recovery after restoration.

Readiness `503` is dependency-state evidence, not an application throughput
failure.

### 14. Authentication rejection

Test:

- Missing bearer token
- Expired token
- Wrong client ID
- ID token instead of access token
- Malformed token

Expected response: `401`. Confirm rejected requests do not reach business
database or Kafka operations.

### 15. Health-probe load

Generate repeated requests to:

- `GET /health/live`
- `GET /health/ready`

Measure probe latency during application load. Readiness performs dependency
checks and must be analysed separately from liveness.

### 16. Kubernetes restart and recovery

During a controlled workload, restart:

- API pod
- Frontend pod
- Valkey
- Kafka or the consumer

Record failed requests, recovery time, readiness transitions, event delay or
loss, and cache warm-up behavior.

## Recommended execution order

1. Redirect cache-hit baseline
2. Redirect cache-miss comparison
3. Authenticated create and list
4. Mixed redirect traffic
5. Password and visit-limit correctness
6. Kafka and Redis degradation
7. Pod restart and recovery

## Evidence to capture for every run

- Workload shape, target rate, user count, and duration
- Response-code distribution
- p50, p95, and p99 latency
- Throughput
- API, PostgreSQL, Redis, and Kafka CPU/memory signals
- Consumer lag and event-processing delay
- Readiness and liveness state
- Test-data setup and cleanup details

The first high-value comparison is the same redirect workload with Valkey
healthy and unavailable. This demonstrates whether the cache reduces database
load and improves redirect latency.
