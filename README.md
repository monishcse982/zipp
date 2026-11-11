# Zipp: Performance Testing an Event-Driven Application

Zipp is a URL-shortening application used to explore repeatable performance testing across an API, cache, database, and asynchronous Kafka pipeline. Version-controlled Locust scenarios and load shapes run locally or through GitHub Actions, with Grafana evidence and a browsable report history for each published run.

**[Explore all performance reports](https://monishcse982.github.io/zipp/)** · [250-user ramp and spike](https://monishcse982.github.io/zipp/runs/43018942404-1-e72b2c2/index.html) · [200-user spike](https://monishcse982.github.io/zipp/runs/43005546299-1-e72b2c2/index.html) · [GitHub Actions](https://github.com/monishcse982/zipp/actions)

Each published run includes the native Locust report, application and infrastructure dashboard screenshots for the test window, run metadata, and a link to the Actions execution. The complete run evidence is also retained as an Actions artifact for 90 days.

## System under test

The FastAPI service creates and manages links in PostgreSQL. Redirects exercise policy checks and eligible cache lookups in Valkey; visit events flow through Kafka to a consumer that persists visit details. A React UI uses Amazon Cognito for sign-in. Prometheus scrapes application and infrastructure metrics, which are visualized in separate Grafana dashboards.

```text
Locust → FastAPI → PostgreSQL / Valkey
                   └→ Kafka → visit consumer → PostgreSQL
                  Prometheus → Grafana → report evidence
```

The application, its dependencies, and observability stack run in separate namespaces on a single K3s cluster hosted on EC2. The self-hosted GitHub Actions runner also runs on that EC2 instance. This makes the setup convenient and repeatable, but the load generator competes with the system under test for resources. Treat these runs as feasibility and comparative evidence, not isolated capacity benchmarks.

## Test design

Scenarios, load shapes, and presets are separate so each workload can be adjusted without rewriting the API client:

| Component | Location | Purpose |
| --- | --- | --- |
| Scenarios | [tests/load/scenarios](tests/load/scenarios) | User behavior and API interactions |
| API helpers | [tests/load/scenarios/helpers](tests/load/scenarios/helpers) | Shared authentication and API calls |
| Load shapes | [tests/load/patterns](tests/load/patterns) | User arrival, concurrency, spikes, steps, and recovery |
| Presets | [tests/load/presets](tests/load/presets) | Named, version-controlled scenario and shape parameters |

The mixed redirect scenario authenticates each user, creates four link types, and repeatedly selects visits with weights of 70% public, 15% password-protected, 10% IP-restricted, and 5% visit-limited. Weights express selection probabilities, not guaranteed request totals. Separate scenarios exercise read-heavy link management and write-heavy creation.

Available presets include a 100-user constant run, 200-user spikes, a 250-user step profile, a ramp with additive spikes, burst and recovery, a 50-user one-hour soak, and management and write-heavy workloads. Preset names encode their intended workload; inspect the preset and its shape for exact timing and user counts.

## Run a test from GitHub

The EC2 instance, K3s stack, self-hosted runner, and persistent port-forward service must be running. The `load-test-ec2` GitHub environment supplies the API and Grafana URLs and Cognito credentials. Start the instance manually; the workflow does not manage its lifecycle.

In **Actions → Run load test → Run workflow**, select a preset and provide a run note. Alternatively:

```bash
gh workflow run load-test.yml --ref master \
  -f preset=mixed_redirect_spike_user_200user_5minutes \
  -f run_note='Compare redirect latency under a five-minute spike profile'

gh run watch
```

The workflow validates the preset, checks API readiness and Grafana rendering, runs Locust, captures both dashboards for the test window, scans report files for configured credentials and token patterns, and publishes the report history to GitHub Pages. A completed workflow is not by itself a performance acceptance result: review latency, error rates, workload shape, and resource behavior against the goal for that run.

## Run locally

Start the application and its dependencies using the [operations guide](docs/operations-guide.md), and ensure the API is reachable at `http://localhost:8080`. Python and [uv](https://docs.astral.sh/uv/) are required. Configure a dedicated Cognito test user with the following environment variables; the runner also sources the ignored project `.env` file as shell syntax, so quote values containing shell metacharacters.

```bash
export COGNITO_CLIENT_ID='<app-client-id>'
export COGNITO_API_USERNAME='<test-user>'
export COGNITO_API_PASSWORD='<test-password>'

./tests/load/run-load-test.sh --list
./tests/load/run-load-test.sh mixed_redirect_constant_user_100user_5minutes \
  --base-url http://localhost:8080
```

Local evidence is saved under `reports/load/<preset>/<timestamp>/`: the Locust HTML report, CSV statistics and history, log, executed command, and preset snapshot. Credentials and generated tokens must stay out of source control and shared reports.

## Deployment and observability

Pull requests run Python and frontend checks, unit tests, Helm validation, workflow validation, image builds, and secret scans. Successful pushes to `master` publish API and UI images to GHCR using immutable commit-SHA tags and deploy the application release to EC2. A separate [manual deployment workflow](.github/workflows/deploy-ec2.yml) supports a specific previously published SHA. Infrastructure and observability chart changes require an explicit stack update.

The EC2 port-forward service keeps the API, UI, Grafana, Prometheus, PostgreSQL, and Valkey available on host loopback, with recovery after stale forwards. [EC2 setup and operations](docs/operations-guide.md) cover configuration, deployment, access, and troubleshooting. Dashboard definitions live in [deploy/charts/zipp-observability/dashboards](deploy/charts/zipp-observability/dashboards).

## Next improvements

- Add bounded Litmus chaos experiments and correlate recovery with application and infrastructure metrics.
- Host the application on Amazon EKS to explore a managed Kubernetes deployment.
- Host the load runner on EKS and scale load generation independently of the application.

See the [roadmap](docs/roadmap.md) and [load-test scenario ideas](docs/load-test-scenarios.md) for more detail.
