# Zipp Load Testing and Portfolio Plan

> Historical session plan. Several workloads and the GitHub reporting workflow
> are now implemented. Use the [README](../README.md#test-design)
> for current instructions and the [roadmap](roadmap.md) for next steps.

## Objective

Run repeatable, evidence-based performance tests against Zipp, correlate the
results with application and infrastructure dashboards, and preserve the work
in Git so the project demonstrates an end-to-end SDET and platform workflow.

## Tomorrow's test session

### 1. Establish a clean baseline

- Start the local or EC2 Kubernetes stack.
- Confirm API, UI, PostgreSQL, Kafka, Valkey, Prometheus, and Grafana are ready.
- Set Grafana to the exact load-test time window before starting the run.
- Run the current profile:

  ```bash
  ./tests/load/run-load-test.sh \
    mixed_redirect_ramp_up_down_spike_250user_10minutes \
    --base-url http://localhost:8080
  ```

- Save the report path, dashboard screenshots, and the matching Git commit.

### 2. Run higher-intensity profiles one at a time

- Do not run overlapping tests against the same cluster.
- Allow the system to return to baseline between runs.
- Record: user shape, peak requests/second, p50/p75/p90/p95/p99, errors,
  maximum latency, CPU, memory, Kafka lag, PostgreSQL connections, and Valkey
  memory.
- Stop a run if error rate, memory pressure, or pod restarts become unsafe.

## Additional realistic load profiles

The current `mixed_redirect_traffic` scenario is a good general baseline. Add
profiles that isolate different production behaviors rather than increasing
load blindly.

The first four runnable profiles are:

| Test | Preset | Purpose |
| --- | --- | --- |
| Management API | `management_api_constant_user_50user_10minutes` | Read-heavy authenticated list and detail traffic with occasional mutations |
| Write-heavy creation | `write_heavy_constant_user_50user_10minutes` | Sustained creation across policy, TTL, title, and visit-limit variants |
| Burst and recovery | `mixed_redirect_burst_recovery_250user_6m30s` | Establish baseline, burst to 250 users, return to baseline, and observe recovery |
| Soak | `mixed_redirect_soak_50user_60minutes` | Hold moderate mixed redirect traffic for one hour |

### Read-heavy redirect traffic

- 95% public redirects
- 3% password-protected redirects
- 1% IP-restricted redirects
- 1% visit-limited redirects
- Useful for measuring cache effectiveness and redirect tail latency.

### Management API traffic

- Authenticated `GET /links` list requests
- `GET /links/{short_code}` detail requests
- Occasional create, update, and disable operations
- Useful for database query latency and connection-pool pressure.

### Write-heavy link creation

- High link-creation rate with unique short codes
- Mix short and long TTL values
- Mix policies and optional titles
- Useful for PostgreSQL writes, conflict handling, and Kafka side effects.

### Expiry and visit-limit traffic

- Links close to expiry
- Links at or near their visit limit
- Repeated requests to exhausted links
- Useful for soft-delete behavior and error-path latency.

### Cache warm-up and cache cold-start

- Cold run with a new link set
- Warm run against the same public links
- Compare cache hit ratio, database load, and p95/p99 redirect latency.

### Burst and recovery test

- Ramp to the normal peak.
- Apply a short burst above the expected peak.
- Return to baseline and observe recovery time.
- Correlate recovery with pod CPU, memory, Kafka processing, and database
  connections.

### Soak test

- Moderate load for 30–60 minutes.
- Watch for memory growth, connection leaks, Kafka backlog, and latency drift.

### Dependency degradation test

- Run a normal load test while introducing controlled Kafka, Redis, or database
  latency with Chaos Mesh.
- Confirm readiness, error handling, and recovery behavior.
- Keep this separate from the baseline performance tests.

## Test evidence to preserve

For every important run, preserve:

- preset file
- command file
- HTML report
- CSV statistics
- failure and exception CSV files
- Locust log
- Grafana screenshots or dashboard export
- Git commit SHA
- environment and cluster description without secrets

Never commit `.env`, Cognito credentials, bearer tokens, or raw authenticated
requests.

## Hosting plan

### Active path: EC2-hosted k3s with GitHub Actions execution

1. Start the EC2 instance and the k3s service.
2. Install and register a dedicated GitHub Actions self-hosted runner on the
   EC2 machine. Do not use the runner for unrelated workloads.
3. Keep application, infrastructure, and observability in separate namespaces:
   `zipp`, `zipp-infra`, and `zipp-observability`.
4. Trigger all load tests from GitHub Actions. The workflow should select a
   preset, run Locust on the EC2 runner, and upload the HTML/CSV reports as
   workflow artifacts.
5. Use the existing Prometheus and Grafana dashboards for correlation. Record
   the dashboard time window and test run ID in the workflow summary.
6. Store Cognito and database values as GitHub Actions environment secrets;
   never commit them to the repository.
7. Use the SSH tunnel and kubeconfig workflow from the Mac only for manual
   inspection and dashboard access, not for normal test execution.
8. Stop the EC2 instance after testing to avoid unnecessary compute cost.

## Git history and resume evidence

Use small, outcome-focused commits and pull requests. Suggested sequence:

1. `feat(metrics): add operation and policy latency metrics`
2. `feat(observability): split application and infrastructure dashboards`
3. `feat(load-tests): add ramp and recovery profile`
4. `test(load): add read-heavy and management-api scenarios`
5. `ci(performance): publish load-test reports as workflow artifacts`
6. `docs(performance): document baseline and capacity findings`

Each pull request should include:

- the problem being tested
- the load shape
- the expected result
- the measured result
- dashboard evidence
- known limitations
- a link to the generated report

This creates a visible progression from instrumentation, to testing, and to
observability.

## Definition of done

- At least one clean baseline run has zero unexpected failures.
- p50, p75, p90, p95, and p99 are visible for create, list, and redirect paths.
- Application and infrastructure dashboards use the same test time window.
- PostgreSQL, Kafka, and Valkey targets are `UP` in Prometheus.
- At least one burst, soak, and dependency-degradation test is documented.
- Reports and dashboard evidence are linked to Git commits without exposing
  secrets.
