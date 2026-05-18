from __future__ import annotations
import base64
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

class InferenceResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    prediction: str
    confidence: float
    # Proto3 floats default to 0.0; we align here to avoid nullability issues
    latency_ms: float = 0.0

class TelemetryData(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    embedding: List[float]
    # Standardize on bytes for raw image data to match Protobuf
    image_raw: Optional[bytes] = None

    @model_validator(mode='before')
    @classmethod
    def handle_b64_image(cls, data: any) -> any:
        if isinstance(data, dict) and "image_b64" in data and data["image_b64"]:
            try:
                # Convert b64 string to bytes for image_raw
                data["image_raw"] = base64.b64decode(data["image_b64"])
            except Exception:
                pass # Fallback to None if invalid b64
        return data

    @property
    def image_b64(self) -> Optional[str]:
        """Helper to get base64 string for JSON/Web consumption."""
        if self.image_raw:
            return base64.b64encode(self.image_raw).decode('utf-8')
        return None

class SystemStats(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    cpu_usage: float = 0.0
    mem_usage_mb: float = 0.0

class TelemetryMessage(BaseModel):
    """The core contract between Edge and Cloud."""
    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "device_id": "edge-node-001",
                "timestamp": "2026-05-16T17:45:00Z",
                "model_version": "v1.0.0-int8",
                "inference": {
                    "prediction": "cat",
                    "confidence": 0.98,
                    "latency_ms": 12.5
                },
                "data": {
                    "embedding": [0.1, 0.2, 0.3],
                    "image_raw": "..." 
                }
            }
        }
    )

    device_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_version: str
    inference: InferenceResult
    data: TelemetryData
    # Aligning with Proto3: a message field is always present in the schema
    system_stats: SystemStats = Field(default_factory=SystemStats)
