import math
from typing import Any, Dict, List, Tuple
import numpy as np


class EyeProcessor:
    """
    Scientific ocular signal processing engine using NumPy, SciPy, and OpenCV principles.
    Computes:
    - Bivariate Contour Ellipse Area (BCEA 68% and 95% confidence intervals).
    - Fixation identification (Dispersion/Velocity threshold).
    - Saccadic peak velocity and latency.
    - Pupillometry asymmetry dynamics.
    """

    @staticmethod
    def calculate_bcea(gaze_x: List[float], gaze_y: List[float], p: float = 0.68) -> Dict[str, float]:
        """
        Calculates Bivariate Contour Ellipse Area (BCEA).
        Formula: BCEA = 2 * k * pi * sigma_x * sigma_y * sqrt(1 - rho^2)
        where k = -ln(1 - p)
        For p=0.68 (1 std dev), k ≈ 1.14
        For p=0.95 (2 std dev), k ≈ 2.99
        """
        if len(gaze_x) < 5 or len(gaze_y) < 5:
            return {"bcea_deg2": 0.0, "sigma_x": 0.0, "sigma_y": 0.0, "rho": 0.0}

        x = np.array(gaze_x, dtype=np.float64)
        y = np.array(gaze_y, dtype=np.float64)

        sigma_x = float(np.std(x))
        sigma_y = float(np.std(y))

        # Correlation coefficient
        corr_matrix = np.corrcoef(x, y)
        rho = float(corr_matrix[0, 1]) if not np.isnan(corr_matrix[0, 1]) else 0.0

        # Bound rho within [-0.999, 0.999] for numerical stability
        rho = max(-0.999, min(0.999, rho))

        k = -math.log(1.0 - p)
        bcea = 2.0 * k * math.pi * sigma_x * sigma_y * math.sqrt(1.0 - rho**2)

        return {
            "bcea_deg2": round(float(bcea), 4),
            "sigma_x": round(sigma_x, 4),
            "sigma_y": round(sigma_y, 4),
            "rho": round(rho, 4),
            "k_value": round(k, 3)
        }

    @staticmethod
    def classify_fixations_ivt(
        gaze_x: List[float],
        gaze_y: List[float],
        timestamps: List[float],
        velocity_threshold_deg_per_sec: float = 30.0
    ) -> Dict[str, Any]:
        """
        I-VT (Velocity Threshold Identification) algorithm for separating fixations and saccades.
        """
        if len(gaze_x) < 2:
            return {"fixation_percentage": 100.0, "fixation_count": 0, "saccade_count": 0}

        x = np.array(gaze_x)
        y = np.array(gaze_y)
        t = np.array(timestamps)

        dt = np.diff(t)
        # Avoid division by zero
        dt[dt == 0] = 0.001

        dx = np.diff(x)
        dy = np.diff(y)
        distances = np.sqrt(dx**2 + dy**2)
        velocities = distances / dt

        is_fixation = velocities < velocity_threshold_deg_per_sec
        fixation_samples = int(np.sum(is_fixation))
        total_samples = len(velocities)

        fixation_pct = (fixation_samples / total_samples) * 100.0 if total_samples > 0 else 100.0

        return {
            "fixation_percentage": round(float(fixation_pct), 2),
            "mean_velocity": round(float(np.mean(velocities)), 2),
            "peak_velocity": round(float(np.max(velocities)), 2) if len(velocities) > 0 else 0.0,
            "sample_count": total_samples + 1
        }

    @staticmethod
    def analyze_pupillometry(
        left_pupil_mm: List[float],
        right_pupil_mm: List[float]
    ) -> Dict[str, float]:
        """
        Analyzes pupillary dynamics and anisocoria (asymmetry).
        """
        if not left_pupil_mm or not right_pupil_mm:
            return {"mean_left_mm": 3.5, "mean_right_mm": 3.5, "anisocoria_index": 0.0}

        left = np.array(left_pupil_mm)
        right = np.array(right_pupil_mm)

        mean_l = float(np.mean(left))
        mean_r = float(np.mean(right))
        anisocoria = abs(mean_l - mean_r)

        return {
            "mean_left_mm": round(mean_l, 2),
            "mean_right_mm": round(mean_r, 2),
            "anisocoria_index": round(anisocoria, 3),
            "is_within_normal_limits": anisocoria < 0.4 # Clinically significant if > 0.4mm
        }
