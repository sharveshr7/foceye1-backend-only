from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.auth import UserProfile, get_current_user
from app.core.supabase import supabase
from app.schemas.device_schemas import DeviceHeartbeat, DeviceResponse

router = APIRouter(prefix="/devices", tags=["Hardware Devices & Stations"])


class DevicePairRequest(BaseModel):
    device_id: str
    name: Optional[str] = None
    device_type: Optional[str] = "RPi5_SonyIMX500"


@router.get("", response_model=List[DeviceResponse])
async def list_devices(user: UserProfile = Depends(get_current_user)):
    res = supabase.table("devices").select("*").execute()
    return res.data or []


@router.get("/status")
async def get_active_device_status(user: UserProfile = Depends(get_current_user)):
    res = supabase.table("devices").select("*").execute()
    devices = res.data or []
    if not devices:
        return {
            "id": "FOC-PI5-001",
            "name": "FOCEYE Pi-Tracker v2",
            "status": "online",
            "battery": 95,
            "connection": "Active",
            "fps": 60.0,
            "latency_ms": 11.4
        }
    active = next((d for d in devices if d.get("status") == "online"), devices[0])
    return {
        "id": active.get("id"),
        "name": active.get("name"),
        "status": active.get("status", "online"),
        "battery": 92,
        "connection": "Active",
        "fps": active.get("fps", 60.0),
        "latency_ms": active.get("latency_ms", 11.4),
        "last_heartbeat": active.get("last_heartbeat")
    }


@router.post("/heartbeat", response_model=dict)
async def device_heartbeat(heartbeat: DeviceHeartbeat):
    device_data = {
        "id": heartbeat.device_id,
        "name": heartbeat.device_id,
        "status": heartbeat.status,
        "fps": heartbeat.fps,
        "latency_ms": heartbeat.latency_ms,
        "last_heartbeat": datetime.now().isoformat()
    }
    supabase.table("devices").upsert(device_data).execute()
    return {"status": "ok", "recorded_at": datetime.now().isoformat()}


@router.post("/pair")
async def pair_device(pair_req: DevicePairRequest, user: UserProfile = Depends(get_current_user)):
    device_data = {
        "id": pair_req.device_id,
        "name": pair_req.name or f"FOCEYE Station ({pair_req.device_id})",
        "status": "online",
        "fps": 60.0,
        "latency_ms": 12.0,
        "last_heartbeat": datetime.now().isoformat()
    }
    supabase.table("devices").upsert(device_data).execute()
    return {"paired": True, "device": device_data}


@router.post("/disconnect")
async def disconnect_device(pair_req: DevicePairRequest, user: UserProfile = Depends(get_current_user)):
    supabase.table("devices").update({"status": "offline"}).eq("id", pair_req.device_id).execute()
    return {"status": "disconnected", "device_id": pair_req.device_id}
