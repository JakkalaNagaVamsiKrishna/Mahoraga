import pytest
import numpy as np
from api.models import TelemetryMessage
from spoke.src.clustering.processor import perform_clustering
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

def create_mock_telemetry(embedding, confidence=0.9):
    return TelemetryMessage(
        device_id="test-node",
        timestamp=datetime.now(timezone.utc),
        model_version="v1.0",
        inference={"prediction": "test", "confidence": confidence},
        data={"embedding": embedding}
    )

@patch('spoke.src.clustering.processor.forward_to_hub')
@patch('spoke.src.clustering.processor.EPS', 0.5)
@patch('spoke.src.clustering.processor.MIN_SAMPLES', 5)
def test_clustering_logic(mock_forward):
    """Test that DBSCAN clustering correctly identifies clusters and noise."""
    # Using Euclidean space for simpler coordinate-based testing
    # Core cluster: 5 points very close to each other
    cluster_points = [[0.1, 0.1], [0.11, 0.1], [0.1, 0.11], [0.09, 0.1], [0.1, 0.09]]
    # Noise: points far away from each other and the cluster
    noise_points = [[10.0, 10.0], [-10.0, -10.0], [5.0, 5.0], [20.0, 1.0], [0.0, 30.0]]
    
    telemetry_list = [create_mock_telemetry(p) for p in (cluster_points + noise_points)]
    
    # Temporarily switch to euclidean for this test to match coordinate points
    with patch('spoke.src.clustering.processor.DBSCAN') as mock_dbscan:
        from sklearn.cluster import DBSCAN as RealDBSCAN
        mock_dbscan.side_effect = lambda **kwargs: RealDBSCAN(eps=0.5, min_samples=5, metric='euclidean')
        perform_clustering(telemetry_list)
    
    # Total calls: 1 (representative) + 5 (noise) = 6
    assert mock_forward.call_count == 6
    
    # Check that we have at least one call with is_anomaly=False (representative)
    # and some calls with is_anomaly=True (noise)
    # Using call_args_list[index].args[1] is the most direct way
    has_representative = False
    anomaly_count = 0
    for call in mock_forward.call_args_list:
        if len(call.args) > 1:
            if call.args[1] == True:
                anomaly_count += 1
            else:
                has_representative = True
        elif 'is_anomaly' in call.kwargs:
            if call.kwargs['is_anomaly'] == True:
                anomaly_count += 1
            else:
                has_representative = True
    
    assert has_representative == True
    assert anomaly_count == 5

def test_latent_extraction_numpy():
    """Verify embedding conversion to numpy."""
    t = create_mock_telemetry([1.0, 2.0])
    emb = np.array([t.data.embedding])
    assert emb.shape == (1, 2)
    assert emb[0, 0] == 1.0
