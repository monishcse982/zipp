# Zipp Roadmap

Zipp runs on a single EC2-hosted K3s cluster with a self-hosted GitHub Actions runner. Version-controlled Locust workloads produce reports and Grafana evidence through GitHub Pages. The load generator shares resources with the application, so current results are useful for feasibility and comparisons, not isolated capacity measurements.

## Next improvements

- **Litmus chaos experiments:** install Litmus and define bounded, repeatable failure scenarios for application pods and dependencies. Record the hypothesis, safety limits, observed impact, and recovery alongside load-test evidence.
- **Application on EKS:** deploy the application and its supporting components to Amazon EKS; document configuration, access, observability, and teardown costs.
- **Scalable load runner on EKS:** run load generation independently of the application and scale workers to match the workload. Measure runner resource usage and account for network and generator limits before drawing capacity conclusions.

## Additional opportunities

- Define measurable latency, throughput, and error-rate objectives before evaluating results.
- Add browser end-to-end tests for authenticated UI journeys.
- Study degraded Redis behavior, durable Kafka publishing, and idempotent visit processing.
- Validate IP-restricted redirects behind a trusted reverse proxy before using them in a proxied deployment.

The earlier [EC2 and Chaos Mesh plan](ec2-chaos-mesh-plan.md) records the previous exploration; Litmus is the next planned chaos-testing direction.
