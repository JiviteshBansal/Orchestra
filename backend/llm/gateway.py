import time
import logging
from typing import Optional
from dataclasses import dataclass, field

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModelProfile:
    primary_model: str = ""
    fallback_chain: list[str] = field(default_factory=list)
    max_tokens: int = 2048
    temperature: float = 0.7
    provider: str = "gemini"
    constraints: dict = field(default_factory=lambda: {
        "max_latency_ms": 30000,
        "max_cost_per_call": 0.0,
        "privacy_level": "cloud"
    })


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: float = 0
    success: bool = True
    error: Optional[str] = None


class TelemetryTracker:
    def __init__(self):
        self.calls: list[dict] = []

    def record(self, model: str, provider: str, tokens: int, latency_ms: float, success: bool):
        self.calls.append({
            "model": model,
            "provider": provider,
            "tokens": tokens,
            "latency_ms": latency_ms,
            "success": success,
            "timestamp": time.time()
        })

    def get_stats(self) -> dict:
        if not self.calls:
            return {"total_calls": 0}
        total = len(self.calls)
        successful = sum(1 for c in self.calls if c["success"])
        avg_latency = sum(c["latency_ms"] for c in self.calls) / total
        total_tokens = sum(c["tokens"] for c in self.calls)
        return {
            "total_calls": total,
            "successful_calls": successful,
            "failed_calls": total - successful,
            "avg_latency_ms": round(avg_latency, 2),
            "total_tokens": total_tokens,
        }


class ModelRegistry:
    def __init__(self):
        self.models: dict[str, dict] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register("gemini-1.5-flash", {
            "provider": "gemini",
            "model_id": "gemini-1.5-flash",
            "latency_tier": "fast",
            "cost_per_1k_tokens": 0.0,
            "privacy": "cloud",
            "capabilities": ["code", "reasoning", "planning"],
        })
        self.register("gemini-1.5-pro", {
            "provider": "gemini",
            "model_id": "gemini-1.5-pro",
            "latency_tier": "medium",
            "cost_per_1k_tokens": 0.0,
            "privacy": "cloud",
            "capabilities": ["code", "reasoning", "planning"],
        })

    def register(self, name: str, config: dict):
        self.models[name] = config

    def get(self, name: str) -> Optional[dict]:
        return self.models.get(name)

    def list_models(self) -> list[str]:
        return list(self.models.keys())


class LLMGateway:
    def __init__(self):
        self.registry = ModelRegistry()
        self.telemetry = TelemetryTracker()
        self._gemini_client = None

    def _get_gemini_client(self):
        """Lazily initialise the google-generativeai client."""
        if self._gemini_client is None:
            try:
                import google.generativeai as genai
                api_key = settings.GEMINI_API_KEY or settings.OPENAI_API_KEY
                if not api_key:
                    raise ValueError("No API key set. Add GEMINI_API_KEY to your .env file.")
                genai.configure(api_key=api_key)
                self._gemini_client = genai
                logger.info("Gemini client initialised successfully.")
            except ImportError:
                raise RuntimeError(
                    "google-generativeai is not installed. "
                    "Run: pip install google-generativeai"
                )
        return self._gemini_client

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model_profile: Optional[ModelProfile] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        profile = model_profile or ModelProfile(
            primary_model=settings.LM_STUDIO_MODEL or "gemini-1.5-flash"
        )
        model_name = profile.primary_model or "gemini-1.5-flash"
        chain = [model_name] + profile.fallback_chain

        for attempt_model in chain:
            response = await self._call_model(
                model=attempt_model,
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens or profile.max_tokens,
                temperature=temperature or profile.temperature,
            )
            if response.success:
                return response
            logger.warning(f"Model {attempt_model} failed: {response.error}, trying next in chain")

        return LLMResponse(
            content="",
            model=model_name,
            provider="gemini",
            success=False,
            error="All models in fallback chain failed",
        )

    async def _call_model(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        start = time.time()
        try:
            import asyncio
            genai = self._get_gemini_client()

            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }

            # Run the synchronous Gemini call in a thread so we don't block the event loop
            def _sync_call():
                client_model = genai.GenerativeModel(
                    model_name=model,
                    system_instruction=system_prompt if system_prompt else None,
                    generation_config=generation_config,
                )
                return client_model.generate_content(prompt)

            result = await asyncio.get_event_loop().run_in_executor(None, _sync_call)

            content = result.text
            latency_ms = (time.time() - start) * 1000

            # Estimate token usage (Gemini SDK may not always expose this)
            tokens = 0
            if hasattr(result, "usage_metadata") and result.usage_metadata:
                tokens = getattr(result.usage_metadata, "total_token_count", 0) or 0

            self.telemetry.record(model, "gemini", tokens, latency_ms, True)

            return LLMResponse(
                content=content,
                model=model,
                provider="gemini",
                tokens_used=tokens,
                latency_ms=latency_ms,
                success=True,
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            self.telemetry.record(model, "gemini", 0, latency_ms, False)
            logger.error(f"Gemini call to {model} failed: {e}")
            return LLMResponse(
                content="",
                model=model,
                provider="gemini",
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )

    def get_telemetry(self) -> dict:
        return self.telemetry.get_stats()


llm_gateway = LLMGateway()
