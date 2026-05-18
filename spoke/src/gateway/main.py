import json
import logging
import time
from rich.logging import RichHandler
from rich.console import Console
import paho.mqtt.client as mqtt

from api.models import TelemetryMessage
from shared.kafka_utils import get_producer, delivery_report, TOPIC_TELEMETRY_RAW, create_topics

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("mahoraga-spoke")
console = Console()

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "mahoraga/telemetry/#"

# Initialize Kafka Producer
producer = get_producer()

# ─── MQTT Callbacks ───────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("[bold green]✓ Connected to MQTT Broker[/bold green]", extra={"markup": True})
        client.subscribe(MQTT_TOPIC)
    else:
        logger.error(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        # 1. Decode and basic JSON check
        raw_payload = msg.payload.decode()
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            logger.warning(f"[bold red]Discarded malformed JSON[/bold red] from topic {msg.topic}", extra={"markup": True})
            return

        # 2. Schema Validation (Pydantic)
        try:
            telemetry = TelemetryMessage(**payload)
        except Exception as ve:
            logger.warning(f"[yellow]Schema mismatch from {msg.topic}: {ve}[/yellow]", extra={"markup": True})
            return
        
        logger.info(
            f"[cyan]Validated {telemetry.device_id}[/cyan]: pred={telemetry.inference.prediction}",
            extra={"markup": True}
        )
        
        # 3. Forward to Kafka with a timeout guard
        producer.produce(
            TOPIC_TELEMETRY_RAW,
            key=telemetry.device_id,
            value=telemetry.model_dump_json(),
            callback=delivery_report
        )
        producer.poll(0)
        
    except Exception as e:
        logger.error(f"[bold red]Critical pipeline failure:[/bold red] {str(e)}", extra={"markup": True})

def run_gateway():
    console.print("[bold blue]Mahoraga Spoke Gateway Starting...[/bold blue]")
    
    # 0. Ensure Infrastructure is ready (Create topics)
    try:
        create_topics()
    except Exception as e:
        logger.warning(f"Initial topic creation failed: {e}. Will retry on produce.")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Enable automatic reconnection logic
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_forever()
        except Exception as e:
            logger.error(f"MQTT connection lost: {e}. Retrying in 5s...")
            time.sleep(5)
        finally:
            producer.flush()

if __name__ == "__main__":
    run_gateway()
