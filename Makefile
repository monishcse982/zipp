SHELL := /bin/bash
.DEFAULT_GOAL := help
.NOTPARALLEL:

PROFILE ?= minikube
NAMESPACE ?= zipp
INFRA_NAMESPACE ?= zipp-infra
RELEASE ?= zipp-app
INFRA_RELEASE ?= zipp-infra
IMAGE ?= zipp
IMAGE_TAG ?= local
FRONTEND_IMAGE ?= zipp-ui
FRONTEND_IMAGE_TAG ?= local
ENV_FILE ?= .env.kubernetes
LOCAL_PORT ?= $(or $(shell awk -F= '$$1 == "APP_PORT" { print $$2; exit }' $(ENV_FILE) 2>/dev/null),8000)
POSTGRES_LOCAL_PORT ?= 5433
VALKEY_LOCAL_PORT ?= 6380

MINIKUBE_CPUS ?= 4
MINIKUBE_MEMORY ?= 8192
MINIKUBE_DISK_SIZE ?= 25g
MINIKUBE_DRIVER ?= docker

APP_CHART := deploy/charts/zipp-app
INFRA_CHART := deploy/charts/zipp-infra
OBSERVABILITY_CHART := deploy/charts/zipp-observability
RENDERED_APP_MANIFEST := /tmp/zipp-app-rendered.yaml
RENDERED_INFRA_MANIFEST := /tmp/zipp-infra-rendered.yaml
RENDERED_OBSERVABILITY_MANIFEST := /tmp/zipp-observability-rendered.yaml
KUBECTL := kubectl --context $(PROFILE)
HELM_CONTEXT := --kube-context $(PROFILE)
POSTGRES_SECRET := zipp-postgresql
POSTGRES_STATEFULSET := $(INFRA_RELEASE)-postgresql
FRONTEND_SERVICE := $(RELEASE)-ui
VALKEY_SECRET := zipp-valkey
VALKEY_DEPLOYMENT := valkey
STRIMZI_RELEASE := strimzi-operator
STRIMZI_CHART := oci://quay.io/strimzi-helm/strimzi-kafka-operator
STRIMZI_VERSION := 1.2.0
STRIMZI_VALUES := deploy/kafka/strimzi-operator-values.yaml
KAFKA_CLUSTER := zipp
KAFKA_USER := zipp-user
MONITORING_NAMESPACE ?= zipp-observability
MONITORING_RELEASE ?= monitoring
SCRAPE_INTERVAL ?= 15s
GRAFANA_SERVICE := $(MONITORING_RELEASE)-grafana
PROMETHEUS_SERVICE := $(MONITORING_RELEASE)-kube-prometheus-prometheus
GRAFANA_PORT ?= 3000
PROMETHEUS_PORT ?= 9090
PORT_FORWARD_FRONTEND ?= 1
APP_HELM_IMAGE_ARGS = --set-string image.repository=$(IMAGE) --set-string image.tag=$(IMAGE_TAG) --set-string frontend.image.repository=$(FRONTEND_IMAGE) --set-string frontend.image.tag=$(FRONTEND_IMAGE_TAG)

.PHONY: help unit-test coverage app-up app-start frontend-deps frontend-env-check infra-up infra-start infra-stop infra-status cluster-up cluster-stop cluster-status image-build image-load validate-env namespace infra-namespace secret postgres-secret valkey-secret kafka-operator monitoring-install monitoring-status grafana-password postgres-password valkey-password kafka-password prometheus-password grafana-forward prometheus-forward chart-deps chart-validate deploy deploy-infra deploy-app wait-infra wait-app sync-kafka-password infra-ready migration-status status logs port-forward port-forward-app port-forward-all diagnose-port-forward restart uninstall cluster-delete makemigrations migrate

help: ## Show the available commands.
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target> [VARIABLE=value]\n\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf "\nCommon overrides:\n"
	@printf "  PROFILE=%s NAMESPACE=%s INFRA_NAMESPACE=%s ENV_FILE=%s LOCAL_PORT=%s\n" "$(PROFILE)" "$(NAMESPACE)" "$(INFRA_NAMESPACE)" "$(ENV_FILE)" "$(LOCAL_PORT)"

