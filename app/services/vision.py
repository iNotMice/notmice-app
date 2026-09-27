"""Vision LLM providers. Gemini is wired; Claude is a swap-in stub."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Protocol, cast

import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.domain.uploads import (
    RawLabExtraction,
    VisionExtractionError,
    VisionNotConfiguredError,
    VisionTimeoutError,
)
from app.services.gemini_budget import GEMINI_MAX_ATTEMPTS

logger = structlog.get_logger(__name__)

_EXTRACTION_INSTRUCTIONS = (
    "Extract every numeric laboratory analyte from this blood panel. "
    "Return lab_name and collected_at (YYYY-MM-DD) when visible. "
    "Do not extract patient name, date of birth, phone, email, or medical record numbers. "
    "Units must stay as printed on the report. "
    "confidence is 0-1 for each marker."
)


@dataclass(frozen=True, slots=True)
class ProviderExtraction:
    """Model output plus the billed token count for this call, including retries."""

    extraction: RawLabExtraction
    tokens_used: int | None


class UsageTally:
    """Sum token counts across retries. One unknown bill keeps the whole call unknown."""

    def __init__(self) -> None:
        self._total = 0
        self._unknown = False

    def add(self, tokens: int | None) -> None:
        """Record one attempt.

        Args:
            tokens: Measured tokens, or ``None`` when the response had no usage metadata.
        """
        if tokens is None:
            self._unknown = True
            return
        self._total += tokens

    def tokens(self) -> int | None:
        """Return the summed bill, or ``None`` when any attempt omitted usage."""
        if self._unknown:
            return None
        return self._total


def gemini_response_schema(model: type[RawLabExtraction]) -> dict[str, Any]:
    """Return a JSON schema the Gemini Developer API will accept.

    Pydantic includes ``additionalProperties`` because the models forbid extra
    fields. That key is rejected on ``generateContent``.

    Args:
        model: Structured extraction model sent as ``response_schema``.
    """
    cleaned = _without_additional_properties(model.model_json_schema())
    if not isinstance(cleaned, dict):
        raise TypeError("Gemini response schema must be an object")
    return cleaned


def _without_additional_properties(node: object) -> object:
    """Drop additionalProperties from a JSON schema tree."""
    if isinstance(node, dict):
        return {
            key: _without_additional_properties(value)
            for key, value in node.items()
            if key not in {"additionalProperties", "additional_properties"}
        }
    if isinstance(node, list):
        return [_without_additional_properties(item) for item in node]
    return node


def usage_token_count(metadata: object | None) -> int | None:
    """Sum prompt, candidate, and thought tokens from a Gemini usage object.

    Args:
        metadata: ``usage_metadata`` from a generate_content response, or None.

    Returns:
        The summed count, ``total_token_count`` when the parts are absent, or
        ``None`` when the response did not report a bill.
    """
    if metadata is None:
        return None

    def read(name: str) -> int | None:
        if isinstance(metadata, dict):
            value = metadata.get(name)
        else:
            value = getattr(metadata, name, None)
        if value is None:
            return None
        return int(value)

    prompt = read("prompt_token_count")
    candidates = read("candidates_token_count")
    thoughts = read("thoughts_token_count")
    if prompt is None and candidates is None and thoughts is None:
        return read("total_token_count")
    return (prompt or 0) + (candidates or 0) + (thoughts or 0)


class ExtractionProvider(Protocol):
    """Structured lab extraction. Implementations must not write files to disk."""

    @property
    def name(self) -> str:
        """Provider id used in parser_version, e.g. ``gemini``."""

    @property
    def model_id(self) -> str:
        """Model id used in parser_version."""

    async def extract_from_text(self, text: str) -> ProviderExtraction:
        """Structure already-extracted PDF text into markers."""

    async def extract_from_media(self, payload: bytes, mime_type: str) -> ProviderExtraction:
        """OCR a scan, photo, or image-only PDF from in-memory bytes."""


class ClaudeExtractionProvider:
    """Reserved adapter. Implement this class to switch VISION_PROVIDER=claude."""

    name = "claude"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self.model_id = model

    async def extract_from_text(self, text: str) -> ProviderExtraction:
        """Claude text structuring is not wired yet."""
        del text
        raise VisionNotConfiguredError(
            "Claude Vision is not implemented yet. Keep VISION_PROVIDER=gemini."
        )

    async def extract_from_media(self, payload: bytes, mime_type: str) -> ProviderExtraction:
        """Claude image/PDF vision is not wired yet."""
        del payload, mime_type
        raise VisionNotConfiguredError(
            "Claude Vision is not implemented yet. Keep VISION_PROVIDER=gemini."
        )


class GeminiExtractionProvider:
    """Gemini structured output over inline bytes. Never uses the Files API."""

    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: float = 60) -> None:
        self._api_key = api_key
        self.model_id = model
        self._timeout_seconds = timeout_seconds

    def _require_key(self) -> None:
        """Fail closed when the process has no Gemini key."""
        if not self._api_key.strip():
            raise VisionNotConfiguredError("GEMINI_API_KEY is not set")

    async def extract_from_text(self, text: str) -> ProviderExtraction:
        """Send selectable PDF text to Gemini for structuring."""
        self._require_key()
        return await self._complete([_EXTRACTION_INSTRUCTIONS, text])

    async def extract_from_media(self, payload: bytes, mime_type: str) -> ProviderExtraction:
        """Send PDF or image bytes inline. The payload is not uploaded to Files API."""
        self._require_key()
        from google.genai import types

        part = types.Part.from_bytes(data=payload, mime_type=mime_type)
        resolution = (
            types.MediaResolution.MEDIA_RESOLUTION_MEDIUM
            if mime_type == "application/pdf"
            else types.MediaResolution.MEDIA_RESOLUTION_HIGH
        )
        return await self._complete(
            [_EXTRACTION_INSTRUCTIONS, part],
            media_resolution=resolution,
        )

    async def _complete(
        self,
        contents: list[object],
        media_resolution: object | None = None,
    ) -> ProviderExtraction:
        """Call Gemini with retries and parse a RawLabExtraction.

        Args:
            contents: Prompt plus optional inline media part.
            media_resolution: Optional Gemini media_resolution enum value.
        """
        tally = UsageTally()
        try:
            panel = await self._retry(contents, media_resolution, tally)
        except (VisionNotConfiguredError, VisionTimeoutError):
            raise
        except VisionExtractionError as exc:
            raise VisionExtractionError(
                "Gemini extraction failed",
                tokens_used=tally.tokens(),
            ) from exc
        return ProviderExtraction(extraction=panel, tokens_used=tally.tokens())

    async def _retry(
        self,
        contents: list[object],
        media_resolution: object | None,
        tally: UsageTally,
    ) -> RawLabExtraction:
        """Retry a single extract and fold every attempt into ``tally``."""
        last_error: Exception | None = None
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(GEMINI_MAX_ATTEMPTS),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            retry=retry_if_exception_type((VisionExtractionError, ConnectionError)),
            reraise=True,
        ):
            with attempt:
                try:
                    panel, tokens = await self._once(contents, media_resolution)
                except (VisionNotConfiguredError, VisionTimeoutError):
                    raise
                except VisionExtractionError as exc:
                    tally.add(exc.tokens_used)
                    last_error = exc
                    raise
                except Exception as exc:
                    last_error = exc
                    logger.warning("gemini_extract_retry", error=str(exc))
                    raise VisionExtractionError(
                        "Gemini extraction failed",
                        tokens_used=0,
                    ) from exc
                tally.add(tokens)
                return panel
        raise VisionExtractionError(
            "Gemini extraction failed",
            tokens_used=tally.tokens(),
        ) from last_error

    async def _once(
        self,
        contents: list[object],
        media_resolution: object | None,
    ) -> tuple[RawLabExtraction, int | None]:
        """Single Gemini generate_content call and its usage metadata."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._api_key)
        config = types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=gemini_response_schema(RawLabExtraction),
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            media_resolution=cast(Any, media_resolution),
        )
        response = await self._bounded(
            client.aio.models.generate_content(
                model=self.model_id,
                contents=cast(Any, contents),
                config=config,
            )
        )
        tokens = usage_token_count(getattr(response, "usage_metadata", None))
        parsed = response.parsed
        if isinstance(parsed, RawLabExtraction):
            return parsed, tokens
        if isinstance(parsed, dict):
            return RawLabExtraction.model_validate(parsed), tokens
        text = response.text
        if text:
            return RawLabExtraction.model_validate_json(text), tokens
        raise VisionExtractionError("Gemini returned an empty extraction", tokens_used=tokens)

    async def _bounded(self, call: Awaitable[Any]) -> Any:
        """Wait for one Gemini call and turn a deadline miss into ``VisionTimeoutError``."""
        try:
            return await asyncio.wait_for(call, timeout=self._timeout_seconds)
        except TimeoutError as exc:
            raise VisionTimeoutError("Gemini extraction timed out") from exc


def build_extraction_provider(
    *,
    provider: str,
    gemini_api_key: str,
    gemini_model: str,
    claude_api_key: str,
    claude_model: str,
    gemini_timeout_seconds: float = 60,
) -> ExtractionProvider:
    """Return the configured provider. Claude is intentionally unimplemented.

    Args:
        provider: ``gemini`` or ``claude``.
        gemini_api_key: Gemini API key, empty if unset.
        gemini_model: Gemini model id.
        claude_api_key: Reserved for the Claude adapter.
        claude_model: Reserved Claude model id.
        gemini_timeout_seconds: Deadline for one Gemini call, in seconds.
    """
    name = provider.strip().lower()
    if name == "gemini":
        return GeminiExtractionProvider(
            api_key=gemini_api_key,
            model=gemini_model,
            timeout_seconds=gemini_timeout_seconds,
        )
    if name == "claude":
        return ClaudeExtractionProvider(api_key=claude_api_key, model=claude_model)
    raise VisionNotConfiguredError(f"Unknown VISION_PROVIDER: {provider}")
