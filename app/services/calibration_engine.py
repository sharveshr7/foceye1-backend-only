import math
from typing import Any, Dict, List, Tuple
import numpy as np


class CalibrationEngine:
    """
    9-Point gaze-to-screen coordinate polynomial mapping solver.
    Uses second-order polynomial surface fitting via least squares.
    """

    @staticmethod
    def solve_calibration(
        target_pts: List[Tuple[float, float]],
        recorded_pts: List[Tuple[float, float]]
    ) -> Dict[str, Any]:
        """
        Fits polynomial transformation:
        x_screen = a0 + a1*x + a2*y + a3*x^2 + a4*y^2 + a5*x*y
        y_screen = b0 + b1*x + b2*y + b3*x^2 + b4*y^2 + b5*x*y
        """
        from typing import Any
        if len(target_pts) < 6:
            # Need at least 6 points for 2nd order polynomial, default fallback
            return {
                "success": False,
                "rmse_pixels": 0.0,
                "accuracy_percentage": 90.0,
                "coefficients": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "message": "Insufficient calibration points. Need at least 6 points."
            }

        T = np.array(target_pts) # Target (True screen coordinates)
        R = np.array(recorded_pts) # Recorded raw gaze

        rx = R[:, 0]
        ry = R[:, 1]
        tx = T[:, 0]
        ty = T[:, 1]

        # Design matrix for 2nd order polynomial: [1, x, y, x^2, y^2, x*y]
        A = np.column_stack([
            np.ones(len(rx)),
            rx,
            ry,
            rx**2,
            ry**2,
            rx * ry
        ])

        # Least squares solutions
        coeff_x, residuals_x, _, _ = np.linalg.lstsq(A, tx, rcond=None)
        coeff_y, residuals_y, _, _ = np.linalg.lstsq(A, ty, rcond=None)

        # Estimate predicted points and RMSE
        pred_x = A @ coeff_x
        pred_y = A @ coeff_y

        error_sq = (pred_x - tx)**2 + (pred_y - ty)**2
        rmse = float(np.sqrt(np.mean(error_sq)))

        # Accuracy rating: 100% minus pixel error penalty
        accuracy = max(50.0, min(99.5, 100.0 - (rmse / 15.0)))

        all_coeffs = list(coeff_x) + list(coeff_y)

        return {
            "success": True,
            "rmse_pixels": round(rmse, 2),
            "accuracy_percentage": round(accuracy, 1),
            "coefficients": [round(float(c), 6) for c in all_coeffs],
            "message": f"9-Point Calibration Matrix Computed. Accuracy: {round(accuracy, 1)}% (RMSE: {round(rmse, 2)}px)"
        }
