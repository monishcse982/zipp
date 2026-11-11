# Zipp Roadmap

Zipp runs on a single EC2-hosted K3s cluster with a self-hosted GitHub Actions runner. Version-controlled Locust workloads produce reports and Grafana evidence through GitHub Pages. The load generator shares resources with the application, so current results are useful for feasibility and comparisons, not isolated capacity measurements.

## Next improvements

- **Validate the test path:** compare identical profiles through port-forward and a private direct cluster path, with measured runner and target resource headroom.
- **Separate the generator:** run Locust from another small EC2 instance, then repeat each preset at least three times to quantify variance. Keep the target, data setup, and environment comparable.
- **Pipeline evidence:** instrument successful event-to-persistence delay, expose and verify committed consumer lag, and reconcile event delivery separately so a fast percentile does not hide missing events.
- **Litmus chaos experiments:** run bounded hypotheses under a known background load; record steady state, namespace scope, abort conditions, observed impact, and recovery. See [chaos experiment proposals](chaos-experiments.md).
- **Application on EKS:** examine how managed Kubernetes changes deployment, node scaling, and operational overhead compared with single-node K3s; document cost and teardown.
- **Scalable load runner on EKS:** investigate independent distributed load generation and worker scaling after a separate generator baseline exists.

## Known limitations and risks

- Define measurable latency, throughput, and error-rate objectives before evaluating results.
- Add browser end-to-end tests for authenticated UI journeys.
- Cache operations are not best-effort; Valkey failures can affect availability.
- The visit consumer runs in the API process. Persistence does not deduplicate by event ID, and delivery during failures is not guaranteed.
- Validate IP-restricted redirects behind a trusted reverse proxy before using them in a proxied deployment.

The earlier [EC2 and Chaos Mesh plan](ec2-chaos-mesh-plan.md) records the previous exploration; Litmus is the next planned chaos-testing direction.