unit-test: ## Run unit tests while collecting line and branch coverage.
	uv run --locked coverage run -m unittest discover -s tests/unit -v

coverage: unit-test ## Run unit tests and print the coverage summary.
	uv run --locked coverage report

app-up: frontend-env-check infra-up ## Deploy the stack and serve the UI at localhost:5173; Ctrl+C stops local forwards.
	PORT_FORWARD_CORE_ONLY=1 $(MAKE) port-forward-all

app-start: frontend-env-check infra-start ## Resume an existing Minikube stack and serve the UI without rebuilding or redeploying.
	$(KUBECTL) rollout status --namespace $(NAMESPACE) deployment/$(RELEASE) --timeout=5m
	$(KUBECTL) rollout status --namespace $(NAMESPACE) deployment/$(FRONTEND_SERVICE) --timeout=5m
	PORT_FORWARD_CORE_ONLY=1 $(MAKE) port-forward-all

frontend-deps: ## Install locked frontend dependencies if they are missing.
	@test -d frontend/node_modules || npm --prefix frontend ci

frontend-env-check: ## Validate local UI and API configuration before startup.
	ENV_FILE="$(ENV_FILE)" LOCAL_PORT="$(LOCAL_PORT)" python3 scripts/check-local-app-config.py

infra-up: image-load infra-ready status ## Start Minikube and deploy the complete application stack.

infra-start: cluster-up status ## Start the existing Minikube profile without rebuilding.

infra-stop: cluster-stop ## Stop Minikube while preserving cluster data.

infra-status: cluster-status status monitoring-status ## Show Minikube, Helm, and Kubernetes status.

cluster-up: ## Create or start the Minikube profile.
	minikube start --profile $(PROFILE) --driver $(MINIKUBE_DRIVER) --cpus $(MINIKUBE_CPUS) --memory $(MINIKUBE_MEMORY) --disk-size $(MINIKUBE_DISK_SIZE)
	minikube update-context --profile $(PROFILE)

cluster-stop: ## Stop the Minikube profile without deleting it.
	minikube stop --profile $(PROFILE)

cluster-status: ## Show Minikube and Kubernetes node status.
	minikube status --profile $(PROFILE)
	$(KUBECTL) get nodes -o wide

image-build: frontend-env-check ## Build the API and static UI images.
	docker build -t $(IMAGE):$(IMAGE_TAG) .
	python3 scripts/build-frontend-image.py "$(FRONTEND_IMAGE):$(FRONTEND_IMAGE_TAG)"

image-load: cluster-up image-build ## Load the application image into Minikube.
	minikube image load $(IMAGE):$(IMAGE_TAG) --profile $(PROFILE)
	minikube image load $(FRONTEND_IMAGE):$(FRONTEND_IMAGE_TAG) --profile $(PROFILE)
	@minikube image ls --profile $(PROFILE) | grep -F "$(IMAGE):$(IMAGE_TAG)"
	@minikube image ls --profile $(PROFILE) | grep -F "$(FRONTEND_IMAGE):$(FRONTEND_IMAGE_TAG)"

validate-env: ## Check that the env file exists and contains no duplicate keys.
	@test -f "$(ENV_FILE)" || { echo "Missing environment file: $(ENV_FILE)"; exit 1; }
	@duplicates=$$(awk -F= '/^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=/ { key=$$1; sub(/^[[:space:]]*export[[:space:]]+/, "", key); gsub(/[[:space:]]/, "", key); count[key]++ } END { for (key in count) if (count[key] > 1) print key " (" count[key] " definitions)" }' "$(ENV_FILE)"); if [ -n "$$duplicates" ]; then echo "Duplicate environment keys found:"; echo "$$duplicates"; exit 1; fi

namespace: cluster-up ## Create the application namespace when it does not exist.
	$(KUBECTL) create namespace $(NAMESPACE) --dry-run=client -o yaml | $(KUBECTL) apply -f -

