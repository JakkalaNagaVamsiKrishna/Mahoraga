import os
import logging
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import paho.mqtt.client as mqtt
from rich.logging import RichHandler
from rich.console import Console

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("mahoraga-ota")
console = Console()

# Path to the outputs directory where newly distilled models are saved
MODEL_REGISTRY_DIR = Path("hub/storage/registry")
MODEL_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = 1883
MQTT_CONTROL_TOPIC = "mahoraga/control/update"

# ─── MQTT Client ──────────────────────────────────────────────────────────────

mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect MQTT
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        logger.info(f"[bold green]✓ OTA Orchestrator connected to MQTT at {MQTT_BROKER}[/bold green]", extra={"markup": True})
    except Exception as e:
        logger.error(f"Failed to connect to MQTT: {e}")
    yield
    # Shutdown
    mqtt_client.disconnect()

app = FastAPI(title="Mahoraga OTA Orchestrator", lifespan=lifespan)

# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.get("/models/{version}")
async def get_model(version: str):
    """Endpoint for edge devices to download the new ONNX model."""
    model_path = MODEL_REGISTRY_DIR / f"student_{version}.onnx"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model version not found in registry")
    
    return FileResponse(path=model_path, filename=f"student_{version}.onnx")

@app.post("/rollout/{version}")
async def trigger_rollout(version: str):
    """
    Triggers a fleet-wide update. 
    In a real scenario, this would support phased rollouts (10%, 50%, 100%).
    """
    model_path = MODEL_REGISTRY_DIR / f"student_{version}.onnx"
    if not model_path.exists():
        raise HTTPException(status_code=400, detail="Cannot rollout a non-existent model version")

    # Command payload for the C++ Edge Engine
    payload = {
        "version": version,
        "url": f"http://{os.getenv('OTA_HOST', 'localhost')}:8000/models/{version}",
        "command": "HOT_SWAP"
    }

    mqtt_client.publish(MQTT_CONTROL_TOPIC, json.dumps(payload))
    
    logger.info(f"[bold magenta]ROLLOUT TRIGGERED:[/bold magenta] Version {version} pushed to fleet.", extra={"markup": True})
    return {"status": "success", "pushed_version": version, "target_topic": MQTT_CONTROL_TOPIC}

@app.get("/health")
def health():
    return {"status": "active", "registry_count": len(list(MODEL_REGISTRY_DIR.glob("*.onnx")))}

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    console.print("[bold red]Mahoraga OTA Orchestrator Launching...[/bold red]")
    uvicorn.run(app, host="0.0.0.0", port=8000)
