#!/usr/bin/env bash
# Rebuild the disposable Zipp stack on the local, single-node K3s host.
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
context=""
storage_class="local-path"
confirmed=false
archive=""

usage() {
  cat <<'EOF'
Usage: ./scripts/reset-ec2-k3s.sh --confirm [--context NAME] [--storage-class NAME]

Deletes and recreates zipp, zipp-infra, and zipp-observability on the local
single-node K3s cluster. This removes their Secrets, PVCs, and database data.
K3s, kube-system, and Chaos Mesh are left alone.

Required local files: .env.kubernetes and frontend/.env.local
The script builds both images, imports them into K3s, and redeploys the charts.
It does not start port-forwards; restart them after the rebuild.
EOF
}

die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
log() { printf '\n==> %s\n' "$*"; }
k() { kubectl --context "$context" "$@"; }
h() { helm --kube-context "$context" "$@"; }
cleanup() { if [[ -n "$archive" ]]; then rm -f -- "$archive"; fi; }
trap cleanup EXIT
trap 'printf "Reset stopped at line %s. Check the error above; the script can be rerun.\n" "$LINENO" >&2' ERR

while (($#)); do
  case "$1" in
    --confirm) confirmed=true; shift ;;
    --context|--storage-class)
      (($# >= 2)) && [[ -n "$2" ]] || die "$1 needs a value"
      if [[ "$1" == --context ]]; then context="$2"; else storage_class="$2"; fi
      shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1 (see --help)" ;;
  esac
done

[[ "$confirmed" == true ]] || { usage; die 'Pass --confirm to erase the three Zipp namespaces'; }
cd "$project_dir"

for tool in kubectl helm docker sudo k3s make python3 git hostname systemctl awk; do
  command -v "$tool" >/dev/null || die "Missing command: $tool"
done
[[ -f .env.kubernetes ]] || die 'Missing .env.kubernetes'
[[ -f frontend/.env.local ]] || die 'Missing frontend/.env.local'

context="${context:-$(kubectl config current-context)}"
[[ -n "$context" ]] || die 'No Kubernetes context selected'
[[ "$context" =~ ^[A-Za-z0-9._-]+$ ]] || die 'Use a simple K3s context name (letters, digits, dots, underscores, hyphens)'
[[ "$storage_class" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || die 'Invalid StorageClass name'
[[ $(systemctl is-active k3s) == active ]] || die 'The local K3s service is not active'

node_names="$(k get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')"
[[ $(printf '%s\n' "$node_names" | wc -l) -eq 1 ]] || die 'This script requires exactly one K3s node'
node_version="$(k get nodes -o jsonpath='{.items[0].status.nodeInfo.kubeletVersion}')"
[[ "$node_version" == *+k3s* ]] || die "Context $context is not a K3s cluster"
node_ip="$(k get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')"
[[ -n "$node_ip" && " $(hostname -I) " == *" $node_ip "* ]] || die 'The selected K3s node is not this host'
k wait --for=condition=Ready "node/$node_names" --timeout=30s
k get storageclass "$storage_class" -o name >/dev/null
[[ $(k auth can-i delete namespaces) == yes ]] || die 'Kubernetes permission to delete namespaces is required'
[[ $(k auth can-i create namespaces) == yes ]] || die 'Kubernetes permission to create namespaces is required'
[[ $(k auth can-i create secrets --namespace zipp) == yes ]] || die 'Kubernetes permission to create Zipp Secrets is required'
docker info >/dev/null || die 'Docker daemon is unavailable to this user; check docker group membership'
sudo -n k3s ctr images list >/dev/null || die 'Passwordless sudo access to k3s ctr is required'

log "Preflight: context=$context node=$node_names storage=$storage_class"
make validate-env frontend-env-check
helm repo add valkey https://valkey.io/valkey-helm/ --force-update
make chart-validate "PROFILE=$context" "PROMETHEUS_STORAGE_CLASS=$storage_class"

revision="$(git rev-parse --short=8 HEAD)"
if [[ -n "$(git status --porcelain)" ]]; then
  revision="$revision-dirty"
fi
tag="local-$revision-$(date -u +%Y%m%d%H%M%S)"
log "Building and importing zipp:$tag and zipp-ui:$tag"
make image-build "IMAGE_TAG=$tag" "FRONTEND_IMAGE_TAG=$tag"
archive="$(mktemp "${TMPDIR:-/tmp}/zipp-images.XXXXXX")"
docker save --output "$archive" "zipp:$tag" "zipp-ui:$tag"
sudo -n k3s ctr images import "$archive"
sudo -n k3s ctr images list | grep -F "docker.io/library/zipp:$tag" >/dev/null
sudo -n k3s ctr images list | grep -F "docker.io/library/zipp-ui:$tag" >/dev/null
cleanup
archive=""

namespace_exists() {
  local result
  result="$(k get namespace "$1" --ignore-not-found -o name)" || die "Could not inspect namespace $1"
  [[ -n "$result" ]]
}

namespace_terminating() {
  local result
  result="$(k get namespace "$1" -o jsonpath='{.metadata.deletionTimestamp}')" || die "Could not inspect namespace $1"
  [[ -n "$result" ]]
}

uninstall_active_release() {
  local release="$1" namespace="$2"
  if namespace_exists "$namespace" && ! namespace_terminating "$namespace"; then
    if ! h uninstall "$release" --namespace "$namespace" --ignore-not-found --wait --timeout 10m; then
      if [[ "$namespace" == zipp-infra ]]; then
        k get kafka,kafkauser,kafkanodepool,kafkatopic --namespace zipp-infra -o wide || true
      fi
      die "Could not uninstall $release; inspect remaining resources before retrying"
    fi
  fi
}

topic_names() {
  k get kafkatopics.kafka.strimzi.io --namespace zipp-infra \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'
}

wait_for_topics() {
  local attempt remaining
  for ((attempt = 0; attempt < 24; attempt++)); do
    remaining="$(topic_names)" || die 'Could not list KafkaTopics'
    [[ -z "$remaining" ]] && return 0
    sleep 5
  done
  return 1
}

clear_stuck_topic_finalizers() {
  local remaining topic finalizers
  remaining="$(topic_names)" || die 'Could not list KafkaTopics'
  [[ -n "$remaining" ]] || return 0
  log 'Topic deletion timed out; checking the known Strimzi topic-operator finalizer'
  while IFS= read -r topic; do
    [[ -n "$topic" ]] || continue
    finalizers="$(k get kafkatopic "$topic" --namespace zipp-infra -o jsonpath='{.metadata.finalizers}')"
    [[ "$finalizers" == '["strimzi.io/topic-operator"]' ]] || die "KafkaTopic/$topic has unexpected finalizers: $finalizers"
    k patch kafkatopic "$topic" --namespace zipp-infra --type=json \
      --patch='[{"op":"remove","path":"/metadata/finalizers"}]'
  done <<< "$remaining"
  wait_for_topics || die 'KafkaTopics still exist after removing their finalizers'
}

delete_topics() {
  local crd topics
  namespace_exists zipp-infra || return 0
  crd="$(k get crd kafkatopics.kafka.strimzi.io --ignore-not-found -o name)" || die 'Could not inspect KafkaTopic CRD'
  [[ -n "$crd" ]] || return 0
  topics="$(topic_names)" || die 'Could not list KafkaTopics'
  [[ -n "$topics" ]] || return 0
  k delete kafkatopics.kafka.strimzi.io --namespace zipp-infra --all --wait=false
  wait_for_topics || clear_stuck_topic_finalizers
}

ensure_strimzi_operator() {
  local crd clusters
  namespace_exists zipp-infra || return 0
  namespace_terminating zipp-infra && return 0
  crd="$(k get crd kafkas.kafka.strimzi.io --ignore-not-found -o name)" || die 'Could not inspect Kafka CRD'
  [[ -n "$crd" ]] || return 0
  clusters="$(k get kafkas.kafka.strimzi.io --namespace zipp-infra -o name)" || die 'Could not list Kafka clusters'
  [[ -n "$clusters" ]] || return 0
  # An interrupted previous teardown may have removed the operator first.
  h upgrade --install strimzi-operator oci://quay.io/strimzi-helm/strimzi-kafka-operator \
    --namespace zipp-infra --version 1.2.0 \
    --values deploy/kafka/strimzi-operator-values.yaml --wait --timeout 10m
}

wait_for_strimzi_resources() {
  local crd remaining attempt
  namespace_exists zipp-infra || return 0
  crd="$(k get crd kafkas.kafka.strimzi.io --ignore-not-found -o name)" || die 'Could not inspect Kafka CRD'
  [[ -n "$crd" ]] || return 0
  for ((attempt = 0; attempt < 60; attempt++)); do
    remaining="$(k get kafka,kafkauser,kafkanodepool,kafkatopic \
      --namespace zipp-infra -o name)" || die 'Could not list Strimzi resources'
    [[ -z "$remaining" ]] && return 0
    sleep 5
  done
  k get kafka,kafkauser,kafkanodepool,kafkatopic --namespace zipp-infra -o wide || true
  die 'Strimzi resources still exist; keeping the operator installed for cleanup'
}

log 'Removing the Zipp releases and Strimzi topics'
uninstall_active_release zipp-app zipp
ensure_strimzi_operator
delete_topics
uninstall_active_release zipp-infra zipp-infra
wait_for_strimzi_resources
uninstall_active_release monitoring zipp-observability
uninstall_active_release strimzi-operator zipp-infra

log 'Deleting Zipp namespaces, including retained PVCs and data'
k delete namespace zipp zipp-infra zipp-observability --ignore-not-found --wait=false
for namespace in zipp zipp-infra zipp-observability; do
  namespace_exists "$namespace" || continue
  if ! k wait --for=delete "namespace/$namespace" --timeout=5m; then
    if [[ "$namespace" == zipp-infra ]]; then
      delete_topics
      k wait --for=delete "namespace/$namespace" --timeout=2m && continue
    fi
    k describe namespace "$namespace" || true
    die "Namespace $namespace is still terminating; inspect its remaining resources and finalizers"
  fi
done

# A Retain PV would preserve data outside its deleted namespace. Stop before
# installing a new stack if any former Zipp claim still has a cluster PV.
for ((attempt = 0; attempt < 24; attempt++)); do
  stale_pvs="$(k get pv -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.claimRef.namespace}{"\n"}{end}' \
    | awk '$2 == "zipp" || $2 == "zipp-infra" || $2 == "zipp-observability" {print $1}')"
  [[ -z "$stale_pvs" ]] && break
  sleep 5
done
[[ -z "$stale_pvs" ]] || die "Old Zipp PVs still exist: $stale_pvs (inspect reclaim policy and storage before retrying)"

log 'Installing the stack with K3s storage'
make --old-file=cluster-up infra-ready \
  "PROFILE=$context" \
  "PROMETHEUS_STORAGE_CLASS=$storage_class" \
  "IMAGE_TAG=$tag" \
  "FRONTEND_IMAGE_TAG=$tag"

log 'Checking application and Prometheus readiness'
k rollout status deployment/zipp-app --namespace zipp --timeout=5m
k rollout status deployment/zipp-app-ui --namespace zipp --timeout=5m
k wait --for=condition=complete job/zipp-app-migrate --namespace zipp --timeout=5m
k get prometheus.monitoring.coreos.com monitoring-kube-prometheus-prometheus \
  --namespace zipp-observability -o name >/dev/null

prometheus_ready=false
for ((attempt = 0; attempt < 120; attempt++)); do
  pvc_states="$(k get pvc --namespace zipp-observability \
    -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.phase}{"\n"}{end}')"
  endpoints="$(k get endpointslices.discovery.k8s.io --namespace zipp-observability \
    -l kubernetes.io/service-name=monitoring-kube-prometheus-prometheus \
    -o jsonpath='{range .items[*].endpoints[*]}{.conditions.ready}{"\n"}{end}')"
  if printf '%s\n' "$pvc_states" | awk '$1 ~ /prometheus/ && $2 == "Bound" {found=1} END {exit !found}'; then
    pvc_ready=true
  else
    pvc_ready=false
  fi
  if [[ "$pvc_ready" == true && "$endpoints" == *true* ]]; then
    prometheus_ready=true
    break
  fi
  sleep 5
done
if [[ "$prometheus_ready" != true ]]; then
  k get prometheus,statefulset,pod,pvc,endpointslices --namespace zipp-observability -o wide || true
  k logs deployment/monitoring-kube-prometheus-operator --namespace zipp-observability --tail=100 || true
  die 'Prometheus has no Bound PVC and ready Service endpoint'
fi

log 'Rebuild complete'
printf 'Images: zipp:%s, zipp-ui:%s\n' "$tag" "$tag"
printf 'Restart local forwards on EC2: make port-forward-all PROFILE=%s\n' "$context"
