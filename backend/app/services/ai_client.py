import asyncio
import json
import logging
import time
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AIPipelineError(Exception):
    pass


class AIModelTimeoutError(AIPipelineError):
    pass


class AIModelResponseError(AIPipelineError):
    pass


class AIPipelineExhaustedError(AIPipelineError):
    pass


class _ModelConfig(BaseModel):
    model: str
    api_key: str
    base_url: str
    max_tokens: int = 4096
    temperature: float = 0.7


MODEL_REGISTRY: dict[str, _ModelConfig] = {}

TASK_TO_MODEL: dict[str, str] = {
    "analyze_job": "glm",
    "gap_analysis": "glm",
    "generate_resume": "openai",
    "validate_ats": "glm",
    "generate_cover_letter": "glm",
    "interview_coach": "glm",
    "parse_resume": "glm",
}

FALLBACK_MAP: dict[str, str] = {
    "glm": "openai",
    "openai": "glm",
}


def _init_registry() -> None:
    if MODEL_REGISTRY:
        return
    if settings.GLM_API_KEY:
        MODEL_REGISTRY["glm"] = _ModelConfig(
            model=settings.GLM_MODEL,
            api_key=settings.GLM_API_KEY,
            base_url=settings.GLM_BASE_URL,
        )
    if settings.OPENAI_API_KEY:
        MODEL_REGISTRY["openai"] = _ModelConfig(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )


_init_registry()


def _get_model_for_task(task: str) -> tuple[_ModelConfig, str]:
    model_key = TASK_TO_MODEL.get(task, "glm")
    config = MODEL_REGISTRY.get(model_key)
    if config is None:
        available = list(MODEL_REGISTRY.keys())
        if not available:
            raise AIPipelineError("No AI models configured. Set GLM_API_KEY or OPENAI_API_KEY.")
        model_key = available[0]
        config = MODEL_REGISTRY[model_key]
    return config, model_key


def _get_fallback(model_key: str) -> tuple[_ModelConfig, str] | None:
    fallback_key = FALLBACK_MAP.get(model_key)
    if fallback_key and fallback_key in MODEL_REGISTRY:
        return MODEL_REGISTRY[fallback_key], fallback_key
    return None


async def _call_openai_api(
    config: _ModelConfig,
    messages: list[dict[str, str]],
    response_format: dict[str, Any] | None = None,
) -> str:
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {
        "model": config.model,
        "messages": messages,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
    }
    if response_format is not None:
        payload["response_format"] = response_format

    url = f"{config.base_url.rstrip('/')}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise AIModelTimeoutError(f"Model {config.model} timed out: {exc}") from exc
    except httpx.HTTPError as exc:
        raise AIPipelineError(f"HTTP error calling {config.model}: {exc}") from exc

    if response.status_code == 401:
        raise AIPipelineError(f"Authentication failed for {config.model}: {response.text}")
    if response.status_code == 400:
        raise AIPipelineError(f"Bad request to {config.model}: {response.text}")

    if response.status_code >= 500:
        raise AIPipelineError(
            f"Server error from {config.model} (status={response.status_code}): {response.text}"
        )

    if response.status_code != 200:
        raise AIPipelineError(
            f"Unexpected status {response.status_code} from {config.model}: {response.text}"
        )

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise AIModelResponseError(f"Malformed response from {config.model}: {data}") from exc


def _extract_json_from_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        json_lines: list[str] = []
        inside = False
        for line in lines:
            if line.strip().startswith("```"):
                if inside:
                    break
                inside = True
                continue
            if inside:
                json_lines.append(line)
        text = "\n".join(json_lines).strip()

    first_brace = text.find("{")
    first_bracket = text.find("[")

    if first_bracket != -1 and (first_brace == -1 or first_bracket < first_brace):
        end = text.rfind("]")
        if end != -1 and end > first_bracket:
            return text[first_bracket : end + 1]

    if first_brace != -1:
        end = text.rfind("}")
        if end != -1 and end > first_brace:
            return text[first_brace : end + 1]

    return text


class AIClient:
    def __init__(self) -> None:
        _init_registry()

    async def call(
        self,
        task: str,
        messages: list[dict[str, str]],
        response_model: type[T] | None = None,
        context: dict[str, Any] | None = None,
    ) -> T | str:
        config, model_key = _get_model_for_task(task)
        log_ctx = {
            "task": task,
            "model_used": config.model,
            **(context or {}),
        }

        last_error: Exception | None = None
        backends = [(config, model_key)]
        fallback = _get_fallback(model_key)
        if fallback:
            backends.append(fallback)

        for backend_config, backend_key in backends:
            for attempt in range(settings.AI_MAX_RETRIES):
                delay = settings.AI_RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
                start_time = time.monotonic()

                try:
                    raw = await self._call_with_structured_output(
                        backend_config, messages, response_model
                    )
                    latency_ms = (time.monotonic() - start_time) * 1000
                    logger.info(
                        "AI call succeeded",
                        extra={**log_ctx, "attempt": attempt + 1, "latency_ms": latency_ms},
                    )
                    return raw

                except AIModelTimeoutError as exc:
                    last_error = exc
                    logger.warning(
                        f"AI call timeout (attempt {attempt + 1})",
                        extra={**log_ctx, "delay": delay},
                    )
                except AIPipelineError as exc:
                    last_error = exc
                    if "Authentication failed" in str(exc):
                        logger.error(f"Auth error, skipping retries: {exc}", extra=log_ctx)
                        break
                    logger.warning(
                        f"AI call failed (attempt {attempt + 1}): {exc}",
                        extra=log_ctx,
                    )
                except AIModelResponseError as exc:
                    last_error = exc
                    if attempt < settings.AI_MALFORMED_RETRIES:
                        logger.warning("Malformed response, retrying with correction", extra=log_ctx)
                        correction_msg = {
                            "role": "user",
                            "content": (
                                "Your previous response was malformed JSON. "
                                "Please respond with ONLY valid JSON, no markdown fences."
                            ),
                        }
                        messages = messages + [correction_msg]
                        continue
                    logger.error(f"Malformed response after retries: {exc}", extra=log_ctx)

                if attempt < settings.AI_MAX_RETRIES - 1:
                    await asyncio.sleep(delay)

        raise AIPipelineExhaustedError(
            f"All retries exhausted for task '{task}': {last_error}"
        )

    async def _call_with_structured_output(
        self,
        config: _ModelConfig,
        messages: list[dict[str, str]],
        response_model: type[T] | None,
    ) -> T | str:
        response_format = None
        if response_model is not None:
            schema = response_model.model_json_schema()
            response_format = {
                "type": "json_object",
            }

        raw = await _call_openai_api(config, messages, response_format)

        if response_model is None:
            return raw

        json_str = _extract_json_from_text(raw)
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise AIModelResponseError(
                f"Failed to parse JSON from {config.model}: {exc}. Raw: {raw[:500]}"
            ) from exc

        try:
            return response_model.model_validate(parsed)
        except ValidationError as exc:
            raise AIModelResponseError(
                f"Schema validation failed for {config.model}: {exc}. Data: {json.dumps(parsed)[:500]}"
            ) from exc