infra-namespace: cluster-up ## Create the infrastructure namespace when it does not exist.
	$(KUBECTL) create namespace $(INFRA_NAMESPACE) --dry-run=client -o yaml | $(KUBECTL) apply -f -

secret: namespace validate-env ## Create or update the application Secret from the env file.
	$(KUBECTL) create secret generic zipp-env --namespace $(NAMESPACE) --from-env-file=$(ENV_FILE) --dry-run=client -o yaml | $(KUBECTL) apply -f -

postgres-secret: infra-namespace validate-env ## Create PostgreSQL credentials in the infrastructure namespace.
	@database_url=$$(awk -F= '$$1 == "DATABASE_URL" { print substr($$0, index($$0, "=") + 1); exit }' "$(ENV_FILE)"); password=$$(printf '%s' "$$database_url" | sed -E 's#^[^:]+://[^:]+:([^@]+)@.*#\1#'); if [ -z "$$password" ] || [ "$$password" = "$$database_url" ]; then echo "Could not extract the PostgreSQL password from DATABASE_URL"; exit 1; fi; $(KUBECTL) create secret generic $(POSTGRES_SECRET) --namespace $(INFRA_NAMESPACE) --from-literal=postgres-password="$$password" --from-literal=password="$$password" --dry-run=client -o yaml | $(KUBECTL) apply -f -

valkey-secret: infra-namespace validate-env ## Create Valkey credentials in the infrastructure namespace.
	@cache_url=$$(awk -F= '$$1 == "CACHE_URL" { print substr($$0, index($$0, "=") + 1); exit }' "$(ENV_FILE)"); password=$$(printf '%s' "$$cache_url" | sed -E 's#^[^:]+://([^:]*:)?([^@]+)@.*#\2#'); if [ -z "$$password" ] || [ "$$password" = "$$cache_url" ]; then echo "Could not extract the Valkey password from CACHE_URL"; exit 1; fi; $(KUBECTL) create secret generic $(VALKEY_SECRET) --namespace $(INFRA_NAMESPACE) --from-literal=default="$$password" --dry-run=client -o yaml | $(KUBECTL) apply -f -

kafka-operator: infra-namespace ## Install or upgrade the Strimzi Kafka operator.
	helm upgrade --install $(STRIMZI_RELEASE) $(STRIMZI_CHART) $(HELM_CONTEXT) --version $(STRIMZI_VERSION) --namespace $(INFRA_NAMESPACE) --values $(STRIMZI_VALUES) --wait --timeout 10m

monitoring-install: cluster-up ## Install or upgrade Prometheus and Grafana.
	helm upgrade --install $(MONITORING_RELEASE) $(OBSERVABILITY_CHART) $(HELM_CONTEXT) --namespace $(MONITORING_NAMESPACE) --create-namespace --set kube-prometheus-stack.prometheus.prometheusSpec.scrapeInterval=$(SCRAPE_INTERVAL) --set kube-prometheus-stack.prometheus.prometheusSpec.evaluationInterval=$(SCRAPE_INTERVAL) --wait --timeout 15m

monitoring-status: ## Show Prometheus and Grafana resources.
	helm list $(HELM_CONTEXT) --namespace $(MONITORING_NAMESPACE)
	$(KUBECTL) get pods,services --namespace $(MONITORING_NAMESPACE) -o wide

grafana-password: ## Print the local Grafana username and generated password.
	@printf "Username: "; $(KUBECTL) get secret $(GRAFANA_SERVICE) --namespace $(MONITORING_NAMESPACE) -o jsonpath='{.data.admin-user}' | base64 --decode; printf '\n'
	@printf "Password: "; $(KUBECTL) get secret $(GRAFANA_SERVICE) --namespace $(MONITORING_NAMESPACE) -o jsonpath='{.data.admin-password}' | base64 --decode; printf '\n'

postgres-password: ## Print the PostgreSQL application username and password.
	@set -o pipefail; printf 'Username: zipp_user\nPassword: '; $(KUBECTL) get secret $(POSTGRES_SECRET) --namespace $(INFRA_NAMESPACE) -o jsonpath='{.data.password}' | base64 --decode || exit $$?; printf '\n'

