"""Extractor agent: one class, parameterized by (schema, prompt) from the registry.

The orchestrator selects the config by document_type — the LLM never picks the schema.
"""

import config
from llm import StructuredResponse, call_structured
from prompts import EXTRACTION_PREAMBLE
from registry import EXTRACTORS, ExtractorConfig


class Extractor:
    """Runs one forced-schema extraction call for a given document type."""

    def __init__(self, cfg: ExtractorConfig) -> None:
        self._schema = cfg.schema
        self._system = f"{EXTRACTION_PREAMBLE}\n{cfg.prompt}"

    def run(self, raw_text: str, prior_errors: list[str] | None = None) -> StructuredResponse:
        """Extract fields from the full document text.

        prior_errors, when present, are appended so a validation retry can self-correct.
        """
        user_text = raw_text
        if prior_errors:
            user_text = (
                f"{raw_text}\n\n"
                "Your previous extraction failed these checks:\n"
                + "\n".join(f"- {e}" for e in prior_errors)
                + "\nProduce a corrected extraction."
            )
        return call_structured(
            stage="extract",
            model=config.MODEL_EXTRACT,
            system=self._system,
            user_text=user_text,
            schema=self._schema,
            max_tokens=config.MAX_TOKENS_EXTRACT,
        )


def config_for(document_type: str) -> ExtractorConfig:
    """Code-level routing: the extraction config for a supported document type.

    Only reached for the four supported types — `route_after_classify` stops "Other" before
    extraction — so a missing key here is a routing bug, not a runtime fallback.
    """
    return EXTRACTORS[document_type]
