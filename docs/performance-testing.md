# Performance Testing Guide

Zipp uses Locust to exercise a FastAPI service and its PostgreSQL, Valkey, and Kafka dependencies. Scenarios define user behavior; load shapes define how concurrency changes; presets combine a scenario, a shape, and its parameters. The [report catalogue](https://monishcse982.github.io/zipp/) retains published runs and dashboard evidence.

## Workloads

| Scenario | Behavior | Example preset |
| --- | --- | --- |
| Mixed redirects | Each user authenticates, creates four links, then selects public, password-protected, IP-restricted, and visit-limited visits with weights 70/15/10/5. | `mixed_redirect_spike_user_200user_5minutes` |
| Management API | Authenticated users primarily list and read links, with some create, update, and disable operations. | `management_api_constant_user_50user_10minutes` |
| Write-heavy creation | Authenticated users repeatedly create links with different policies, TTLs, and optional titles. | `write_heavy_constant_user_50user_10minutes` |

The task weights express the probability of selecting each task, not a promise that actual requests will have exactly those percentages. Setup calls, wait time, differing task durations, failures, and random selection affect the measured mix. One user repeatedly selects a task until the load shape removes it or the run ends.

Presets include constant, spike, step, ramp with spikes, burst and recovery, and soak profiles. See [the preset files](../tests/load/presets) for the actual parameters; a preset's user count represents concurrent virtual users, not requests per second. In the 250-user ramp preset, 50 users are added to the *current baseline* during each spike, so the spike does not necessarily reach 300 concurrent users.

## Run through GitHub Actions

Start EC2 manually and confirm K3s, the application, the `zipp-port-forwards` service, Grafana, and the `zipp-load` self-hosted runner are available. The `load-test-ec2` GitHub environment must contain:

- Variables: `LOAD_TEST_BASE_URL`, `LOAD_TEST_ENVIRONMENT`, and `GRAFANA_BASE_URL`.
- Secrets: `COGNITO_CLIENT_ID`, `COGNITO_API_USERNAME`, and `COGNITO_API_PASSWORD`.

Choose a preset and enter a run note in **Actions → Run load test**, or use:

```bash
gh workflow run load-test.yml --ref master \
  -f preset=mixed_redirect_spike_user_200user_5minutes \
  -f run_note='Describe the question this run will answer'

gh run watch
```

The workflow checks API liveness and readiness and validates Grafana rendering before starting Locust. It captures both Grafana dashboards for the test window, scans report content for configured credentials and token patterns, and uploads the run as a 90-day Actions artifact. A GitHub-hosted job publishes a sanitized bundle and report history to Pages. The workflow serializes load tests against this environment.

## Run locally

Follow the [operations guide](operations-guide.md) to make the target available, then set `COGNITO_CLIENT_ID`, `COGNITO_API_USERNAME`, and `COGNITO_API_PASSWORD` in the environment or the ignored project `.env` file. The script sources `.env` as shell code; quote values containing shell metacharacters. Never commit credentials or tokens.

```bash
./tests/load/run-load-test.sh --help
./tests/load/run-load-test.sh --list
./tests/load/run-load-test.sh mixed_redirect_constant_user_100user_5minutes \
  --base-url http://localhost:8080
```

Each run creates `reports/load/<preset>/<timestamp>/` with the Locust HTML report, CSV statistics and history, log, executed command, and preset snapshot. Review generated content before sharing it.

## Interpret a run

Before running, record the question, expected behavior, workload, target version, and relevant thresholds. Afterwards compare request counts, response codes, failures, throughput, and latency percentiles with the application and infrastructure graphs over the same time window. Check pod restarts and dependency health when investigating changes. Record observations and any uncertainty alongside links to the report and Actions run.

Locust's **Final ratio** section describes configured task weights and final user-class counts; it is not a count of actual executed requests. A shape that ends with zero users can display zero for the final class and total ratios. Use request statistics for observed traffic.

The EC2 runner and K3s workloads currently share a machine. CPU, memory, network, and port forwarding can affect both generator and target. Treat the results as repeatable comparisons and feasibility evidence, not isolated capacity measurements. A successful workflow means execution and publication completed; it does not establish a performance pass without explicit thresholds.

See [scenario ideas](load-test-scenarios.md) for proposed experiments and the [roadmap](roadmap.md) for Litmus and EKS work.
