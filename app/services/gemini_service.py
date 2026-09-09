import json
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple

from google import genai
from google.genai import errors, types

from app.core.config import settings

logger = logging.getLogger("foceye.gemini")


class GeminiService:
    """
    Production-grade Google Gemini API service using the official google-genai SDK.
    Never exposes API keys, isolates errors, and provides dedicated health verification.
    """

    def __init__(self):
        self._client: Optional[genai.Client] = None
        self._configured: bool = False
        self._init_client()

    def _get_api_key(self) -> str:
        key = (
            os.getenv("GEMINI_API_KEY")
            or settings.GEMINI_API_KEY
            or os.getenv("GOOGLE_API_KEY")
            or ""
        ).strip()
        # Discard dummy or placeholder keys
        if not key or "mock" in key.lower() or key.startswith("your-"):
            return ""
        return key

    def _init_client(self):
        api_key = self._get_api_key()
        if api_key:
            try:
                self._client = genai.Client(api_key=api_key)
                self._configured = True
                logger.info("Gemini API key configured: True")
            except Exception as e:
                self._client = None
                self._configured = False
                logger.error(f"Failed to initialize Gemini client: {e}")
        else:
            self._client = None
            self._configured = False
            logger.info("Gemini API key configured: False")

    @property
    def is_configured(self) -> bool:
        # Re-check key in case environment was loaded after import
        if not self._configured or not self._client:
            self._init_client()
        return self._configured

    @property
    def default_model(self) -> str:
        model = (os.getenv("GEMINI_MODEL") or settings.GEMINI_MODEL or "gemini-3.5-flash-lite").strip()
        return model or "gemini-3.5-flash-lite"

    def get_candidate_models(self) -> list[str]:
        preferred = self.default_model
        fallbacks = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash"]
        models = [preferred] + [m for m in fallbacks if m != preferred]
        return models

    async def check_health(self) -> Dict[str, Any]:
        """
        Dedicated health check verifying the live Gemini connection independently
        from clinical application flow. Never exposes keys or credentials.
        """
        if not self.is_configured or not self._client:
            return {
                "success": False,
                "gemini_configured": False,
                "gemini_working": False,
                "message": "Gemini API key is not configured in environment (GEMINI_API_KEY).",
                "model": self.default_model,
                "error_type": "MISSING_API_KEY",
            }

        candidate_models = self.get_candidate_models()
        last_error = ""
        last_error_type = "API_ERROR"

        for model_name in candidate_models:
            try:
                config = types.GenerateContentConfig(
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                )
                response = self._client.models.generate_content(
                    model=model_name,
                    contents="Reply with the single word: OK",
                    config=config,
                )
                if response and response.text:
                    return {
                        "success": True,
                        "gemini_configured": True,
                        "gemini_working": True,
                        "message": "Gemini API is operational and responding.",
                        "model": model_name,
                    }
            except errors.ClientError as ce:
                last_error = str(ce)
                if ce.code == 400:
                    last_error_type = "INVALID_REQUEST"
                elif ce.code in (401, 403):
                    last_error_type = "AUTHENTICATION_FAILED"
                    break
                elif ce.code == 404:
                    last_error_type = "MODEL_NOT_FOUND"
                elif ce.code == 429:
                    last_error_type = "QUOTA_EXCEEDED"
                logger.warning(f"Gemini probe for model {model_name} failed: {ce}")
            except errors.ServerError as se:
                last_error = str(se)
                last_error_type = "SERVER_UNAVAILABLE"
                logger.warning(f"Gemini probe server error for model {model_name}: {se}")
            except Exception as e:
                last_error = str(e)
                last_error_type = "COMMUNICATION_ERROR"
                logger.warning(f"Gemini probe general failure on {model_name}: {e}")

        return {
            "success": False,
            "gemini_configured": True,
            "gemini_working": False,
            "message": f"Gemini API request failed ({last_error_type}): {last_error[:120]}",
            "model": self.default_model,
            "error_type": last_error_type,
        }

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        """
        Executes a prompt requesting JSON output from Gemini.
        Returns:
            (parsed_dict, used_model_name, error_message)
        """
        if not self.is_configured or not self._client:
            return None, None, "Gemini API key is not configured."

        models_to_try = [model] if model else self.get_candidate_models()
        last_error_msg = None

        for target_model in models_to_try:
            try:
                config_kwargs = {
                    "response_mime_type": "application/json",
                    "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
                }
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction

                config = types.GenerateContentConfig(**config_kwargs)

                response = self._client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config,
                )

                if not response or not response.text:
                    last_error_msg = f"Empty response received from Gemini model {target_model}"
                    continue

                raw_text = response.text.strip()
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if match:
                    raw_text = match.group(0)

                parsed_data = json.loads(raw_text)
                return parsed_data, target_model, None

            except json.JSONDecodeError as jde:
                last_error_msg = f"Malformed JSON from {target_model}: {jde}"
                logger.warning(last_error_msg)
            except errors.ClientError as ce:
                last_error_msg = f"Client error ({ce.code}) on {target_model}: {ce}"
                logger.warning(last_error_msg)
                if ce.code in (401, 403):
                    break
            except errors.ServerError as se:
                last_error_msg = f"Server error on {target_model}: {se}"
                logger.warning(last_error_msg)
            except Exception as ex:
                last_error_msg = f"Unexpected Gemini error on {target_model}: {ex}"
                logger.warning(last_error_msg)

        return None, None, last_error_msg


gemini_service = GeminiService()
