"""Thin OpenAI client wrapper: forced structured output via function calling.

The only file in the project that talks to the OpenAI API.
"""

import json
import logging
import time
from typing import NamedTuple

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

_TRANSPORT_ERRORS = (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)
_TRANSPORT_ATTEMPTS = 3

_client: OpenAI | None = None


class StructuredCallError(Exception):
    """The model's output failed schema validation (handled by stage retries)."""


class StructuredResponse(NamedTuple):
    """Validated model output plus token accounting for pipeline_meta."""

    parsed: BaseModel
    input_tokens: int
    output_tokens: int


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()  # reads OPENAI_API_KEY from the environment
    return _client


def call_structured(
    *,
    stage: str,
    model: str,
    system: str,
    user_text: str,
    schema: type[BaseModel],
    max_tokens: int = 2000,
) -> StructuredResponse:
    """Call the model and force its reply into `schema`. Raises StructuredCallError
    if the reply does not validate; transport errors are retried with backoff."""
    tool_name = f"record_{schema.__name__.lower()}"
    response = _create_with_backoff(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"Record the {schema.__name__} for this document.",
                    "parameters": schema.model_json_schema(),
                },
            }
        ],
        tool_choice={"type": "function", "function": {"name": tool_name}},
        temperature=0,
        max_tokens=max_tokens,
    )

    usage = response.usage
    logger.info(
        "llm call | stage=%s model=%s in_tokens=%s out_tokens=%s",
        stage, model, usage.prompt_tokens, usage.completion_tokens,
    )

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise StructuredCallError(f"{stage}: model returned no tool call")
    raw_arguments = tool_calls[0].function.arguments
    try:
        parsed = schema.model_validate(json.loads(raw_arguments))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise StructuredCallError(f"{stage}: output failed validation: {exc}") from exc

    return StructuredResponse(parsed, usage.prompt_tokens, usage.completion_tokens)


def embed_texts(texts: list[str], *, model: str) -> list[list[float]]:
    """Return one embedding vector per input string (single API call). Used by the eval's
    semantic summary-similarity metric; callers handle transport/auth failures."""
    response = _get_client().embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def _create_with_backoff(**kwargs):
    """chat.completions.create with exponential backoff on transport errors."""
    for attempt in range(1, _TRANSPORT_ATTEMPTS + 1):
        try:
            return _get_client().chat.completions.create(**kwargs)
        except _TRANSPORT_ERRORS as exc:
            if attempt == _TRANSPORT_ATTEMPTS:
                raise
            delay = 2 ** (attempt - 1)
            logger.warning("transport error (%s), retry %d in %ds", exc, attempt, delay)
            time.sleep(delay)
