# BugBountyAI Planner Internals

This document details the architecture, decision pipeline, workflow selection hierarchy, and future AI integration layers for the BugBountyAI Planner.

---

## 1. Planning Pipeline & Decision Flow

The Planner acts as the orchestration brain of the scan. It runs a unified planning-to-execution pipeline:

```text
       User Objective (e.g. "dns recon example.com")
                           │
                           ▼
                 1. Normalization & Sanitization
                           │
                           ▼
      2. Dynamic Tool Discovery (Inspects Registry Capabilities)
                           │
                           ▼
          3. Workflow Selection Hierarchy (manual/rule/AI)
                           │
                           ▼
        4. Validation (Confirm workflow steps exist in registry)
                           │
                           ▼
                  5. Plan Creation
                           │
                           ▼
       6. Workflow Engine Dispatch (Concurrent execution)
                           │
                           ▼
       7. Result Aggregation & Telemetry Capture (PlanResult)
```

---

## 2. Workflow Selection Algorithm

The Planner maps objectives to execution tracks using a deterministic fallback hierarchy:

1. **MANUAL Mode / Suggested Workflow**:
   If the mode is `MANUAL`, the user-specified workflow is used directly. If it doesn't exist, planning fails.
2. **HYBRID Mode**:
   If a suggestion is supplied, the Planner verifies the target YAML file existence. If validated, it executes; otherwise, it falls back to the rule-based keyword matcher.
3. **AI Recommendation (AUTO Mode)**:
   If `AIProvider` is active, the Planner generates a context prompt enumerating available tool capabilities and passes it to the AI for recommendation. If the AI returns a valid, on-disk workflow choice, it is selected.
4. **Rule-Based Matcher**:
   If the AI is disabled or fails, the Planner parses the objective for keywords (e.g., `recon`, `subdomain`, `dns`, `scan`) and maps them to appropriate workflow templates (e.g., `recon`).
5. **Default Workflow**:
   If no rules match, the engine falls back to `"recon"`.

---

## 3. Dynamic Capability Discovery

The Planner remains decoupled from specific tool names (like `subfinder` or `nuclei`).

- At execution time, the Planner requests tool registration lists from the `ToolRegistry`.
- Mapped tools are resolved as `Capability` objects.
- Before executing a selected workflow, the Planner compares the required workflow step tools against the active registered capabilities list. If any required tool is missing, the scan aborts safely and returns a failed `PlanResult` without throwing exceptions.

---

## 4. Future AI Integration

The `AIProvider` is configured as a non-blocking advisory layer. Future iterations will extend the AI role to:
- Dynamically suggest custom tool execution parameters.
- Re-order step dependency trees based on early scan findings (e.g., skip `nuclei` web checks if `httpx` reports no web ports are active).
- Triage anomalies and suggest additional scan targets.
