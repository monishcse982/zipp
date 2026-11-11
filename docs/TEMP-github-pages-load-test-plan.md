# Temporary Plan: GitHub-Triggered Long Load Test and Report History

> Historical planning document: checkboxes and proposed details below are not
> current status. The workflow and report history now exist; see the current
> [README](../README.md#run-a-test-from-github) and [roadmap](roadmap.md).

> Temporary working document. Remove it or convert the completed sections into
> permanent documentation after the first successful published run.

## Goal

Trigger a long Locust test manually from GitHub Actions, execute it against the
EC2-hosted k3s deployment, preserve the raw evidence, and publish a browsable
history of HTML reports through GitHub Pages.

The first run is a feasibility and repeatability exercise. It is not a clean
capacity benchmark because the load generator and the target Kubernetes cluster
share the same EC2 machine.

## Expected outcome

One manual workflow run must provide all of the following:

- an immutable GitHub Actions execution record;
- a downloadable artifact containing the native Locust report, CSV files,
  preset snapshot, command, and logs;
- a permanent GitHub Pages URL for the sanitized HTML report;
- a workflow summary with the test configuration and report links;
- a version-controlled observation document that explains the result,
  limitations, and follow-up work.

## Proposed architecture

```text
GitHub workflow_dispatch
        |
        v
EC2 self-hosted runner (zipp-load)
        |
        +--> checks application readiness
        +--> runs Locust against EC2 k3s
        +--> creates native HTML and CSV reports
        +--> uploads complete run directory as an Actions artifact
        +--> uploads a sanitized Pages bundle
                         |
                         v
GitHub-hosted publishing job
        |
        +--> updates the report catalogue
        +--> deploys the complete static site to GitHub Pages
        +--> exposes the permanent report URL
```

The publishing job must not receive Cognito credentials, kubeconfig data, SSH
keys, or AWS credentials.

## Phase 1: Prepare the self-hosted runner

- [ ] Create a dedicated, unprivileged Linux account for the GitHub Actions
  runner on the EC2 machine.
- [ ] Register the runner only with this repository.
- [ ] Apply the custom runner label `zipp-load`.
- [ ] Do not give the runner account `sudo`, Docker, kubeconfig, AWS, or SSH
  credentials unless a later requirement proves they are necessary.
- [ ] Confirm the runner can access the API through a stable local address.
- [ ] Confirm `git`, `uv`, Python 3.12, and the locked project dependencies are
  available.
- [ ] Keep runner startup manual. Starting or stopping EC2 remains outside the
  GitHub workflow.

The test job should use:

```yaml
runs-on: [self-hosted, linux, x64, zipp-load]
```

## Phase 2: Configure the GitHub environment

Create a protected GitHub environment named `load-test-ec2`.

Store these values as environment secrets:

- `COGNITO_CLIENT_ID`
- `COGNITO_API_USERNAME`
- `COGNITO_API_PASSWORD`

Store non-sensitive configuration as environment variables:

- `LOAD_TEST_BASE_URL`
- `LOAD_TEST_ENVIRONMENT=ec2-k3s`

Restrict the environment to the default branch. Add manual approval if the
repository settings support it and the extra click remains useful.

## Phase 3: Add the manual load-test workflow

Create a dedicated workflow, separate from normal CI. It must use
`workflow_dispatch` only.

Suggested inputs:

| Input | Purpose | Initial value |
| --- | --- | --- |
| `preset` | Select a version-controlled load profile | `mixed_redirect_soak_50user_60minutes` |
| `run_note` | Explain why the run is being executed | Required short text |
| `publish_report` | Publish the sanitized report to Pages | `true` |

Safety controls:

- [ ] Only accept preset names that exist under `tests/load/presets`.
- [ ] Do not accept an arbitrary Locust command from workflow input.
- [ ] Use a concurrency group with `cancel-in-progress: false` so two load tests
  cannot run against the same environment.
- [ ] Set a workflow timeout longer than the selected test. Use 90 minutes for
  the first one-hour run.
- [ ] Check out only the selected default-branch commit.
- [ ] Use `persist-credentials: false` in the test job.
- [ ] Print configuration names, but never secret values.

## Phase 4: Add preflight checks

Before Locust starts, the workflow must:

1. Print the commit SHA, preset, runner hostname, UTC start time, and run note.
2. Confirm the API liveness endpoint returns HTTP 200.
3. Confirm the API readiness endpoint returns HTTP 200.
4. Confirm Cognito authentication succeeds without printing any token.
5. Record the sanitized readiness response.
6. Confirm sufficient free disk space for the report directory.
7. Stop before generating load if any preflight check fails.

The workflow does not start EC2, K3s, Kubernetes workloads, or the Mac SSH
tunnel. EC2 localhost forwards are maintained by
`zipp-port-forwards.service`; the workflow verifies them with bounded retries
before generating load.

## Phase 5: Run the long test

Use the existing preset:

```text
mixed_redirect_soak_50user_60minutes
```

Current profile:

- scenario: `mixed_redirect_traffic.py`;
- pattern: constant users;
- concurrent users: 50;
- spawn rate: 10 users per second;
- duration: 3,600 seconds.

Run it through `tests/load/run-load-test.sh`; do not reproduce the Locust
command in the workflow.

Capture these identifiers with the run:

- GitHub run ID and attempt;
- Git commit SHA;
- preset name;
- test start and end time in UTC;
- target environment name;
- runner hostname;
- Locust version;
- Python version.

## Phase 6: Preserve the raw run artifact

Upload the complete generated run directory with
`actions/upload-artifact`. Use a name such as:

```text
locust-mixed_redirect_soak_50user_60minutes-<run-id>-<attempt>
```

Set retention to 90 days.

The artifact should include:

- `report.html`;
- `locust_stats.csv`;
- `locust_stats_history.csv`;
- `locust_failures.csv` when present;
- `locust_exceptions.csv` when present;
- `locust.log`;
- `preset.env`;
- `command.txt`;
- sanitized run metadata.

Run a secret and sensitive-data check before uploading. The artifact must not
contain `.env`, access tokens, refresh tokens, passwords, Authorization
headers, kubeconfig files, or SSH material.

Upload the artifact even when Locust or a later threshold check fails. Failed
runs are evidence too.

## Phase 7: Build the GitHub Pages report bundle

Publish only sanitized presentation files:

- the native Locust `report.html` copied to `index.html`;
- a small metadata page or JSON file;
- a human-readable link back to the GitHub Actions run.

Do not publish raw logs, environment files, commands containing secrets, or
authenticated request data.

Use this path structure:

```text
performance/
├── index.html
├── latest/
│   └── mixed-redirect-soak/
│       └── index.html
└── runs/
    └── <github-run-id>-<attempt>-<short-sha>/
        ├── index.html
        └── metadata.json
```

The catalogue should show:

- run date;
- preset and scenario;
- duration and peak users;
- commit SHA;
- result status;
- run note;
- link to the HTML report;
- link to the GitHub Actions run.

## Phase 8: Preserve Pages history

A Pages deployment replaces the previously deployed site. To retain old runs,
the publishing job must first restore the existing report catalogue, add the
new run, and then deploy the complete site.

Use a dedicated branch such as `performance-reports` as the durable source for
the static catalogue. The GitHub-hosted publishing job should:

1. download the sanitized Pages artifact from the test job;
2. check out the `performance-reports` branch;
3. add the new immutable run directory;
4. update the matching `latest` report;
5. regenerate the root catalogue;
6. commit the generated site with the run ID in the message;
7. upload the complete branch content as the Pages artifact;
8. deploy it using `actions/deploy-pages`.

The publishing job needs narrowly scoped permissions:

```yaml
permissions:
  contents: write
  pages: write
  id-token: write
```

The test job should retain `contents: read` only. Do not grant write permission
to the EC2 self-hosted test job.

Add `.nojekyll` to the published site so generated files are served without a
Jekyll build.

## Phase 9: Write the workflow summary

Add a concise Markdown summary through `GITHUB_STEP_SUMMARY` containing:

- preset and run note;
- target environment;
- commit SHA;
- start time and duration;
- request count;
- failure count and failure percentage;
- average RPS and peak RPS, if available;
- p50, p90, p95, and p99 response time;
- Actions artifact name;
- permanent Pages report URL;
- explicit `PASS`, `FAIL`, or `NOT EVALUATED` status.

Use `NOT EVALUATED` for the first run unless meaningful thresholds have been
agreed before execution. A completed process is not automatically a passed
performance test.

## Phase 10: Observe the long run

For the one-hour soak test, compare at least these windows:

- first 15 minutes;
- middle 15 minutes;
- final 15 minutes;
- five minutes after load stops.

Record:

- throughput stability;
- p50, p90, p95, and p99 latency drift;
- failure rate and failure types;
- active users and achieved RPS;
- API and UI pod CPU and memory;
- PostgreSQL CPU, memory, disk, and connections;
- Kafka CPU, memory, processing latency, errors, and backlog indicators;
- Valkey CPU, memory, and cache behavior;
- pod restarts and readiness failures;
- runner CPU and memory, because it shares the target EC2 host;
- recovery after the test ends.

## Phase 11: Commit the human observation record

After reviewing the report and Grafana data, add a permanent file:

```text
docs/performance-results/<date>-mixed-redirect-soak.md
```

Use this structure:

```markdown
# Mixed Redirect Soak Test

## Objective
## Environment
## Workload
## Success criteria
## Results
## Latency and throughput observations
## Application and infrastructure observations
## Errors and anomalies
## Known limitations
## Conclusions
## Follow-up actions
## Evidence links
```

The evidence section must link to:

- the GitHub Actions run;
- the GitHub Pages report;
- the source commit;
- relevant dashboard evidence;
- the downloadable artifact while it remains available.

This committed interpretation is the permanent record. The HTML report shows
numbers; the observation document explains what those numbers mean.

## Known limitations to state explicitly

- The load generator and target cluster share one EC2 machine.
- Runner CPU, memory, disk, and network usage can affect the target.
- The first run establishes workflow feasibility, not production capacity.
- The EC2 instance, k3s, application, and port access are started manually.
- GitHub Pages is public for this public repository.
- Actions artifacts expire after their configured retention period.
- Locust's native HTML report has limited layout and historical comparison.

## Definition of done

- [ ] A long test can be started from the GitHub Actions UI without SSHing into
  EC2 to run Locust.
- [ ] The workflow refuses to run when application readiness fails.
- [ ] Exactly one load-test workflow can execute at a time.
- [ ] The complete run directory is downloadable as an Actions artifact.
- [ ] The native Locust HTML report opens directly from GitHub Pages.
- [ ] The Pages catalogue retains earlier published runs.
- [ ] The workflow summary links to both the artifact and Pages report.
- [ ] No secret or sensitive material appears in artifacts, Pages, logs, or
  workflow output.
- [ ] A version-controlled observation document explains the long-run result
  and its limitations.
- [ ] The EC2 instance can be stopped after the run without losing the hosted
  report or written observations.

## Implementation order

1. Register and validate the restricted EC2 runner.
2. Create the protected `load-test-ec2` GitHub environment.
3. Add the manual load-test workflow and preflight checks.
4. Upload raw Actions artifacts and write the workflow summary.
5. Enable GitHub Pages with GitHub Actions as its source.
6. Add the `performance-reports` branch and catalogue generator.
7. Publish a short smoke-test report first.
8. Run the one-hour soak test only after the complete reporting path works.
9. Review Grafana and the Locust report.
10. Commit the permanent observation document and remove or consolidate this
    temporary plan.
