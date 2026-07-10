import hashlib
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from core.config import BASE_DIR


@dataclass(frozen=True)
class PromptMetadata:
    """
    Strongly typed metadata defined in a prompt's YAML frontmatter.
    """
    name: str
    version: int
    author: str
    description: str
    created: Optional[str] = None
    updated: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    min_provider_version: Optional[str] = None


@dataclass(frozen=True)
class PromptTemplate:
    """
    Parsed prompt template containing metadata, the raw body, and expected variables.
    """
    metadata: PromptMetadata
    body: str
    required_vars: list[str]


@dataclass(frozen=True)
class CompiledPrompt:
    """
    Rendered prompt text populated with variable parameters and its SHA-256 verification hash.
    """
    metadata: PromptMetadata
    rendered_text: str
    hash: str


def parse_prompt_file(content: str) -> PromptTemplate:
    """
    Parse a Markdown file with a YAML frontmatter header boundary.
    Extracts metadata and locates all {{ variable }} placeholders.
    """
    # Parse frontmatter bounded by ---
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
    if not match:
        raise ValueError("Invalid frontmatter: File must start with '---' header boundary.")

    yaml_str = match.group(1)
    body = match.group(2).strip()

    try:
        meta_dict = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid frontmatter YAML formatting: {e}")

    if not isinstance(meta_dict, dict):
        raise ValueError("Frontmatter YAML must parse as a dictionary.")

    # Validate required metadata fields
    for field_name in ["name", "version", "author", "description"]:
        if field_name not in meta_dict:
            raise ValueError(f"Missing required prompt metadata field: {field_name}")

    metadata = PromptMetadata(
        name=str(meta_dict["name"]),
        version=int(meta_dict["version"]),
        author=str(meta_dict["author"]),
        description=str(meta_dict["description"]),
        created=meta_dict.get("created"),
        updated=meta_dict.get("updated"),
        tags=list(meta_dict.get("tags", [])),
        min_provider_version=meta_dict.get("min_provider_version"),
    )

    # Discover placeholders like {{ var }}
    placeholders = re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", body)

    # Validate duplicate variable parsing check
    seen = set()
    required_vars = []
    for var in placeholders:
        if var not in seen:
            seen.add(var)
            required_vars.append(var)

    return PromptTemplate(
        metadata=metadata,
        body=body,
        required_vars=required_vars,
    )


class PromptManager:
    """
    Manager responsible for loading, rendering, caching, and validating prompt templates.
    """

    def __init__(self, prompts_dir: Optional[Path] = None) -> None:
        self.prompts_dir = prompts_dir or (BASE_DIR / "prompts")
        self._cache: dict[str, PromptTemplate] = {}
        self._lock = threading.Lock()

    def load(self, name: str) -> PromptTemplate:
        """
        Load prompt from templates cache or disk, validating structure immediately.
        """
        with self._lock:
            if name in self._cache:
                return self._cache[name]

            prompt_file = self.prompts_dir / f"{name}.md"
            if not prompt_file.exists():
                raise FileNotFoundError(f"Prompt file '{name}.md' not found at {prompt_file}")

            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()

            template = parse_prompt_file(content)
            self._cache[name] = template
            return template

    def validate(self, template: PromptTemplate, variables: dict[str, Any]) -> None:
        """
        Ensure all required variables are present, and that no unexpected
        keys are supplied in the dictionary parameter payload.
        """
        provided = set(variables.keys())
        expected = set(template.required_vars)

        missing = expected - provided
        if missing:
            raise ValueError(f"Missing required variables for prompt '{template.metadata.name}': {missing}")

        extra = provided - expected
        if extra:
            raise ValueError(f"Unknown variables provided for prompt '{template.metadata.name}': {extra}")

    def render(self, name: str, variables: dict[str, Any]) -> CompiledPrompt:
        """
        Load prompt template, perform parameter validations, and replace
        all placeholders. Returns a CompiledPrompt with SHA-256 integrity hash.
        """
        template = self.load(name)
        self.validate(template, variables)

        rendered = template.body
        for var, val in variables.items():
            pattern = r"\{\{\s*" + re.escape(var) + r"\s*\}\}"
            rendered = re.sub(pattern, str(val), rendered)

        prompt_hash = hashlib.sha256(rendered.encode("utf-8")).hexdigest()

        return CompiledPrompt(
            metadata=template.metadata,
            rendered_text=rendered,
            hash=prompt_hash,
        )
