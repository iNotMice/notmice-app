"""Recognize provider answers that mean "out of quota" rather than "bad request"."""

from __future__ import annotations


def is_quota_error(exc: BaseException) -> bool:
    """True for an HTTP 429 / RESOURCE_EXHAUSTED answer from the model provider.

    google-genai raises ``ClientError`` whose text starts with the status code,
    for example ``429 RESOURCE_EXHAUSTED. {...}``. The text never contains user
    data: it is the provider's own error message.
    """
    text = str(exc)
    return "RESOURCE_EXHAUSTED" in text or text.startswith("429") or " 429 " in f" {text} "
