import os
import json
import logging
from typing import Type, TypeVar, Any, List
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger("urfeast.gemma")

T = TypeVar("T", bound=BaseModel)

class GemmaClient:
    REQUEST_TIMEOUT_S = 15.0

    def __init__(self):
        self.model_id = settings.GEMMA_MODEL
        self.genai_client = None
        self.available_models: List[str] = []

        api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                from google import genai
                self.genai_client = genai.Client(api_key=api_key)
                self._check_models()
            except Exception as e:
                print(f"[GemmaClient] Warning initializing google-genai SDK: {e}")
        else:
            print("[GemmaClient] GEMINI_API_KEY is not set. Live Gemma calls will fail until configured.")

    def _check_models(self):
        """At startup, list models from the API and print every model ID."""
        if not self.genai_client:
            return
        try:
            print(f"[GemmaClient] Target model from GEMMA_MODEL: {self.model_id}")
            models = list(self.genai_client.models.list())
            self.available_models = [m.name for m in models]
            print(f"[GemmaClient] {len(self.available_models)} models available:")
            for name in self.available_models:
                print(f"   - {name}")
            if self.model_id not in self.available_models and f"models/{self.model_id}" not in self.available_models:
                fallback = "gemma-4-26b-a4b-it"
                candidates = [n for n in self.available_models if fallback in n]
                if candidates:
                    self.model_id = candidates[0].split("/")[-1] if "/" in candidates[0] else candidates[0]
                    print(f"[GemmaClient] GEMMA_MODEL not in list; using fallback: {self.model_id}")
        except Exception as e:
            print(f"[GemmaClient] Could not list models from Gemini API: {e}")

    def generate_json(
        self,
        system_prompt: str,
        user_parts: List[Any],
        schema: Type[T],
        retry_count: int = 1
    ) -> T:
        """Sends text and optional image bytes to Gemma, requests JSON, and validates with Pydantic."""
        
        if not self.genai_client:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        try:
            return self._call_gemini(system_prompt, user_parts, schema, retry_count)
        except Exception as e:
            logger.warning(f"[GemmaClient] Gemini API call failed ({e}).")
            raise RuntimeError(f"Gemma API call failed: {e}") from e

    def _call_gemini(self, system_prompt: str, user_parts: List[Any], schema: Type[T], retry_count: int) -> T:
        from google.genai import types

        # Prepare contents list
        contents = []
        for part in user_parts:
            if isinstance(part, str):
                contents.append(part)
            elif isinstance(part, bytes):
                contents.append(types.Part.from_bytes(data=part, mime_type="image/jpeg"))
            elif isinstance(part, dict) and "mime_type" in part and "data" in part:
                contents.append(types.Part.from_bytes(data=part["data"], mime_type=part["mime_type"]))

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.2
        )

        response = self.genai_client.models.generate_content(
            model=self.model_id,
            contents=contents,
            config=config,
            http_options={"timeout": int(self.REQUEST_TIMEOUT_S * 1000)},
        )

        raw_text = response.text or "{}"
        
        # Strip markdown fences if present
        cleaned_json = self._clean_json(raw_text)

        try:
            parsed = json.loads(cleaned_json)
            return schema.model_validate(parsed)
        except Exception as err:
            if retry_count > 0:
                print(f"[GemmaClient] JSON validation failed ({err}). Retrying once with repair prompt...")
                repair_prompt = f"Previous response failed schema validation: {err}. Please output ONLY raw valid JSON matching the schema."
                new_parts = user_parts + [repair_prompt]
                return self._call_gemini(system_prompt, new_parts, schema, retry_count - 1)
            raise err

    def _clean_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

gemma_client = GemmaClient()
