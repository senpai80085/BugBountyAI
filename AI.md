# BugBountyAI Provider & Exception Architecture

This document describes the design, lifecycle, exception hierarchy, and context rules of the AI Provider layer.

---

## 1. Provider Capabilities Configuration

Each provider implements a generic LLM contract without core knowledge of security vulnerabilities or specific CLI scan tools. Instead, capabilities are exposed via the strongly typed [`ProviderCapabilities`](file:///c:/BugBountyAI/providers/capabilities.py) schema:

- `provider_name`: Identifier (e.g. `"Gemini"`).
- `provider_version`: Provider release version.
- `supported_features`: List of operations (e.g. `["chat", "stream", "structured", "embedding"]`).
- `context_window`: Context limit in tokens.
- `supports_structured`: Boolean indicating JSON schema validation support.

Adding a new provider (e.g., Claude, OpenAI, Ollama, DeepSeek) requires adding **only one file** inside the `providers/` directory implementing the `AIProvider` base class.

---

## 2. Conversation Memory Isolation

The AI provider is completely stateless. System prompts, chat records, and assistant outputs are stored outside the provider in [`memory/conversation.py`](file:///c:/BugBountyAI/memory/conversation.py):

- **Memory**: The orchestrator instantiates a `Conversation` model and appends `Message` elements (Role is typed as `system`, `user`, or `model`).
- **Parameter Pass**: The active conversation instance is passed directly as a parameter inside `chat()`, `stream()`, or `structured()`.
- **Trimming Loop**: Prompt token counts are computed and old messages are trimmed from the conversation boundary if the total exceeds `max_tokens`.

---

## 3. Unified Exception Model

Downstream SDK errors are caught and converted into a standard exception tree to simplify execution handling for planners and analyst pipelines:

```text
AIProviderError (Base Exception)
 ├── AuthenticationError      (Invalid API keys)
 ├── TimeoutError             (Response timeout)
 ├── RateLimitError           (Quota limit exceeded)
 ├── ValidationError          (JSON parsing/schema validation failure)
 ├── ContextOverflowError     (Context window exceeded)
 └── ProviderUnavailableError (Host unreachable/down)
```
No raw generic Exceptions are propagated to callers of the provider layer.
