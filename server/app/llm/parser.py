from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.logger import llm_logger
from app.llm.exceptions import ParsingError

ModelT = TypeVar("ModelT", bound=BaseModel)


class LLMParser:
    """Extract and validate structured JSON from raw model output."""

    _code_fence_pattern = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)

    def parse_json(self, raw_output: str, response_model: type[ModelT]) -> ModelT:
        payload = self.extract_json(raw_output)
        try:
            return response_model.model_validate_json(payload)
        except ValidationError as exc:
            raise ParsingError(f"LLM JSON did not match schema: {exc}") from exc
        except ValueError as exc:
            raise ParsingError(f"LLM output was not valid JSON: {exc}") from exc

    def extract_json(self, raw_output: str) -> str:
        cleaned = self._strip_markdown(raw_output).strip()
        if self._is_json(cleaned):
            llm_logger.debug("LLM parser accepted full response as JSON", payload=cleaned)
            return cleaned

        candidate = self._find_json_fragment(cleaned)
        if candidate is None:
            llm_logger.debug("LLM parser found no JSON fragment", raw_output=raw_output, cleaned_output=cleaned)
            raise ParsingError("LLM response did not contain a JSON object or array.")
        try:
            json.loads(candidate)
        except json.JSONDecodeError as exc:
            llm_logger.error(
                "LLM parser extracted invalid JSON fragment",
                error=str(exc),
                fragment=candidate,
                raw_output=raw_output,
            )
            raise ParsingError(f"Extracted LLM JSON fragment is invalid: {exc}") from exc
        llm_logger.debug("LLM parser extracted JSON fragment", payload=candidate)
        return candidate

    def _strip_markdown(self, raw_output: str) -> str:
        raw_output = raw_output.strip()
        match = self._code_fence_pattern.fullmatch(raw_output)
        if match:
            return match.group(1)
        return raw_output.replace("```json", "").replace("```", "")

    def _is_json(self, value: str) -> bool:
        try:
            json.loads(value)
        except json.JSONDecodeError:
            return False
        return True

    def _find_json_fragment(self, value: str) -> str | None:
        decoder = json.JSONDecoder()
        for index, char in enumerate(value):
            if char not in "[{":
                continue
            try:
                _, end = decoder.raw_decode(value[index:])
            except json.JSONDecodeError:
                continue
            return value[index : index + end]
        return None
