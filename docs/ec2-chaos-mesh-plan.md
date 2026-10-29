# EC2 Kubernetes and Chaos Mesh learning plan

## Goal

Recreate the Zipp stack on a Linux EC2 instance, then use Chaos Mesh to run small,
observable failure experiments against the app. This is a disposable learning
environment. Do not migrate the Minikube database or try to preserve its data.

The first pass uses one EC2 instance running a single-node K3s cluster. K3s is a
small Kubernetes distribution that can run a complete single-node cluster. This
keeps the exercise focused on Kubernetes and Chaos Mesh without the EKS control
plane and multi-node setup. It does not provide high availability: if the EC2
host fails, the whole cluster is unavailable. If the learning goal changes to
EKS, use the separate [EKS learning plan](eks-learning-plan.md).

## Target layout

```text
One Linux EC2 instance
└── K3s (single node, containerd)
    ├── zipp                 API and UI
    ├── zipp-infra           PostgreSQL, Valkey, Kafka, Strimzi
    ├── zipp-observability   Prometheus, Grafana, Zipp dashboard
    └── chaos-mesh           Chaos Mesh controllers, daemon, dashboard
```

Use the existing `zipp-app`, `zipp-infra`, and `zipp-observability` charts as
the deployment base. Keep Chaos Mesh in its own namespace and manage it as a
separate, pinned Helm release. The Chaos Mesh daemon needs privileged access to
the node to apply some fault types, so install only the permissions and
experiments needed for this isolated learning cluster. See the [Chaos Mesh Helm
installation guide](https://chaos-mesh.org/docs/production-installation-using-helm/).

## Phases

### 1. Set limits and prepare the EC2 host

- Pick the AWS Region and a Linux AMI supported by K3s. Price the instance, root
  EBS volume, and public IPv4 address in the AWS Pricing Calculator before
  launch. Set a budget alert and an instance shutdown reminder.
- Start with enough CPU and memory for PostgreSQL, Kafka, Valkey, Prometheus,
  Grafana, the app, and Chaos Mesh at the same time. Use the existing Minikube
  settings (4 CPUs and 8 GiB) as a bare reference, not a capacity guarantee;
  measure memory pressure and adjust the EC2 size before load or chaos runs.
- Restrict SSH to the current trusted IP range, or use AWS Systems Manager
  Session Manager. Do not expose the Kubernetes API, app, Grafana, or Chaos Mesh
  dashboard to the public internet. AWS recommends limiting SSH ingress to
  trusted sources in its [security group guidance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/security-group-rules-reference.html).
- Keep AWS credentials and `.env.kubernetes` off the instance image and out of
  Git. Use a narrowly scoped instance role only if the deployment requires AWS
  APIs.

**Done when:** the instance is reachable through the chosen admin path, has
working outbound access for packages and container images, and its cost and
shutdown plan are recorded.

### 2. Install K3s and check the host

- Install a pinned K3s release as a single-node server. K3s includes the control
  plane, data store, kubelet, and container runtime in a single-node install; see
  the [K3s quick-start guide](https://docs.k3s.io/quick-start).
- Configure local `kubectl` access without opening the Kubernetes API to all
  sources. Protect the copied kubeconfig because it grants cluster-admin access
  by default.
- Confirm the node is Ready, identify the container runtime socket, and record
  the K3s and Kubernetes versions. Chaos Mesh documents the K3s containerd
  socket as `/run/k3s/containerd/containerd.sock` and requires matching runtime
  settings during Helm installation.
- Check K3s's `local-path` StorageClass. The current Prometheus values use the
  Minikube-specific `standard` StorageClass. Add EC2/K3s values that select
  `local-path` (or a separately configured EBS StorageClass) before deploying
  Prometheus. K3s includes a local path provisioner, which binds storage to a
  node; see [K3s storage](https://docs.k3s.io/add-ons/storage). Confirm PVCs for
  PostgreSQL, Kafka, Valkey, and Prometheus bind.
- Treat all PVC data as disposable. With one node and local-path storage, data
  is tied to that host; deleting the EC2 instance or its EBS root volume removes
  the experiment state.

**Done when:** local `kubectl` can reach the cluster, the node is Ready, and a
test PVC binds using the selected StorageClass.

### 3. Rebuild the Zipp stack on K3s

- Build and publish or transfer the API and frontend images. Use immutable
  commit tags or digests; the current `pullPolicy: Never` and Minikube image
  loading flow are local-cluster settings and need K3s-specific deployment
  values or an image registry.
- Create `zipp`, `zipp-infra`, and `zipp-observability`. Deploy Strimzi and the
  `zipp-infra` chart, then observability, then `zipp-app`, following the existing
  dependency and secret synchronization order in the Makefile.
- Create fresh secrets on the host or inject them through a secure mechanism.
  Do not copy secrets from shell history or commit generated Kubernetes Secret
  manifests.
- Verify migrations, API and UI readiness, PostgreSQL/Kafka/Valkey access,
  Prometheus targets, and the Zipp Grafana dashboard. Use `kubectl port-forward`
  for private app and dashboard access.

**Done when:** create, visit, and disable flows work, visit events persist, and
the Zipp dashboard shows application metrics.

### 4. Install Chaos Mesh

- Check the installed Kubernetes version against Chaos Mesh's current
  [supported releases](https://chaos-mesh.org/docs/supported-releases/).
- Pin a Chaos Mesh Helm chart version. Install it in `chaos-mesh` with
  containerd runtime and K3s socket settings. Do not copy an old version from a
  tutorial without checking compatibility.
- Keep Dashboard authentication enabled. Access it with `kubectl
  port-forward`; do not expose it through a public LoadBalancer or ingress.
- Check the controller, daemon, dashboard, and DNS components are ready. Verify
  that the daemon runs on the K3s node before creating an experiment.
- Record the exact experiment YAML and expected recovery behavior. Give each
  experiment a short duration and explicit target selectors in namespace `zipp`.

**Done when:** Chaos Mesh is ready, its dashboard is private, and a short,
scoped experiment can be created and stopped.

### 5. Run experiments from low risk to higher impact

Run one experiment at a time. For each run, capture baseline health, start and
end time, target pods, fault duration, API behavior, pod events, logs, and
Prometheus/Grafana observations. Confirm the fault has ended and the system has
recovered before starting another.

1. **Pod kill:** delete one API pod with a short PodChaos experiment. Confirm
   Kubernetes replaces it and requests recover after the restart.
2. **Application network delay:** add a short NetworkChaos delay for traffic
   from the app namespace to one dependency. Watch readiness, error rates, and
   recovery after the fault ends. Keep selectors narrow and do not partition
   every workload from every dependency.
3. **Application resource stress:** use a short StressChaos run against one API
   pod. Observe CPU or memory pressure, latency, restarts, and recovery. Stop if
   the node begins to evict unrelated workloads.
4. **Repeat under a small Locust profile:** compare the same workload before,
   during, and after one selected fault. Save the report outside the cluster.

Do not start with node shutdown, broad network partitions, storage faults, or
KernelChaos. A single-node cluster has no alternate node for recovery, so node
failure takes down the control plane and all workloads. KernelChaos is disabled
by default, needs specific Linux kernel support, and can affect other pods on
the same host; see the [KernelChaos prerequisites and warning](https://chaos-mesh.org/docs/next/simulate-kernel-chaos-on-kubernetes/).

**Done when:** at least one failure has a repeatable baseline, a scoped fault,
observable impact, and evidence that the app recovers afterward.

### 6. Stop and clean up

- Delete all Chaos Mesh experiments and verify no experiment resources remain.
  Chaos Mesh's [uninstall guide](https://chaos-mesh.org/docs/uninstallation/)
  requires cleanup of experiments before uninstalling the controller.
- Uninstall Helm releases if retaining the host for another session. Otherwise
  terminate the EC2 instance and remove any detached EBS volumes, snapshots,
  public IPv4 addresses, and security group rules created for the exercise.
- Check AWS billing and resource inventory after cleanup. Keep load-test reports
  and notes outside the instance if they are useful.

**Done when:** the EC2 host and any billable attached or detached resources are
removed or intentionally retained, and the actual session cost is recorded.

## Repository changes expected during implementation

- Add K3s-specific values for image pull policy, registry references, and
  Prometheus storage class. Keep Minikube defaults intact.
- Add an explicit EC2 deployment workflow or Make targets that use a dedicated
  kubecontext and values files rather than Minikube startup and image loading.
- Add a pinned Chaos Mesh chart dependency or a documented pinned Helm install
  command, plus example PodChaos, NetworkChaos, and StressChaos manifests scoped
  to the `zipp` namespace.
- Add cleanup and validation commands. Do not add automated chaos experiments
  to normal CI; run them only against the disposable cluster.

This document is a plan only. No EC2 instance, K3s cluster, or Chaos Mesh
installation is created by adding it to the repository.
