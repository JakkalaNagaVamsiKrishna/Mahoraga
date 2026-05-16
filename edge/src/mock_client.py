import json
import time
import random
from datetime import datetime, timezone
import numpy as np
import paho.mqtt.client as mqtt
from rich.console import Console

console = Console()

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "mahoraga/telemetry/mock-node"

LAST_EMBEDDING = None
SIMILARITY_THRESHOLD = 0.98

def generate_telemetry():
    """Simulate an edge inference result."""
    # Generate a random 128-dim embedding
    embedding = [random.uniform(-1, 1) for _ in range(128)]
    
    classes = ["cat", "dog", "bird", "car", "person"]
    prediction = random.choice(classes)
    confidence = random.uniform(0.1, 0.99)
    
    message = {
        "device_id": "mock-edge-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_version": "v1.0.0-mock",
        "inference": {
            "prediction": prediction,
            "confidence": confidence,
            "latency_ms": random.uniform(5, 50)
        },
        "data": {
            "embedding": embedding
        }
    }
    
    # Simulate OOD image upload if confidence is very low
    if confidence < 0.3:
        message["data"]["image_b64"] = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        
    return message

def calculate_similarity(emb1, emb2):
    """Simple cosine similarity."""
    if emb1 is None or emb2 is None: return 0.0
    a = np.array(emb1)
    b = np.array(emb2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def run_mock():
    global LAST_EMBEDDING
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        console.print(f"[green]✓ Mock Edge connected to {MQTT_BROKER}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to connect: {e}[/red]")
        return

    while True:
        data = generate_telemetry()
        current_emb = data["data"]["embedding"]
        
        # Adaptive Sampling Check
        similarity = calculate_similarity(current_emb, LAST_EMBEDDING)
        
        if similarity > SIMILARITY_THRESHOLD:
            console.print(f"[yellow]Skipping redundant telemetry (similarity={similarity:.4f})[/yellow]")
        else:
            client.publish(MQTT_TOPIC, json.dumps(data))
            console.print(f"[blue]Sent telemetry for {data['inference']['prediction']} (conf={data['inference']['confidence']:.2f})[/blue]")
            LAST_EMBEDDING = current_emb
            
        time.sleep(random.uniform(1, 3))

if __name__ == "__main__":
    run_mock()
