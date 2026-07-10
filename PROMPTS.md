# BugBountyAI Prompt System & Manager

This document describes prompt versioning, template variables rendering, and strict variable checks in the prompt manager.

---

## 1. Metadata Frontmatter Schemas

All prompt templates inside [`prompts/`](file:///c:/BugBountyAI/prompts/) are structured as Markdown files with a YAML frontmatter boundary. This enables future prompt upgrades and version tracking without code refactoring:

```yaml
---
name: planner
version: 1
author: BugBountyAI
description: Recommend scan workflow
created: 2026-07-10
tags: [planner, auto]
min_provider_version: gemini-1.5
---
Analyze user objective: {{ objective }}
```

The parsed metadata is mapped into a strongly typed `PromptMetadata` dataclass.

---

## 2. Dynamic Rendering & Caching

The [`PromptManager`](file:///c:/BugBountyAI/core/prompt_manager.py) controls prompt compilation:

1. **Jinja-Like Placeholders**: The template uses `{{ variable }}` tags.
2. **On-Demand Loading**: Files are loaded from disk upon request, parsed into `PromptTemplate`, and stored in a thread-safe memory cache.
3. **Hashing**: Every rendered output is compiled into a `CompiledPrompt` instance containing a SHA-256 hash of the final text.

---

## 3. Strict Validation & Fail-Fast Safeguards

To prevent malformed LLM prompts, the PromptManager performs strict validations before rendering:

- **Missing variables**: Throws a `ValueError` if the template expects a placeholder that is missing from the variables dictionary.
- **Unknown variables**: Throws a `ValueError` if unexpected keys are provided in the dictionary payload.
- **Malformed frontmatter**: Throws a parsing error if the YAML frontmatter is invalid.