valkey-password: ## Print the Valkey password.
	@set -o pipefail; printf 'Password: '; $(KUBECTL) get secret $(VALKEY_SECRET) --namespace $(INFRA_NAMESPACE) -o jsonpath='{.data.default}' | base64 --decode || exit $$?; printf '\n'

kafka-password: ## Print the Kafka application username and generated password.
	@set -o pipefail; printf 'Username: $(KAFKA_USER)\nPassword: '; $(KUBECTL) get secret $(KAFKA_USER) --namespace $(INFRA_NAMESPACE) -o jsonpath='{.data.password}' | base64 --decode || exit $$?; printf '\n'

prometheus-password: ## Explain local Prometheus access (no password configured).
	@echo 'Prometheus has no password in the local stack; use make prometheus-forward.'

grafana-forward: ## Forward Grafana to localhost.
	@echo "Grafana: http://localhost:$(GRAFANA_PORT)"
	$(KUBECTL) port-forward --namespace $(MONITORING_NAMESPACE) service/$(GRAFANA_SERVICE) $(GRAFANA_PORT):80

prometheus-forward: ## Forward Prometheus to localhost.
	@echo "Prometheus: http://localhost:$(PROMETHEUS_PORT)"
	$(KUBECTL) port-forward --namespace $(MONITORING_NAMESPACE) service/$(PROMETHEUS_SERVICE) $(PROMETHEUS_PORT):9090

chart-deps: ## Refresh infrastructure and observability chart dependencies and lock files.
	helm dependency update $(INFRA_CHART)
	helm dependency list $(INFRA_CHART)
	helm dependency update $(OBSERVABILITY_CHART)
	helm dependency list $(OBSERVABILITY_CHART)

chart-validate: ## Build dependencies, lint all charts, and render all releases.
	helm dependency build $(INFRA_CHART)
	helm dependency build $(OBSERVABILITY_CHART)
	helm lint $(APP_CHART)
	helm lint $(INFRA_CHART)
	helm lint $(OBSERVABILITY_CHART)
	helm template $(RELEASE) $(APP_CHART) $(HELM_CONTEXT) --namespace $(NAMESPACE) $(APP_HELM_IMAGE_ARGS) --set monitoring.serviceMonitor.interval=$(SCRAPE_INTERVAL) > $(RENDERED_APP_MANIFEST)
	helm template $(INFRA_RELEASE) $(INFRA_CHART) $(HELM_CONTEXT) --namespace $(INFRA_NAMESPACE) --set valkey.metrics.serviceMonitor.interval=$(SCRAPE_INTERVAL) > $(RENDERED_INFRA_MANIFEST)
	helm template $(MONITORING_RELEASE) $(OBSERVABILITY_CHART) $(HELM_CONTEXT) --namespace $(MONITORING_NAMESPACE) --set kube-prometheus-stack.prometheus.prometheusSpec.scrapeInterval=$(SCRAPE_INTERVAL) --set kube-prometheus-stack.prometheus.prometheusSpec.evaluationInterval=$(SCRAPE_INTERVAL) > $(RENDERED_OBSERVABILITY_MANIFEST)

deploy-infra: chart-validate postgres-secret valkey-secret kafka-operator monitoring-install ## Install or upgrade PostgreSQL, Valkey, Kafka, and observability.
	helm upgrade --install $(INFRA_RELEASE) $(INFRA_CHART) $(HELM_CONTEXT) --namespace $(INFRA_NAMESPACE) --set valkey.metrics.serviceMonitor.interval=$(SCRAPE_INTERVAL) --timeout 5m

wait-infra: deploy-infra ## Wait for infrastructure dependencies and Kafka resources.
	$(KUBECTL) rollout status statefulset/$(POSTGRES_STATEFULSET) --namespace $(INFRA_NAMESPACE) --timeout=10m
	$(KUBECTL) rollout status deployment/$(VALKEY_DEPLOYMENT) --namespace $(INFRA_NAMESPACE) --timeout=5m
	$(KUBECTL) wait kafka/$(KAFKA_CLUSTER) --namespace $(INFRA_NAMESPACE) --for=condition=Ready --timeout=10m
	$(KUBECTL) wait kafkauser/$(KAFKA_USER) --namespace $(INFRA_NAMESPACE) --for=condition=Ready --timeout=5m
	$(KUBECTL) wait kafkatopic/link-visited --namespace $(INFRA_NAMESPACE) --for=condition=Ready --timeout=5m
	$(KUBECTL) wait kafkatopic/link-visited-dlq --namespace $(INFRA_NAMESPACE) --for=condition=Ready --timeout=5m

