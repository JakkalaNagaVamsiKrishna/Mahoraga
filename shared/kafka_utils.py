import os
from confluent_kafka import Producer, Consumer
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.error import KafkaException, KafkaError
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_TELEMETRY_RAW = "mahoraga.telemetry.raw"
TOPIC_TELEMETRY_CURATED = "mahoraga.telemetry.curated"

# Singleton Producer instance
_PRODUCER = None

def create_topics():
    """Ensure required topics exist in Redpanda/Kafka."""
    admin = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
    
    # Configuration for production-readiness, fallback to dev defaults
    num_partitions = int(os.getenv("KAFKA_NUM_PARTITIONS", "1"))
    replication_factor = int(os.getenv("KAFKA_REPLICATION_FACTOR", "1"))

    new_topics = [
        NewTopic(TOPIC_TELEMETRY_RAW, num_partitions=num_partitions, replication_factor=replication_factor),
        NewTopic(TOPIC_TELEMETRY_CURATED, num_partitions=num_partitions, replication_factor=replication_factor)
    ]
    
    fs = admin.create_topics(new_topics)
    for topic, f in fs.items():
        try:
            f.result() # Wait for creation
            logger.info(f"Topic {topic} initialized.")
        except KafkaException as e:
            if e.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                logger.debug(f"Topic {topic} already exists — skipping.")
            else:
                logger.error(f"Failed to create topic {topic}: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error creating topic {topic}: {e}")
            raise

def get_producer():
    """Build a Kafka producer with standard enterprise settings (Singleton)."""
    global _PRODUCER
    if _PRODUCER is None:
        conf = {
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'client.id': 'mahoraga-producer',
            'enable.idempotence': True,     # Enforces acks=all, retries, and ordering
        }
        _PRODUCER = Producer(conf)
    return _PRODUCER

def delivery_report(err, msg):
    """Callback for producer delivery status."""
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

def get_consumer(group_id: str, topics: list[str]):
    """Build a Kafka consumer with manual commit enabled for safety."""
    conf = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': group_id,
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,    # Manual commit after processing to avoid loss
    }
    consumer = Consumer(conf)
    consumer.subscribe(topics)
    return consumer
