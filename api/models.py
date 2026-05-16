from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class InferenceResult(BaseModel):
    prediction: str
    confidence: float
    latency_ms: Optional[float] = None

class TelemetryData(BaseModel):
    embedding: List[float]
    image_b64: Optional[str] = None

class SystemStats(BaseModel):
    cpu_usage: Optional[float] = None
    mem_usage_mb: Optional[float] = None

class TelemetryMessage(BaseModel):
    """The core contract between Edge and Cloud."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "edge-node-001",
                "timestamp": "2026-05-16T17:45:00Z",
                "model_version": "v1.0.0-int8",
                "inference": {
                    "prediction": "cat",
                    "confidence": 0.98
                },
                "data": {
                    "embedding": [0.1, 0.2, 0.3]
                }
            }
        }
    )

    device_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_version: str
    inference: InferenceResult
    data: TelemetryData
    system_stats: Optional[SystemStats] = None
