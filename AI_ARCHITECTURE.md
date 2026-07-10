# AI Component Architecture

This document describes the design decoupling and package relationships established for the AI integration components.

---

## 1. Directory Structure Layout

The AI modules are structured under clean boundaries:

```text
BugBountyAI/
├── core/
│   └── prompt_manager.py     # Template caching, versioning, variable validations
├── memory/
│   └── conversation.py       # Isolated thread-safe conversation messages state
├── models/
│   └── ai/
│       ├── decision.py       # PlanDecision & AnalysisDecision Pydantic models
│       ├── response.py       # LLMResponse telemetry model
│       ├── severity.py       # SeverityAssessment model
│       └── recommendation.py # WorkflowRecommendation model
├── providers/
│   ├── base.py               # AIProvider ABC & Exception hierarchy
│   ├── capabilities.py       # ProviderCapabilities dataclass
│   └── gemini.py             # Reference generic Gemini client implementation
└── engine/
    ├── analyst.py            # Orchestrator coordinating analysis stages
    └── analysis/
        ├── normalizer.py     # Tool outputs standardizer
        ├── deduplicator.py   # Redundancy filter
        ├── classifier.py     # Severity mapper using Severity Enum
        └── analyzer.py       # AI validation and triaging stage
```

---

## 2. Decoupled Interface Principles

1. **Decoupled Providers**:
   Provider instances (e.g. `GeminiProvider`) are fully generic, holding **no** references to security tools or keywords. Planners and analysts interact through the unified `AIProvider` base class interface.
2. **Stateless Clients**:
   Conversation logs and token counters are maintained entirely inside the `Conversation` memory wrapper and passed in-argument to the provider client.
3. **Structured Pydantic Returns**:
   All generation outputs are validated using Pydantic JSON schemas, eliminating raw dictionary returns and ensuring strong type compliance.
