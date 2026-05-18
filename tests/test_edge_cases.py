import json
from unittest.mock import MagicMock, patch
from api.models import TelemetryMessage
from spoke.src.gateway.main import on_message

def test_on_message_malformed_json():
    """Verify that malformed JSON is caught and logged, not raising an exception."""
    client = MagicMock()
    msg = MagicMock()
    msg.payload = b"invalid-json{"
    msg.topic = "mahoraga/telemetry/test"
    
    with patch('spoke.src.gateway.main.logger') as mock_logger:
        on_message(client, None, msg)
        # Should log a warning
        assert mock_logger.warning.called

def test_on_message_schema_mismatch():
    """Verify that mismatching schema is caught."""
    client = MagicMock()
    msg = MagicMock()
    # Missing required 'device_id'
    msg.payload = json.dumps({"timestamp": "2026-05-16T12:00:00Z"}).encode()
    msg.topic = "mahoraga/telemetry/test"
    
    with patch('spoke.src.gateway.main.logger') as mock_logger:
        on_message(client, None, msg)
        assert mock_logger.warning.called

def test_perform_clustering_empty():
    """Verify safety with empty list."""
    from spoke.src.clustering.processor import perform_clustering
    with patch('spoke.src.clustering.processor.logger') as mock_logger:
        perform_clustering([])
        # Now returns silently
        assert not mock_logger.warning.called

def test_perform_clustering_mismatched_dims():
    """Verify safety with mismatched embedding dimensions."""
    from spoke.src.clustering.processor import perform_clustering
    from datetime import datetime, timezone
    
    # Create telemetry with inconsistent embedding sizes
    t1 = TelemetryMessage(
        device_id="n1", timestamp=datetime.now(timezone.utc), model_version="v1",
        inference={"prediction": "a", "confidence": 0.9},
        data={"embedding": [0.1, 0.2]}
    )
    t2 = TelemetryMessage(
        device_id="n2", timestamp=datetime.now(timezone.utc), model_version="v1",
        inference={"prediction": "b", "confidence": 0.9},
        data={"embedding": [0.1, 0.2, 0.3]} # D=3
    )
    
    with patch('spoke.src.clustering.processor.logger') as mock_logger:
        perform_clustering([t1, t2])
        # np.array will likely create an object array or fail if forced to float, 
        # but our dimension check should catch it.
        assert mock_logger.error.called

def test_save_image_malformed_b64():
    """Verify safety with invalid base64."""
    from hub.services.collector import save_image
    with patch('hub.services.collector.logger') as mock_logger:
        save_image("not-base64-!!!", "device-001")
        assert mock_logger.error.called
