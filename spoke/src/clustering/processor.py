import json
import logging
import numpy as np
from sklearn.cluster import DBSCAN
from rich.logging import RichHandler
from rich.console import Console

from api.models import TelemetryMessage
from shared.kafka_utils import get_consumer, get_producer, delivery_report, TOPIC_TELEMETRY_RAW, TOPIC_TELEMETRY_CURATED

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("mahoraga-clustering")
console = Console()

BUFFER_SIZE = 10   # Reduced for faster feedback in CI and local dev
EPS = 0.5          # DBSCAN epsilon: distance threshold for a neighborhood
MIN_SAMPLES = 5    # Minimum samples to form a cluster

# Initialize Kafka
producer = get_producer()

def run_clustering_processor():
    """
    Consumes raw telemetry, clusters embeddings, and forwards curated samples to the Hub.
    """
    console.print("[bold yellow]Mahoraga Clustering Processor Starting...[/bold yellow]")
    
    consumer = get_consumer(group_id="clustering-group", topics=[TOPIC_TELEMETRY_RAW])
    
    buffer = []
    
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.error(f"Consumer error: {msg.error()}")
                continue
            
            # 1. Decode message
            try:
                data = json.loads(msg.value().decode('utf-8'))
                telemetry = TelemetryMessage(**data)
                buffer.append(telemetry)
            except Exception as e:
                logger.error(f"Failed to parse telemetry: {e}")
                continue
            
            # 2. Process Buffer when full
            if len(buffer) >= BUFFER_SIZE:
                perform_clustering(buffer)
                buffer = [] # Clear buffer after processing
                
    except KeyboardInterrupt:
        logger.info("Shutting down clustering processor...")
    finally:
        consumer.close()
        producer.flush()

def perform_clustering(telemetry_list: list[TelemetryMessage]):
    """
    Runs DBSCAN on the latent embeddings and selects representative 'Core' samples for the Hub.
    """
    if not telemetry_list:
        logger.warning("Empty batch received for clustering. Skipping.")
        return

    logger.info(f"Processing batch of {len(telemetry_list)} embeddings...")
    
    try:
        # 1. Extract and Validate dimensions
        embeddings = np.array([t.data.embedding for t in telemetry_list])
        
        if embeddings.ndim != 2:
            logger.error(f"Invalid embedding dimensions: {embeddings.shape}")
            return
            
        # 2. Run DBSCAN
        clustering = DBSCAN(eps=EPS, min_samples=MIN_SAMPLES, metric='cosine').fit(embeddings)
        labels = clustering.labels_
        
        unique_labels = set(labels)
        n_clusters = len(unique_labels) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)
        
        logger.info(f"Found {n_clusters} clusters and {n_noise} noise points.")
        
        # Handle Noise (Anomalies)
        processed_count = 0
        for i, label in enumerate(labels):
            if label == -1:
                forward_to_hub(telemetry_list[i], is_anomaly=True)
                processed_count += 1
                
        # Handle Clusters (Redundancy)
        for label in unique_labels:
            if label == -1:
                continue
            
            indices = np.where(labels == label)[0]
            rep_idx = indices[0]
            forward_to_hub(telemetry_list[rep_idx], is_anomaly=False)
            processed_count += 1

        logger.info(f"Forwarded {processed_count} curated samples to the Global Hub.")

    except Exception as e:
        logger.error(f"Clustering algorithm failure: {e}")

def forward_to_hub(telemetry: TelemetryMessage, is_anomaly: bool):
    """Produces a curated message to the Kafka topic destined for the Global Hub."""
    payload = telemetry.model_dump()
    payload["is_anomaly"] = is_anomaly
    
    producer.produce(
        TOPIC_TELEMETRY_CURATED,
        key=telemetry.device_id,
        value=json.dumps(payload),
        callback=delivery_report
    )
    producer.poll(0)

if __name__ == "__main__":
    run_clustering_processor()