sync-kafka-password: wait-infra secret ## Copy Kafka credentials into the app namespace Secret.
	@password_b64=$$($(KUBECTL) get secret $(KAFKA_USER) --namespace $(INFRA_NAMESPACE) -o jsonpath='{.data.password}'); if [ -z "$$password_b64" ]; then echo "Kafka password was not generated"; exit 1; fi; $(KUBECTL) patch secret zipp-env --namespace $(NAMESPACE) --type=merge -p '{"data":{"KAFKA_PASSWORD":"'"$$password_b64"'"}}' >/dev/null; echo "Kafka password synchronized to zipp-env"

deploy-app: sync-kafka-password ## Install or upgrade the API and UI in the app namespace.
	helm upgrade --install $(RELEASE) $(APP_CHART) $(HELM_CONTEXT) --namespace $(NAMESPACE) $(APP_HELM_IMAGE_ARGS) --set monitoring.serviceMonitor.interval=$(SCRAPE_INTERVAL) --timeout 5m

deploy: deploy-app ## Deploy infrastructure first, then the application.

wait-app: deploy-app ## Wait for app migrations and API/UI readiness.
	$(KUBECTL) wait --namespace $(NAMESPACE) --for=condition=complete job/$(RELEASE)-migrate --timeout=5m
	$(KUBECTL) rollout status deployment/$(RELEASE) --namespace $(NAMESPACE) --timeout=5m
	$(KUBECTL) rollout status deployment/$(FRONTEND_SERVICE) --namespace $(NAMESPACE) --timeout=5m

infra-ready: deploy wait-app restart ## Wait for infrastructure, deploy app, and restart to pick up Secrets.

migration-status: ## Show migration versions recorded in the cluster database.
	$(KUBECTL) exec --namespace $(INFRA_NAMESPACE) statefulset/$(POSTGRES_STATEFULSET) -- sh -ec 'export PGPASSWORD="$$(cat /opt/bitnami/postgresql/secrets/password)"; psql -h 127.0.0.1 -U zipp_user -d zipp -c "SELECT app, name, applied_at FROM tortoise_migrations ORDER BY applied_at"'

status: ## Show app and infrastructure resources.
	helm list $(HELM_CONTEXT) --namespace $(NAMESPACE)
	$(KUBECTL) get deployment,statefulset,job,pods,services,pvc --namespace $(NAMESPACE) -o wide
	helm list $(HELM_CONTEXT) --namespace $(INFRA_NAMESPACE)
	$(KUBECTL) get deployment,statefulset,pods,services,pvc --namespace $(INFRA_NAMESPACE) -o wide
	$(KUBECTL) get kafka,kafkauser,kafkatopic --namespace $(INFRA_NAMESPACE)

logs: ## Follow application logs.
	$(KUBECTL) logs --namespace $(NAMESPACE) deployment/$(RELEASE) --all-containers=true --tail=200 --follow

port-forward: port-forward-all ## Forward the application and local development dependencies.

port-forward-app: ## Forward only the application Service to localhost.
	@echo "Application: http://localhost:$(LOCAL_PORT)"
	@echo "Metrics:     http://localhost:$(LOCAL_PORT)/metrics"
	@echo "FastAPI:     http://localhost:$(LOCAL_PORT)/docs"
	$(KUBECTL) port-forward --namespace $(NAMESPACE) service/$(RELEASE) $(LOCAL_PORT):8000

