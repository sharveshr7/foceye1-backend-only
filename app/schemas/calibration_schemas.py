from typing import List, Optional
from pydantic import BaseModel


class CalibrationPoint(BaseModel):
    target_x: float
    target_y: float
    recorded_x: float
    recorded_y: float


class CalibrationRequest(BaseModel):
    points: List[CalibrationPoint]
    screen_width: int = 1920
    screen_height: int = 1080


class CalibrationResponse(BaseModel):
    success: bool
    rmse_pixels: float
    accuracy_percentage: float
    polynomial_coefficients: List[float]
    message: str
