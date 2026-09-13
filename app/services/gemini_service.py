import asyncio
import json
import logging
import os
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from google import genai
from google.genai import errors, types

from app.core.config import settings

logger = logging.getLogger("foceye.gemini")


class GeminiService:
    """
    Production-grade Google Gemini API service using the official google-genai SDK.
    - True non-blocking asynchronous execution via client.aio
    - Multi-model fallback (gemini-3.5-flash-lite -> gemini-3.6-flash -> gemini-flash-lite-latest)
    - Automatic Function Calling (AFC) warning suppression
    - JSON extraction with markdown stripping
    - Real-time token streaming support
    - Isolated error handling and zero key leaks
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
                logger.info("Gemini API client initialized successfully.")
            except Exception as e:
                self._client = None
                self._configured = False
                logger.error(f"Failed to initialize Gemini client: {e}")
        else:
            self._client = None
            self._configured = False
            logger.info("Gemini API key not configured.")

    @property
    def is_configured(self) -> bool:
        if not self._configured or not self._client:
            self._init_client()
        return self._configured

    @property
    def default_model(self) -> str:
        model = (os.getenv("GEMINI_MODEL") or settings.GEMINI_MODEL or "gemini-3.6-flash").strip()
        return model or "gemini-3.6-flash"

    def get_candidate_models(self) -> List[str]:
        preferred = self.default_model
        fallbacks = ["gemini-3.6-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash"]
        models = [preferred] + [m for m in fallbacks if m != preferred]
        return models

    async def check_health(self) -> Dict[str, Any]:
        """
        Dedicated health check verifying the live Gemini connection asynchronously
        without exposing keys, credentials, or secrets.
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
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    temperature=0.0,
                )
                response = await self._client.aio.models.generate_content(
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
                        "error_type": None,
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
                logger.warning(f"Gemini probe for {model_name} failed: {ce}")
            except errors.ServerError as se:
                last_error = str(se)
                last_error_type = "SERVER_UNAVAILABLE"
                logger.warning(f"Gemini probe server error for {model_name}: {se}")
            except Exception as e:
                last_error = str(e)
                last_error_type = "COMMUNICATION_ERROR"
                logger.warning(f"Gemini probe failure on {model_name}: {e}")

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
        temperature: float = 0.2,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
        """
        Executes an asynchronous non-blocking prompt requesting valid JSON output from Gemini.
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
                    "temperature": temperature,
                }
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction

                config = types.GenerateContentConfig(**config_kwargs)

                response = await self._client.aio.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config,
                )

                if not response or not response.text:
                    last_error_msg = f"Empty response from {target_model}"
                    continue

                raw_text = response.text.strip()
                # Clean markdown fences if present
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()

                # Regex fallback for JSON object/array
                match = re.search(r"(\{|\[).*(?:\}|\])", raw_text, re.DOTALL)
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
                if ce.code == 429:
                    await asyncio.sleep(0.5)
            except errors.ServerError as se:
                last_error_msg = f"Server error on {target_model}: {se}"
                logger.warning(last_error_msg)
            except Exception as ex:
                last_error_msg = f"Unexpected Gemini error on {target_model}: {ex}"
                logger.warning(last_error_msg)

        return None, None, last_error_msg

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Executes an asynchronous non-blocking prompt returning raw text from Gemini.
        Returns:
            (response_text, used_model_name, error_message)
        """
        if not self.is_configured or not self._client:
            return None, None, "Gemini API key is not configured."

        models_to_try = [model] if model else self.get_candidate_models()
        last_error_msg = None

        for target_model in models_to_try:
            try:
                config_kwargs = {
                    "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
                    "temperature": temperature,
                }
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction

                config = types.GenerateContentConfig(**config_kwargs)

                response = await self._client.aio.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config,
                )

                if response and response.text:
                    return response.text.strip(), target_model, None

                last_error_msg = f"Empty response from {target_model}"

            except errors.ClientError as ce:
                last_error_msg = f"Client error ({ce.code}) on {target_model}: {ce}"
                if ce.code in (401, 403):
                    break
            except Exception as ex:
                last_error_msg = f"Error on {target_model}: {ex}"

        return None, None, last_error_msg

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> AsyncGenerator[str, None]:
        """
        Asynchronously streams generated tokens from Gemini for real-time SSE/WebSocket responses.
        """
        if not self.is_configured or not self._client:
            yield "Gemini API key is not configured."
            return

        target_model = model or self.default_model
        try:
            config_kwargs = {
                "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
                "temperature": temperature,
            }
            if system_instruction:
                config_kwargs["system_instruction"] = system_instruction

            config = types.GenerateContentConfig(**config_kwargs)

            async for chunk in await self._client.aio.models.generate_content_stream(
                model=target_model,
                contents=prompt,
                config=config,
            ):
                if chunk and chunk.text:
                    yield chunk.text
        except Exception as ex:
            logger.error(f"Streaming failed on {target_model}: {ex}")
            yield f"\n[Streaming error: {ex}]"


gemini_service = GeminiService()

