from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class PromptEngine:
    """Build final prompts from versioned markdown templates."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self.templates_dir = templates_dir or Path(__file__).parent / "prompts"

    def build_prompt(
        self,
        *,
        system_role: str,
        mission: str,
        memory: str | dict[str, Any] | list[Any] | None,
        agent_name: str,
        expected_schema: type[BaseModel] | BaseModel | dict[str, Any] | str,
        template_name: str,
    ) -> str:
        template = self._load_template(template_name)
        replacements = {
            "mission": mission,
            "memory": self._serialize(memory),
            "schema": self._schema_to_text(expected_schema),
            "agent": agent_name,
            "available_agents": self._serialize(self._available_agents(memory)),
        }
        prompt = template
        for key, value in replacements.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", value)

        return "\n\n".join(
            [
                system_role.strip(),
                prompt.strip(),
                "Return ONLY valid JSON. No markdown. No explanations. No code fences.",
            ]
        )

    def _load_template(self, template_name: str) -> str:
        safe_name = template_name.removesuffix(".md")
        path = self.templates_dir / f"{safe_name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {safe_name}")
        return path.read_text(encoding="utf-8")

    def _serialize(self, value: str | dict[str, Any] | list[Any] | None) -> str:
        if value is None:
            return "{}"
        if isinstance(value, str):
            return value
        return json.dumps(value, indent=2, sort_keys=True)

    def _schema_to_text(self, schema: type[BaseModel] | BaseModel | dict[str, Any] | str) -> str:
        if isinstance(schema, str):
            return schema
        if isinstance(schema, dict):
            return json.dumps(schema, indent=2, sort_keys=True)
        if isinstance(schema, BaseModel):
            return json.dumps(schema.model_json_schema(), indent=2, sort_keys=True)
        if issubclass(schema, BaseModel):
            return json.dumps(schema.model_json_schema(), indent=2, sort_keys=True)
        return str(schema)

    def _available_agents(self, memory: str | dict[str, Any] | list[Any] | None) -> Any:
        if isinstance(memory, dict):
            return memory.get("Available Agents", [])
        return []
