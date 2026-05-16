import json
import logging
import base64
import time
from pathlib import Path
from rich.logging import RichHandler
from rich.console import Console

from shared.kafka_utils import get_consumer, TOPIC_TELEMETRY_CURATED

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("mahoraga-hub")
console = Console()

STORAGE_DIR = Path("hub/storage/samples")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

TRIGGER_THRESHOLD = 50  # Trigger Kubeflow after 50 high-value anomalies
anomaly_count = 0

def run_sample_collector():
    """
    Global Hub service that collects curated samples and triggers the adaptation pipeline.
    """
    global anomaly_count
    console.print("[bold red]Mahoraga Global Hub Collector Starting...[/bold red]")
    
    consumer = get_consumer(group_id="hub-collector-group", topics=[TOPIC_TELEMETRY_CURATED])
    
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None: continue
            if msg.error():
                logger.error(f"Consumer error: {msg.error()}")
                continue
            
            # 1. Decode Curated Message
            try:
                data = json.loads(msg.value().decode('utf-8'))
                is_anomaly = data.get("is_anomaly", False)
                device_id = data.get("device_id")
                
                # 2. Store Image if present
                if "data" in data and "image_b64" in data["data"] and data["data"]["image_b64"]:
                    save_image(data["data"]["image_b64"], device_id)
                
                # 3. Handle Trigger Logic
                if is_anomaly:
                    anomaly_count += 1
                    logger.info(f"[bold magenta]Anomaly Registered ({anomaly_count}/{TRIGGER_THRESHOLD})[/bold magenta] from {device_id}", extra={"markup": True})
                    
                    if anomaly_count >= TRIGGER_THRESHOLD:
                        trigger_kubeflow_adaptation()
                        anomaly_count = 0 # Reset after trigger
                else:
                    logger.info(f"Routine cluster sample received from {device_id}")
                    
            except Exception as e:
                logger.error(f"Failed to process curated sample: {e}")
                
    except KeyboardInterrupt:
        logger.info("Hub collector shutting down...")
    finally:
        consumer.close()

def save_image(b64_str: str, device_id: str):
    """Saves base64 image to local storage."""
    try:
        img_data = base64.b64decode(b64_str)
        timestamp = int(time.time())
        filename = f"{device_id}_{timestamp}.png"
        filepath = STORAGE_DIR / filename
        
        with open(filepath, "wb") as f:
            f.write(img_data)
        logger.debug(f"Saved anomaly image to {filepath}")
    except Exception as e:
        logger.error(f"Image save failed: {e}")

def trigger_kubeflow_adaptation():
    """
    Mock trigger for the Kubeflow Pipeline.
    In a real scenario, this would use the kfp client to trigger a DAG.
    """
    console.print("\n[bold blink red]!!! DHARMA WHEEL TRIGGERED !!![/bold blink red]", justify="center")
    console.print("[bold yellow]Initiating Global Re-Distillation Pipeline on Kubernetes...[/bold yellow]", justify="center")
    
    # Simulation of API call to Kubeflow
    # client = kfp.Client()
    # client.run_pipeline(...)
    
    logger.info("Pipeline DAG submitted to Kubeflow Controller.")

if __name__ == "__main__":
    import time # Needed for timestamp
    run_sample_collector()
