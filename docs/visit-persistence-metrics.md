# Visit persistence metrics

The application dashboard's **Visit Event to Persist Latency** panel shows
p50, p95, and p99 derived from `visit_event_to_persist_seconds`. Each sample
starts at the event's `visited_at` timestamp, set immediately before producer
enqueue, and ends when the consumer's successful database write returns. This
includes enqueue, Kafka transport and queueing, and consumer processing; it does
not include the complete client redirect request or independently verify when
another database client can observe the row.

Only successful writes with valid timestamps are observed. Failed, lost,
undelivered, or still queued events do not appear in the latency histogram,
and duplicate deliveries can add samples. A low latency percentile therefore
does not prove complete delivery. Compare the panel with publish, processing,
and error metrics and the Kafka consumer lag metric; missing data is not zero
lag. The infrastructure chart configures a Strimzi Kafka Exporter and
ServiceMonitor, but the exporter and its scrape must be verified after the
infrastructure and observability releases are updated.

The measurement uses producer and consumer wall clocks. They must be
synchronized when deployed across machines. Naive timestamps and timestamps in
the future are excluded and counted by
`visit_event_to_persist_invalid_timestamp_total` with a bounded `reason` label.
Histogram buckets extend to 30 minutes; values beyond the highest finite bucket
cannot provide a precise tail estimate. This instrumentation does not make
visit processing idempotent or guarantee event delivery.
