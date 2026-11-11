import enum

from prometheus_client import Counter, Histogram


class MetricOperation(enum.StrEnum):
    CREATE_LINK = "create_link"
    REDIRECT_LINK = "redirect_link"
    LIST_LINKS = "list_links"
    UPDATE_LINK = "update_link"
    DISABLE_LINK = "disable_link"


class MetricPolicy(enum.StrEnum):
    PUBLIC = "public"
    PASSWORD_PROTECTED = "password_protected"
    IP_RESTRICTED = "ip_restricted"


short_links_creation_requests = Counter(
    "short_links_creation_requests",
    "Total number of short links creation requests",
)

short_links_created = Counter(
    "short_links_created", "Total number of short links created"
)

short_links_creation_error = Counter(
    "short_links_creation_error",
    "Total number of short link creation errors",
    ["error_type"],
)

short_links_create_duration_seconds = Histogram(
    "short_links_create_duration_seconds",
    "Time spent creating short links",
    ["operation", "policy"],
)

short_link_access_request_count = Counter(
    "short_link_access_request_count",
    "Total number of short link access requests",
)

short_link_redirect_duration_seconds = Histogram(
    "short_link_redirect_duration_seconds",
    "Time spent resolving a public short link",
    ["operation", "policy"],
)

list_links_latency_seconds = Histogram(
    "list_links_latency_seconds",
    "Time spent listing links",
    ["operation"],
)
short_link_update_duration_seconds = Histogram(
    "short_link_update_duration_seconds",
    "Time spent updating short links",
    ["operation"],
)

short_link_disable_duration_seconds = Histogram(
    "short_link_disable_duration_seconds",
    "Time spent disabling short links",
    ["operation"],
)

kafka_publish_requests = Counter(
    "kafka_publish_requests",
    "Total number of Kafka publish requests",
    ["topic"],
)

kafka_publish_success = Counter(
    "kafka_publish_success",
    "Total number of Kafka messages delivered successfully",
    ["topic"],
)

kafka_publish_error = Counter(
    "kafka_publish_error",
    "Total number of Kafka publish or delivery errors",
    ["topic", "error_type"],
)

kafka_publish_duration_seconds = Histogram(
    "kafka_publish_duration_seconds",
    "Time spent enqueueing Kafka messages for publish",
    ["topic"],
)

kafka_messages_received = Counter(
    "kafka_messages_received",
    "Total number of Kafka messages received by consumers",
    ["topic"],
)

kafka_messages_processed = Counter(
    "kafka_messages_processed",
    "Total number of Kafka messages processed successfully",
    ["topic"],
)

kafka_message_processing_error = Counter(
    "kafka_message_processing_error",
    "Total number of Kafka message processing errors",
    ["topic", "error_type"],
)

kafka_messages_committed = Counter(
    "kafka_messages_committed",
    "Total number of Kafka messages committed by consumers",
    ["topic"],
)

kafka_messages_dlq = Counter(
    "kafka_messages_dlq",
    "Total number of Kafka messages sent to DLQ",
    ["topic"],
)

kafka_message_processing_duration_seconds = Histogram(
    "kafka_message_processing_duration_seconds",
    "Time spent processing Kafka messages",
    ["topic"],
)

visit_event_to_persist_seconds = Histogram(
    "visit_event_to_persist_seconds",
    "Time from visit event timestamp to successful database write return",
    ["topic"],
    buckets=(
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2.5,
        5,
        10,
        30,
        60,
        120,
        300,
        600,
        1800,
    ),
)

visit_event_to_persist_invalid_timestamp = Counter(
    "visit_event_to_persist_invalid_timestamp",
    "Persisted visits omitted from latency metrics due to invalid event timestamps",
    ["topic", "reason"],
)

time_limited_link_cache_hits = Counter(
    "time_limited_link_cache_hits",
    "Total number of time-limited links successfully served from cache",
)

time_limited_link_cache_misses = Counter(
    "time_limited_link_cache_misses",
    "Total number of time-limited links successfully served from"
    "the database after a cache miss",
)

__all__ = [
    "MetricOperation",
    "MetricPolicy",
    "kafka_message_processing_duration_seconds",
    "kafka_message_processing_error",
    "kafka_messages_committed",
    "kafka_messages_dlq",
    "kafka_messages_processed",
    "kafka_messages_received",
    "kafka_publish_duration_seconds",
    "kafka_publish_error",
    "kafka_publish_requests",
    "kafka_publish_success",
    "short_link_access_request_count",
    "short_link_disable_duration_seconds",
    "short_link_redirect_duration_seconds",
    "short_link_update_duration_seconds",
    "short_links_create_duration_seconds",
    "short_links_created",
    "short_links_creation_error",
    "short_links_creation_requests",
    "time_limited_link_cache_hits",
    "time_limited_link_cache_misses",
    "list_links_latency_seconds",
    "visit_event_to_persist_seconds",
    "visit_event_to_persist_invalid_timestamp",
]
