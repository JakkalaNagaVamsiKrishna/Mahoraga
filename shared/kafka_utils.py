import os
from confluent_kafka import Producer, Consumer
import logging

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_TELEMETRY_RAW = "mahoraga.telemetry.raw"
TOPIC_TELEMETRY_CURATED = "mahoraga.telemetry.curated"

def get_producer():
    """Build a Kafka producer with standard enterprise settings."""
    conf = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'client.id': 'mahoraga-producer',
        'acks': 'all',              # Guarantee delivery
        'retries': 5,
        'max.in.flight.requests.per.connection': 5
    }
    return Producer(conf)

def delivery_report(err, msg):
    """Callback for producer delivery status."""
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

def get_consumer(group_id: str, topics: list[str]):
    """Build a Kafka consumer."""
    conf = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': group_id,
        'auto.offset.reset': 'earliest'
    }
    consumer = Consumer(conf)
    consumer.subscribe(topics)
    return consumer