port-forward-all: ## Serve the UI and forward app, Postgres, Valkey, Grafana, and Prometheus.
	PORT_FORWARD_CONTEXT="$(PROFILE)" \
	PORT_FORWARD_NAMESPACE="$(NAMESPACE)" \
	PORT_FORWARD_INFRA_NAMESPACE="$(INFRA_NAMESPACE)" \
	PORT_FORWARD_MONITORING_NAMESPACE="$(MONITORING_NAMESPACE)" \
	PORT_FORWARD_RELEASE="$(RELEASE)" \
	PORT_FORWARD_INFRA_RELEASE="$(INFRA_RELEASE)" \
	PORT_FORWARD_FRONTEND_SERVICE="$(FRONTEND_SERVICE)" \
	PORT_FORWARD_GRAFANA_SERVICE="$(GRAFANA_SERVICE)" \
	PORT_FORWARD_PROMETHEUS_SERVICE="$(PROMETHEUS_SERVICE)" \
	PORT_FORWARD_APP_LOCAL_PORT="$(LOCAL_PORT)" \
	PORT_FORWARD_POSTGRES_LOCAL_PORT="$(POSTGRES_LOCAL_PORT)" \
	PORT_FORWARD_VALKEY_LOCAL_PORT="$(VALKEY_LOCAL_PORT)" \
	PORT_FORWARD_GRAFANA_LOCAL_PORT="$(GRAFANA_PORT)" \
	PORT_FORWARD_PROMETHEUS_LOCAL_PORT="$(PROMETHEUS_PORT)" \
	PORT_FORWARD_FRONTEND_LOCAL_PORT=5173 \
	PORT_FORWARD_FRONTEND="$(PORT_FORWARD_FRONTEND)" \
	bash scripts/port-forward-all.sh

diagnose-port-forward: ## Inspect app pod health, endpoints, recent events, and logs after a forwarding reset.
	$(KUBECTL) get pods --namespace $(NAMESPACE) -o wide
	$(KUBECTL) get endpoints --namespace $(NAMESPACE) $(RELEASE) $(FRONTEND_SERVICE) -o wide
	$(KUBECTL) get pods,services,endpoints --namespace $(INFRA_NAMESPACE) -o wide
	$(KUBECTL) get events --namespace $(NAMESPACE) --sort-by=.lastTimestamp | tail -n 20
	-$(KUBECTL) logs --namespace $(NAMESPACE) deployment/$(RELEASE) --all-containers=true --tail=100
	-$(KUBECTL) logs --namespace $(NAMESPACE) deployment/$(RELEASE) --all-containers=true --previous --tail=100

restart: ## Restart the API and UI Deployments after local image builds.
	$(KUBECTL) rollout restart --namespace $(NAMESPACE) deployment/$(RELEASE)
	$(KUBECTL) rollout restart --namespace $(NAMESPACE) deployment/$(FRONTEND_SERVICE)
	$(KUBECTL) rollout status --namespace $(NAMESPACE) deployment/$(RELEASE) --timeout=5m
	$(KUBECTL) rollout status --namespace $(NAMESPACE) deployment/$(FRONTEND_SERVICE) --timeout=5m

uninstall: ## Uninstall app, infrastructure, and monitoring releases but preserve Minikube.
	-helm uninstall $(RELEASE) $(HELM_CONTEXT) --namespace $(NAMESPACE)
	-helm uninstall $(INFRA_RELEASE) $(HELM_CONTEXT) --namespace $(INFRA_NAMESPACE)
	-helm uninstall $(MONITORING_RELEASE) $(HELM_CONTEXT) --namespace $(MONITORING_NAMESPACE)
	-helm uninstall $(STRIMZI_RELEASE) $(HELM_CONTEXT) --namespace $(INFRA_NAMESPACE)

cluster-delete: ## Delete the complete Minikube profile; requires CONFIRM=delete.
	@test "$(CONFIRM)" = "delete" || { echo "Refusing to delete the cluster. Re-run with CONFIRM=delete"; exit 1; }
	minikube delete --profile $(PROFILE)

makemigrations: ## Creates the migration files based on DB model definitions
	uv run tortoise -c app.core.config.TORTOISE_ORM makemigrations

migrate: ## Applies migrations created by the makemigrations step
	uv run tortoise -c app.core.config.TORTOISE_ORM migrate
