# Kafka Consumer Lag

The infrastructure chart enables Strimzi Kafka Exporter and a cluster-internal metrics Service and ServiceMonitor. Strimzi manages the exporter's internal mTLS certificate; no application SCRAM credential is copied into the exporter configuration. The infrastructure dashboard groups `kafka_consumergroup_lag_sum` by consumer group and topic. The configured default visit consumer group is `zipp-visits`, but deployments may override it.

Committed offset lag is a message count, not a duration or proof of persistence. It can be absent when a group has no committed offsets or Prometheus cannot scrape the exporter. Treat missing data as unknown, not zero. A low lag can also coexist with lost or duplicated processing, so reconcile events and rows separately.

## Verify after deployment

The application-only image workflow does not update infrastructure or observability Helm releases. Apply those chart changes through the existing infrastructure deployment workflow before expecting the panel to change. For K3s, ensure the Prometheus storage-class override remains `local-path`.

On the cluster host, verify the exporter and its target:

```bash
kubectl -n zipp-infra rollout status deployment/zipp-kafka-exporter --timeout=5m
kubectl -n zipp-infra get service zipp-kafka-exporter-metrics
kubectl -n zipp-infra get endpointslices \
  -l kubernetes.io/service-name=zipp-kafka-exporter-metrics
kubectl -n zipp-infra get servicemonitor zipp-kafka-exporter
```

From a host with Prometheus forwarded to `127.0.0.1:9090`, query the scrape target and actual committed lag:

```bash
curl --fail --silent --show-error --get \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=up{service="zipp-kafka-exporter-metrics"}'

curl --fail --silent --show-error --get \
  http://127.0.0.1:9090/api/v1/query \
  --data-urlencode 'query=kafka_consumergroup_lag_sum{consumergroup="zipp-visits",topic="link.visited"}'
```

Check for an `up` value of `1`, then generate a visit and verify the consumer commits an offset before expecting a lag series. If no matching series appears, inspect the Prometheus targets page and exporter logs; do not interpret an empty result as healthy lag. These are verification steps, not evidence that the deployed cluster has already been checked.

Strimzi's [Kafka Exporter model for the pinned operator version](https://github.com/strimzi/strimzi-kafka-operator/blob/1.2.0/cluster-operator/src/main/java/io/strimzi/operator/cluster/model/KafkaExporter.java) shows its internal listener and certificate handling.
