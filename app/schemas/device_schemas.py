from typing import Optional
from pydantic import BaseModel


class DeviceHeartbeat(BaseModel):
    device_id: str
    fps: float
    latency_ms: float
    cpu_usage: Optional[float] = None
    temperature_c: Optional[float] = None
    status: str = "online"


class DeviceResponse(BaseModel):
    id: str
    name: str
    status: str
    fps: float
    latency_ms: float
    last_heartbeat: str
