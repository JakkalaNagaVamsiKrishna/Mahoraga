import json
import logging
from rich.logging import RichHandler
from rich.console import Console
import paho.mqtt.client as mqtt

from api.models import TelemetryMessage

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

# ─── MQTT Callbacks ───────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("[bold green]✓ Connected to MQTT Broker[/bold green]", extra={"markup": True})
        client.subscribe(MQTT_TOPIC)
    else:
        logger.error(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        
        # 1. Validate against Schema
        telemetry = TelemetryMessage(**payload)
        
        logger.info(
            f"[cyan]Message from {telemetry.device_id}[/cyan]: "
            f"pred={telemetry.inference.prediction} "
            f"conf={telemetry.inference.confidence:.2f}",
            extra={"markup": True}
        )
        
        # 2. To be implemented: Latent Clustering logic
        # cluster_and_forward(telemetry)
        
    except Exception as e:
        logger.error(f"[bold red]Error processing message:[/bold red] {str(e)}", extra={"markup": True})

# ─── Main Execution ───────────────────────────────────────────────────────────

def run_gateway():
    console.print("[bold blue]Mahoraga Spoke Gateway Starting...[/bold blue]")
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        logger.fatal(f"Could not start MQTT client: {e}")

if __name__ == "__main__":
    run_gateway()
