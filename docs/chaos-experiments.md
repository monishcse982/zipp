# Proposed Litmus Experiments

These are hypotheses, not completed experiments or guarantees. Run only on an isolated test deployment after agreeing on steady-state latency and error limits, selecting an appropriate background Locust preset, and verifying a manual stop and recovery path. Scope the blast radius to named test namespaces and resources, cap the duration, and abort if the agreed thresholds or safety conditions are breached. Capture test-window application and infrastructure metrics, report links, experiment parameters, and recovery time.

| Experiment | Hypothesis to test | Evidence and safety |
| --- | --- | --- |
| Interrupt Valkey | Redirects fall back to PostgreSQL without unexpected 5xx responses. Current cache handling is not best-effort, so this is a desired behavior to test, not an expectation the current system meets. | Compare redirect errors and latency, cache availability, database load, readiness, and recovery. Stop on the agreed error or latency limit. |
| Interrupt Kafka | Redirect and event-processing behavior remains bounded during a broker interruption and recovers when Kafka returns. Delivery is not assumed loss-free. | Compare redirects, producer errors, committed consumer lag once instrumented, and reconciled persisted events. Stop on sustained failures or backlog beyond the agreed limit. |
| Restart the API pod | Traffic recovers after a rollout or pod restart; persisted visit events can be reconciled without silently missing or double-counting visits. Current processing is not idempotent, so duplicates or loss are possible. | Observe readiness, request errors, recovery time, event IDs and persisted visits once reconciliation exists. Stop if the service does not recover within the agreed window. |

Before executing, choose experiments supported by the deployed Litmus and Kubernetes versions, and validate the experiment configuration and permissions. Record both a baseline and the experiment under the same workload; do not label a hypothesis as passed until its measurable criteria and evidence are available.
