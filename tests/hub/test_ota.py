import pytest
from fastapi.testclient import TestClient
from hub.services.ota_orchestrator import app, MODEL_REGISTRY_DIR
from unittest.mock import patch, MagicMock
import json

client = TestClient(app)

def test_ota_health():
    """Verify OTA service is alive."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "active"

def test_get_model_not_found():
    """Verify 404 for non-existent model."""
    response = client.get("/models/v99.9.9")
    assert response.status_code == 404

def test_get_model_success():
    """Verify model file download."""
    # Create a dummy model file
    version = "test-v1"
    model_file = MODEL_REGISTRY_DIR / f"student_{version}.onnx"
    model_file.touch()
    
    response = client.get(f"/models/{version}")
    assert response.status_code == 200
    # Clean up
    model_file.unlink()

@patch('hub.services.ota_orchestrator.mqtt_client')
def test_rollout_trigger(mock_mqtt):
    """Verify rollout command is published via MQTT."""
    version = "test-v2"
    model_file = MODEL_REGISTRY_DIR / f"student_{version}.onnx"
    model_file.touch()
    
    response = client.post(f"/rollout/{version}")
    assert response.status_code == 200
    
    # Check if MQTT publish was called
    assert mock_mqtt.publish.called
    topic, payload = mock_mqtt.publish.call_args[0]
    assert topic == "mahoraga/control/update"
    
    data = json.loads(payload)
    assert data["version"] == version
    assert "url" in data
    assert data["command"] == "HOT_SWAP"
    
    # Clean up
    model_file.unlink()
