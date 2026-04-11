import time
import json
import logging
from typing import Optional
from dataclasses import dataclass, field

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModelProfile:
    primary_model: str = ""
    fallback_chain: list[str] = field(default_factory=list)
    max_tokens: int = 2048
    temperature: float = 0.7
    provider: str = "lm_studio"
    constraints: dict = field(default_factory=lambda: {
        "max_latency_ms": 30000,
        "max_cost_per_call": 0.0,
        "privacy_level": "local"
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
        self.register("codellama-7b-instruct", {
            "provider": "lm_studio",
            "base_url": settings.LM_STUDIO_BASE_URL,
            "model_id": settings.LM_STUDIO_MODEL,
            "latency_tier": "medium",
            "cost_per_1k_tokens": 0.0,
            "privacy": "local",
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
        self._client = httpx.Client(timeout=settings.LLM_TIMEOUT)
        self._async_client = httpx.AsyncClient(timeout=settings.LLM_TIMEOUT)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model_profile: Optional[ModelProfile] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        profile = model_profile or ModelProfile(
            primary_model=settings.LM_STUDIO_MODEL
        )
        model_name = profile.primary_model or settings.LM_STUDIO_MODEL
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
            provider="none",
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
        model_config = self.registry.get(model)
        provider = model_config["provider"] if model_config else "lm_studio"
        base_url = model_config["base_url"] if model_config else settings.LM_STUDIO_BASE_URL

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        start = time.time()
        try:
            resp = await self._async_client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            latency_ms = (time.time() - start) * 1000

            self.telemetry.record(model, provider, tokens, latency_ms, True)

            return LLMResponse(
                content=content,
                model=model,
                provider=provider,
                tokens_used=tokens,
                latency_ms=latency_ms,
                success=True,
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            self.telemetry.record(model, provider, 0, latency_ms, False)
            logger.error(f"LLM call to {model} failed: {e}")
            return LLMResponse(
                content="",
                model=model,
                provider=provider,
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )

    def get_telemetry(self) -> dict:
        return self.telemetry.get_stats()


llm_gateway = LLMGateway()
