import pytest
from datetime import datetime
from api.models import TelemetryMessage, InferenceResult, TelemetryData

def test_telemetry_message_valid():
    """Test that a valid telemetry message is correctly parsed."""
    data = {
        "device_id": "test-device",
        "timestamp": datetime.utcnow().isoformat(),
        "model_version": "v1.0",
        "inference": {
            "prediction": "cat",
            "confidence": 0.95
        },
        "data": {
            "embedding": [0.1, 0.2, 0.3]
        }
    }
    msg = TelemetryMessage(**data)
    assert msg.device_id == "test-device"
    assert msg.inference.prediction == "cat"
    assert len(msg.data.embedding) == 3

def test_telemetry_message_invalid():
    """Test that missing required fields raise validation errors."""
    data = {
        "device_id": "test-device",
        # Missing timestamp, model_version, etc.
    }
    with pytest.raises(ValueError):
        TelemetryMessage(**data)

def test_inference_result_bounds():
    """Ensure confidence scores are within expected ranges logic if implemented (optional)."""
    # Pydantic doesn't have strict bounds unless we add them, but we check if it parses.
    res = InferenceResult(prediction="dog", confidence=0.5)
    assert res.confidence == 0.5
